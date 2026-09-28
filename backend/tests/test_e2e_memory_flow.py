import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import google.generativeai as genai
from main import app, hindsight_service


def test_end_to_end_memory_lifecycle(client):
    """Proves the complete Phase 1 lifecycle:
    
    CYCLE 1 (First Review):
    - No existing memory in Hindsight for the project
    - Agent generates review recommending: "Establish Repository Pattern"
    - Durable knowledge is extracted and retained into Hindsight
    
    CYCLE 2 (Subsequent Review):
    - Hindsight recalls the memory created in Cycle 1
    - Memory context builder formats and injects it into LLM prompt
    - Memory-aware review is generated: "Bypasses previously established Repository Pattern"
    """
    project_id = "payments-microservice"
    
    # In-memory store simulating Hindsight persistent memory bank
    persisted_bank = []

    # Mock Gemini review 1 response
    first_review_ai_response = MagicMock()
    first_review_ai_response.text = json.dumps({
        "issues": {"critical": 0, "high": 1, "medium": 0, "low": 0},
        "details": [
            {
                "severity": "high",
                "title": "Establish Repository Pattern",
                "description": "Database queries should be isolated in a dedicated repository layer rather than raw queries in handlers.",
                "suggestion": "Introduce PaymentRepository to handle queries."
            }
        ]
    })

    # Mock Gemini review 2 response (memory-aware)
    second_review_ai_response = MagicMock()
    second_review_ai_response.text = json.dumps({
        "issues": {"critical": 0, "high": 1, "medium": 0, "low": 0},
        "details": [
            {
                "severity": "high",
                "title": "Bypassing Repository Pattern",
                "description": "This implementation bypasses the repository pattern previously established for payments-microservice.",
                "suggestion": "Route this call through PaymentRepository."
            }
        ]
    })

    async def fake_retain(project_id, language, content, metadata=None, tags=None, **kwargs):
        persisted_bank.append({
            "id": f"mem-{len(persisted_bank)+1}",
            "text": content,
            "category": metadata.get("category", "architecture") if metadata else "architecture",
            "metadata": metadata or {},
            "tags": tags or []
        })
        return True

    async def fake_recall(project_id, query, language=None, developer_id=None, limit=None, **kwargs):
        # Return memories matching this project
        return [m for m in persisted_bank if f"project:{project_id}" in m.get("tags", [])]

    with patch.object(hindsight_service, "retain_memory", side_effect=fake_retain), \
         patch.object(hindsight_service, "recall_memory", side_effect=fake_recall):

        # -------------------------------------------------------------
        # FIRST REVIEW: Clean project without historical memory
        # -------------------------------------------------------------
        with patch.object(genai.GenerativeModel, "generate_content_async", AsyncMock(return_value=first_review_ai_response)) as mock_ai_1:
            resp1 = client.post(
                "/review",
                json={
                    "code": "def process_payment(db, amount): return db.execute('INSERT INTO payments ...')",
                    "language": "python",
                    "project_id": project_id
                }
            )
            assert resp1.status_code == 200
            data1 = resp1.json()

            # Confirm first review had no memory applied
            assert data1["memory"]["status"] == "no_memories"
            assert data1["memory"]["memories_retrieved"] == 0
            assert data1["memory"]["learning_context_applied"] is False
            # Verify memory was extracted and retained into Hindsight
            assert len(persisted_bank) >= 1
            assert any("Repository Pattern" in m["text"] for m in persisted_bank)

            # Confirm LLM prompt for review 1 had NO memory block
            prompt_1 = mock_ai_1.call_args[0][0]
            assert "=== BEGIN HISTORICAL PROJECT MEMORY" not in prompt_1

        # -------------------------------------------------------------
        # SECOND REVIEW: Subsequent code in same project
        # -------------------------------------------------------------
        with patch.object(genai.GenerativeModel, "generate_content_async", AsyncMock(return_value=second_review_ai_response)) as mock_ai_2:
            resp2 = client.post(
                "/review",
                json={
                    "code": "def refund_payment(db, refund_id): return db.execute('UPDATE payments ...')",
                    "language": "python",
                    "project_id": project_id
                }
            )
            assert resp2.status_code == 200
            data2 = resp2.json()

            # Confirm second review recalled prior memory
            assert data2["memory"]["status"] == "recalled"
            assert data2["memory"]["memories_retrieved"] >= 1
            assert data2["memory"]["learning_context_applied"] is True

            # Confirm LLM prompt for review 2 DID receive the recalled memory context!
            prompt_2 = mock_ai_2.call_args[0][0]
            assert "=== BEGIN HISTORICAL PROJECT MEMORY (HINDSIGHT) ===" in prompt_2
            assert "payments-microservice" in prompt_2
            assert "Repository Pattern" in prompt_2
            assert "CRITICAL MEMORY INSTRUCTIONS:" in prompt_2

            # Confirm review result reflects the memory-aware finding
            details = data2["details"]
            assert any("Bypassing Repository Pattern" in d["title"] for d in details)
