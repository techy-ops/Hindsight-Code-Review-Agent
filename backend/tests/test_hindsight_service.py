import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from config import Settings
from hindsight_service import HindsightService, sanitize_identifier
from memory_model import MemoryRecord


def test_sanitize_identifier():
    assert sanitize_identifier("my/repo:main") == "my-repo-main"
    assert sanitize_identifier("$$$project!!!") == "project"
    assert sanitize_identifier("") == "default"


def test_resolve_bank_id_project_scoping():
    settings = Settings(hindsight_bank_id="code-review-agent")
    service = HindsightService(config=settings)

    # Default / main projects map cleanly
    assert service.resolve_bank_id("default") == "code-review-agent"
    assert service.resolve_bank_id("main") == "code-review-agent"

    # Distinct project receives isolated bank namespace
    assert service.resolve_bank_id("auth-microservice") == "code-review-agent_auth-microservice"
    assert service.resolve_bank_id("payment-gateway") == "code-review-agent_payment-gateway"


@pytest.mark.asyncio
async def test_check_health_disabled():
    settings = Settings(hindsight_enabled=False)
    service = HindsightService(config=settings)
    health = await service.check_health()
    assert health["status"] == "disabled"


@pytest.mark.asyncio
async def test_check_health_healthy():
    settings = Settings(hindsight_enabled=True, hindsight_base_url="http://mock-hindsight:8888")
    service = HindsightService(config=settings)

    mock_client = MagicMock()
    mock_client.aget_version = AsyncMock(return_value=MagicMock(version="0.10.1"))
    service._client = mock_client

    health = await service.check_health()
    assert health["status"] == "healthy"
    assert health["version"] == "0.10.1"


@pytest.mark.asyncio
async def test_check_health_server_unavailable():
    settings = Settings(hindsight_enabled=True, hindsight_base_url="http://unreachable:8888")
    service = HindsightService(config=settings)

    mock_client = MagicMock()
    mock_client.aget_version = AsyncMock(side_effect=ConnectionError("Cannot connect"))
    service._client = mock_client

    health = await service.check_health()
    assert health["status"] == "unavailable"
    assert "ConnectionError" in health["message"]


@pytest.mark.asyncio
async def test_retain_memory_success():
    settings = Settings(hindsight_enabled=True, hindsight_bank_id="test-bank")
    service = HindsightService(config=settings)

    mock_client = MagicMock()
    mock_client.acreate_bank = AsyncMock()
    mock_client.aretain = AsyncMock()
    service._client = mock_client

    success = await service.retain_memory(
        project_id="repo-1",
        language="python",
        content="Always use pytest for testing.",
        metadata={"category": "convention"},
        tags=["convention", "testing"]
    )

    assert success is True
    assert mock_client.aretain.called
    call_kwargs = mock_client.aretain.call_args.kwargs
    assert call_kwargs["bank_id"] == "test-bank_repo-1"
    assert "Always use pytest" in call_kwargs["content"]
    assert "project:repo-1" in call_kwargs["tags"]
    assert "lang:python" in call_kwargs["tags"]


@pytest.mark.asyncio
async def test_retain_memory_failure_fails_gracefully():
    settings = Settings(hindsight_enabled=True)
    service = HindsightService(config=settings)

    mock_client = MagicMock()
    mock_client.acreate_bank = AsyncMock()
    mock_client.aretain = AsyncMock(side_effect=TimeoutError("Hindsight timeout"))
    service._client = mock_client

    # Should not raise exception
    success = await service.retain_memory(
        project_id="repo-1",
        language="python",
        content="Important memory content"
    )
    assert success is False


