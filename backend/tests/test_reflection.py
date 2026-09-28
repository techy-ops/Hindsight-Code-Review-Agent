import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import google.generativeai as genai
from main import app, hindsight_service
from config import Settings


@pytest.fixture
def mock_gemini_review_response():
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({
        "issues": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "details": []
    })
    return mock_resp


def test_reflection_endpoint_success(client):
    mock_reflection_data = {
        "text": "Project consistently uses repository pattern and rejects raw SQL queries.",
        "based_on": ["Mem 1", "Mem 2"],
        "project_id": "test-proj",
        "developer_id": "dev-1"
    }

    with patch.object(hindsight_service, "reflect_memory", AsyncMock(return_value=mock_reflection_data)):
        res = client.post(
            "/memory/reflect",
            json={
                "project_id": "test-proj",
                "developer_id": "dev-1",
                "query": "Synthesize team conventions"
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["project_id"] == "test-proj"
        assert data["developer_id"] == "dev-1"
        assert "consistently uses repository pattern" in data["reflection"]["text"]


def test_reflection_endpoint_failure_fallback(client):
    with patch.object(hindsight_service, "reflect_memory", AsyncMock(return_value=None)):
        res = client.post(
            "/memory/reflect",
            json={
                "project_id": "test-proj"
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["reflection"] is None


def test_review_triggers_reflection_when_sufficient_memories(
    client,
    mock_gemini_review_response
):
    # 3 memories (exceeds min_memories_for_reflection=2)
    mock_memories = [
        {"id": "m1", "text": "Convention 1", "category": "convention"},
        {"id": "m2", "text": "Convention 2", "category": "convention"},
        {"id": "m3", "text": "Convention 3", "category": "convention"},
    ]

    mock_reflection = {
        "text": "The team strictly adheres to layered architecture and typing conventions.",
        "based_on": ["Convention 1", "Convention 2"],
        "project_id": "proj-x"
    }

    with patch.object(hindsight_service, "recall_memory", AsyncMock(return_value=mock_memories)), \
         patch.object(hindsight_service, "reflect_memory", AsyncMock(return_value=mock_reflection)) as mock_reflect, \
         patch.object(hindsight_service, "retain_knowledge_records", AsyncMock(return_value=0)), \
         patch.object(genai.GenerativeModel, "generate_content_async", AsyncMock(return_value=mock_gemini_review_response)) as mock_ai:

        res = client.post(
            "/review",
            json={
                "code": "def process(): pass",
                "language": "python",
                "project_id": "proj-x",
                "developer_id": "dev-sam"
            }
        )
        assert res.status_code == 200
        data = res.json()

        # Confirm reflection was called
        assert mock_reflect.called
        assert data["memory"]["reflection_applied"] is True
        assert "strictly adheres to layered architecture" in data["memory"]["reflection_summary"]

        # Confirm prompt sent to Gemini contains the synthesized reflection
        prompt_sent = mock_ai.call_args[0][0]
        assert "[Synthesized Higher-Order Reflection (Hindsight Reflect)]" in prompt_sent
        assert "strictly adheres to layered architecture" in prompt_sent


def test_review_skips_reflection_when_insufficient_memories(
    client,
    mock_gemini_review_response
):
    # Only 1 memory (< 2)
    mock_memories = [
        {"id": "m1", "text": "Single memory", "category": "observation"}
    ]

    with patch.object(hindsight_service, "recall_memory", AsyncMock(return_value=mock_memories)), \
         patch.object(hindsight_service, "reflect_memory", AsyncMock()) as mock_reflect, \
         patch.object(hindsight_service, "retain_knowledge_records", AsyncMock(return_value=0)), \
         patch.object(genai.GenerativeModel, "generate_content_async", AsyncMock(return_value=mock_gemini_review_response)):

        res = client.post(
            "/review",
            json={
                "code": "def run(): pass",
                "language": "python",
                "project_id": "proj-y"
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert not mock_reflect.called
        assert data["memory"]["reflection_applied"] is False
