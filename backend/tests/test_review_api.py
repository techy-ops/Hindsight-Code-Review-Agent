import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import google.generativeai as genai
from main import app, hindsight_service


@pytest.fixture
def mock_gemini_review_response():
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({
        "issues": {
            "critical": 0,
            "high": 1,
            "medium": 0,
            "low": 0
        },
        "details": [
            {
                "severity": "high",
                "title": "Bypassing Repository Pattern",
                "description": "Code queries the DB directly instead of using the repository pattern.",
                "suggestion": "Use UserRepository.get_by_id(user_id)."
            }
        ]
    })
    return mock_resp


@pytest.fixture
def mock_gemini_rewrite_response():
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({
        "optimized_code": "def add(a, b): return a + b",
        "metrics": {
            "time_complexity": "O(1)",
            "memory_usage": "O(1)"
        },
        "diff": [
            {"type": "remove", "content": "- return a+b"},
            {"type": "add", "content": "+ return a + b"}
        ]
    })
    return mock_resp


@pytest.mark.asyncio
async def test_review_with_recalled_memory_included_in_prompt(
    async_client,
    mock_gemini_review_response
):
    """Test review succeeds when Hindsight returns memories and memory is passed to LLM."""
    mock_memories = [
        {
            "id": "mem-1",
            "text": "Project convention: Always use repository pattern for database access.",
            "category": "architecture",
            "metadata": {"category": "architecture"},
            "tags": ["project:test-proj", "architecture"]
        }
    ]

    with patch.object(hindsight_service, "recall_memory", AsyncMock(return_value=mock_memories)) as mock_recall, \
         patch.object(hindsight_service, "retain_knowledge_records", AsyncMock(return_value=1)) as mock_retain, \
         patch.object(genai.GenerativeModel, "generate_content_async", AsyncMock(return_value=mock_gemini_review_response)) as mock_generate:

        response = await async_client.post(
            "/review",
            json={
                "code": "def get_user(db, user_id): return db.execute('SELECT * FROM users')",
                "language": "python",
                "project_id": "test-proj"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Contract checks
        assert "issues" in data
        assert "details" in data
        assert "memory" in data

        # Memory verification
        mem = data["memory"]
        assert mem["status"] == "recalled"
        assert mem["project_id"] == "test-proj"
        assert mem["memories_retrieved"] == 1
        assert mem["learning_context_applied"] is True

        # Verify LLM prompt received the recalled memory context!
        prompt_sent = mock_generate.call_args[0][0]
        assert "=== BEGIN HISTORICAL PROJECT MEMORY (HINDSIGHT) ===" in prompt_sent
        assert "Always use repository pattern" in prompt_sent
        assert "CRITICAL MEMORY INSTRUCTIONS:" in prompt_sent


@pytest.mark.asyncio
async def test_review_no_memories_first_time(
    async_client,
    mock_gemini_review_response
):
    """Test first-time review when no memories exist yet in Hindsight."""
    with patch.object(hindsight_service, "recall_memory", AsyncMock(return_value=[])) as mock_recall, \
         patch.object(hindsight_service, "retain_knowledge_records", AsyncMock(return_value=1)) as mock_retain, \
         patch.object(genai.GenerativeModel, "generate_content_async", AsyncMock(return_value=mock_gemini_review_response)):

        response = await async_client.post(
            "/review",
            json={
                "code": "def process(): pass",
                "language": "python",
                "project_id": "brand-new-project"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["memory"]["status"] == "no_memories"
        assert data["memory"]["memories_retrieved"] == 0
        assert data["memory"]["learning_context_applied"] is False


@pytest.mark.asyncio
async def test_review_when_recall_fails_falls_back(
    async_client,
    mock_gemini_review_response
):
    """Test that if Hindsight recall raises an error, the review continues normally."""
    with patch.object(hindsight_service, "recall_memory", AsyncMock(side_effect=RuntimeError("Hindsight down"))), \
         patch.object(hindsight_service, "retain_knowledge_records", AsyncMock(return_value=0)), \
         patch.object(genai.GenerativeModel, "generate_content_async", AsyncMock(return_value=mock_gemini_review_response)):

        response = await async_client.post(
            "/review",
            json={
                "code": "def calculate(): return 42",
                "language": "python"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["issues"]["high"] == 1
        assert data["memory"]["status"] == "error"


@pytest.mark.asyncio
async def test_review_when_retain_fails_succeeds(
    async_client,
    mock_gemini_review_response
):
    """Test that if Hindsight retain fails, the review succeeds and returns properly."""
    with patch.object(hindsight_service, "recall_memory", AsyncMock(return_value=[])), \
         patch.object(hindsight_service, "retain_knowledge_records", AsyncMock(side_effect=Exception("Storage full"))), \
         patch.object(genai.GenerativeModel, "generate_content_async", AsyncMock(return_value=mock_gemini_review_response)):

        response = await async_client.post(
            "/review",
            json={
                "code": "def send_email(): pass",
                "language": "python"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "issues" in data
        assert "details" in data
        assert data["memory"]["memories_retained"] == 0


@pytest.mark.asyncio
async def test_existing_review_payload_compatibility(
    async_client,
    mock_gemini_review_response
):
    """Verify exact backward compatibility: payload without project_id succeeds."""
    with patch.object(hindsight_service, "recall_memory", AsyncMock(return_value=[])), \
         patch.object(hindsight_service, "retain_knowledge_records", AsyncMock(return_value=0)), \
         patch.object(genai.GenerativeModel, "generate_content_async", AsyncMock(return_value=mock_gemini_review_response)):

        # Exact legacy payload
        response = await async_client.post(
            "/review",
            json={
                "code": "print('hello')",
                "language": "python"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "issues" in data
        assert data["issues"]["critical"] == 0
        assert data["issues"]["high"] == 1
        assert len(data["details"]) == 1


@pytest.mark.asyncio
async def test_existing_rewrite_endpoint_preserved(
    async_client,
    mock_gemini_rewrite_response
):
    """Verify that /rewrite endpoint continues working untouched."""
    with patch.object(genai.GenerativeModel, "generate_content_async", AsyncMock(return_value=mock_gemini_rewrite_response)):
        response = await async_client.post(
            "/rewrite",
            json={
                "code": "def add(a, b): return a+b",
                "language": "python"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "optimized_code" in data
        assert "metrics" in data
        assert "diff" in data
        assert data["metrics"]["time_complexity"] == "O(1)"


@pytest.mark.asyncio
async def test_memory_status_debug_endpoint(async_client):
    """Test developer status endpoint."""
    with patch.object(hindsight_service, "check_health", AsyncMock(return_value={"status": "healthy", "version": "0.10.1"})):
        response = await async_client.get("/memory/status")
        assert response.status_code == 200
        data = response.json()
        assert "hindsight_health" in data
        assert data["hindsight_health"]["status"] == "healthy"
        assert "config" in data
        assert data["config"]["gemini_api_key_configured"] is True


@pytest.mark.asyncio
async def test_memory_recall_debug_endpoint(async_client):
    """Test developer recall debug endpoint."""
    mock_mem = [{"id": "m1", "text": "Convention", "category": "convention"}]
    with patch.object(hindsight_service, "recall_memory", AsyncMock(return_value=mock_mem)):
        response = await async_client.post(
            "/memory/recall-debug",
            json={"query": "test query", "project_id": "test-p"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == "test-p"
        assert data["memories_count"] == 1
        assert "Established Project Conventions" in data["formatted_context"]