@pytest.mark.asyncio
async def test_recall_memory_success():
    settings = Settings(hindsight_enabled=True, hindsight_bank_id="test-bank")
    service = HindsightService(config=settings)

    mock_item_1 = MagicMock()
    mock_item_1.id = "mem-1"
    mock_item_1.text = "Established repository pattern for DB access"
    mock_item_1.metadata = {"category": "architecture"}
    mock_item_1.tags = ["architecture"]

    mock_item_2 = MagicMock()
    mock_item_2.id = "mem-2"
    mock_item_2.text = "Prevent SQL injection with parameterized queries"
    mock_item_2.metadata = {"category": "vulnerability"}
    mock_item_2.tags = ["security"]

    mock_response = MagicMock()
    mock_response.results = [mock_item_1, mock_item_2]

    mock_client = MagicMock()
    mock_client.arecall = AsyncMock(return_value=mock_response)
    service._client = mock_client

    results = await service.recall_memory(
        project_id="repo-1",
        query="def get_user(id): pass",
        language="python",
        limit=5
    )

    assert len(results) == 2
    assert results[0]["id"] == "mem-1"
    assert results[0]["category"] == "architecture"
    assert results[1]["id"] == "mem-2"
    assert results[1]["category"] == "vulnerability"


@pytest.mark.asyncio
async def test_recall_memory_failure_returns_empty_fallback():
    settings = Settings(hindsight_enabled=True)
    service = HindsightService(config=settings)

    mock_client = MagicMock()
    mock_client.arecall = AsyncMock(side_effect=Exception("Database down"))
    service._client = mock_client

    results = await service.recall_memory(
        project_id="repo-1",
        query="test query",
    )
    assert results == []


@pytest.mark.asyncio
async def test_reflect_memory_success():
    settings = Settings(hindsight_enabled=True, hindsight_reflect_enabled=True, hindsight_bank_id="test-bank")
    service = HindsightService(config=settings)

    mock_fact = MagicMock()
    mock_fact.text = "Repository pattern accepted 5 times"
    mock_response = MagicMock()
    mock_response.text = "Project strongly prefers repository pattern for database interactions."
    mock_response.based_on = [mock_fact]

    mock_client = MagicMock()
    mock_client.areflect = AsyncMock(return_value=mock_response)
    service._client = mock_client

    result = await service.reflect_memory(
        project_id="repo-1",
        query="Synthesize conventions",
        developer_id="dev-alice"
    )

    assert result is not None
    assert "strongly prefers repository pattern" in result["text"]
    assert len(result["based_on"]) == 1
    assert result["developer_id"] == "dev-alice"


@pytest.mark.asyncio
async def test_reflect_memory_failure_falls_back_to_none():
    settings = Settings(hindsight_enabled=True, hindsight_reflect_enabled=True)
    service = HindsightService(config=settings)

    mock_client = MagicMock()
    mock_client.areflect = AsyncMock(side_effect=TimeoutError("Reflection timeout"))
    service._client = mock_client

    # Should not raise exception
    result = await service.reflect_memory(
        project_id="repo-1",
        query="Synthesize conventions"
    )
    assert result is None


@pytest.mark.asyncio
async def test_retain_feedback_success():
    from memory_model import FeedbackRequest
    settings = Settings(hindsight_enabled=True, hindsight_bank_id="test-bank")
    service = HindsightService(config=settings)

    mock_client = MagicMock()
    mock_client.acreate_bank = AsyncMock()
    mock_client.aretain = AsyncMock()
    service._client = mock_client

    fb = FeedbackRequest(
        project_id="repo-1",
        developer_id="dev-bob",
        issue_title="Use Redis caching",
        recommendation="Install redis-py",
        action="reject",
        reason="Project uses PostgreSQL caching"
    )

    success = await service.retain_feedback(fb)
    assert success is True
    assert mock_client.aretain.called
    call_kwargs = mock_client.aretain.call_args.kwargs
    assert "REJECTED" in call_kwargs["content"]
    assert "PostgreSQL caching" in call_kwargs["content"]
    assert "action:reject" in call_kwargs["tags"]
    assert "developer:dev-bob" in call_kwargs["tags"]

