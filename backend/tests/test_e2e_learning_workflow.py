import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import google.generativeai as genai
from main import app, hindsight_service


def test_e2e_feedback_rejection_learning_lifecycle(client):
    """End-to-End Phase 2 Workflow Test:
    
    1. REVIEW 1:
       - Code submitted for project 'search-service' (Developer 'dan')
       - Agent reviews code and suggests: "Use Redis caching for search query results"
    
    2. FEEDBACK ACTION:
       - Developer rejects the suggestion with reason: "Project uses Memcached cluster"
       - Feedback is submitted via POST /review/feedback
       - Feedback is persisted into Hindsight as a negative constraint memory
    
    3. REVIEW 2+:
       - Developer 'dan' submits new search caching code in 'search-service'
       - Hindsight recalls the rejected decision
       - Reflection / context builder injects DO NOT RECOMMEND 'Use Redis' and reinforces 'Memcached'
       - Reviewer prompt receives the negative constraint
       - LLM generates a personalized review that respects the decision and suggests Memcached instead of Redis!
    
    4. ISOLATION CHECK:
       - A review in an unrelated project 'analytics-service' does NOT receive 'search-service' rejection memories.
    """
    project_id = "search-service"
    developer_id = "dan"

    # Simulated in-memory persistent store
    hindsight_memory_bank = []

    async def fake_retain(project_id, language, content, metadata=None, tags=None, **kwargs):
        hindsight_memory_bank.append({
            "id": f"mem-{len(hindsight_memory_bank)+1}",
            "text": content,
            "category": metadata.get("category", "observation") if metadata else "observation",
            "metadata": metadata or {},
            "tags": tags or []
        })
        return True

    async def fake_recall(project_id, query, language=None, developer_id=None, limit=None, **kwargs):
        # Strict project scoping
        matched = [
            m for m in hindsight_memory_bank
            if f"project:{project_id}" in m.get("tags", [])
        ]
        return matched[:limit] if limit else matched

    async def fake_reflect(project_id, query, developer_id=None, tags=None, **kwargs):
        # Synthesize from memories matching this project
        project_memories = [m for m in hindsight_memory_bank if f"project:{project_id}" in m.get("tags", [])]
        if any("Memcached" in m["text"] for m in project_memories):
            return {
                "text": "Team policy: Memcached is the established caching layer; Redis caching proposals are rejected.",
                "based_on": ["Developer rejected Redis in favor of Memcached"],
                "project_id": project_id,
                "developer_id": developer_id
            }
        return None

    with patch.object(hindsight_service, "retain_memory", side_effect=fake_retain), \
         patch.object(hindsight_service, "recall_memory", side_effect=fake_recall), \
         patch.object(hindsight_service, "reflect_memory", side_effect=fake_reflect):

        # -----------------------------------------------------------------
        # STEP 1: REVIEW 1 - Initial review suggests Redis
        # -----------------------------------------------------------------
        review_1_ai_response = MagicMock()
        review_1_ai_response.text = json.dumps({
            "issues": {"critical": 0, "high": 1, "medium": 0, "low": 0},
            "details": [
                {
                    "severity": "high",
                    "title": "Uncached Search Queries",
                    "description": "Search queries execute directly on database without a cache.",
                    "suggestion": "Use Redis caching for search query results."
                }
            ]
        })

        with patch.object(genai.GenerativeModel, "generate_content_async", AsyncMock(return_value=review_1_ai_response)):
            res1 = client.post(
                "/review",
                json={
                    "code": "def search(q): return db.query(f'SELECT * FROM items WHERE text LIKE %{q}%')",
                    "language": "python",
                    "project_id": project_id,
                    "developer_id": developer_id
                }
            )
            assert res1.status_code == 200
            data1 = res1.json()
            assert data1["details"][0]["suggestion"] == "Use Redis caching for search query results."

        # -----------------------------------------------------------------
        # STEP 2: FEEDBACK - Developer rejects Redis in favor of Memcached
        # -----------------------------------------------------------------
        feedback_res = client.post(
            "/review/feedback",
            json={
                "project_id": project_id,
                "developer_id": developer_id,
                "issue_title": "Uncached Search Queries",
                "recommendation": "Use Redis caching for search query results.",
                "action": "reject",
                "reason": "Project uses Memcached cluster for all query caching",
                "language": "python"
            }
        )
        assert feedback_res.status_code == 200
        fb_data = feedback_res.json()
        assert fb_data["status"] == "recorded"
        assert fb_data["retained"] is True

        # Confirm memory was stored in Hindsight
        assert len(hindsight_memory_bank) >= 1
        reject_record = next(m for m in hindsight_memory_bank if "REJECTED" in m["text"])
        assert "Memcached cluster" in reject_record["text"]
        assert "category:rejected_recommendation" in reject_record["tags"]

        # -----------------------------------------------------------------
        # STEP 3: REVIEW 2 - Subsequent review recognizes the rejected pattern
        # -----------------------------------------------------------------
        review_2_ai_response = MagicMock()
        review_2_ai_response.text = json.dumps({
            "issues": {"critical": 0, "high": 0, "medium": 1, "low": 0},
            "details": [
                {
                    "severity": "medium",
                    "title": "Caching Optimization with Memcached",
                    "description": "Cache missing for product queries. Aligns with team preference for Memcached.",
                    "suggestion": "Integrate with the team's Memcached cluster."
                }
            ]
        })

        with patch.object(genai.GenerativeModel, "generate_content_async", AsyncMock(return_value=review_2_ai_response)) as mock_ai_2:
            res2 = client.post(
                "/review",
                json={
                    "code": "def search_products(q): return db.query(q)",
                    "language": "python",
                    "project_id": project_id,
                    "developer_id": developer_id
                }
            )
            assert res2.status_code == 200
            data2 = res2.json()

            # Verify prompt sent to Gemini received the negative constraint and reflection!
            prompt_sent = mock_ai_2.call_args[0][0]
            assert "[Team Decisions: REJECTED Suggestions (DO NOT REPEAT)]" in prompt_sent
            assert "DO NOT RECOMMEND:" in prompt_sent
            assert "Redis" in prompt_sent
            assert "Memcached" in prompt_sent
            assert "[Synthesized Higher-Order Reflection (Hindsight Reflect)]" in prompt_sent

            # Review output aligns with learned pattern
            assert "Memcached" in data2["details"][0]["suggestion"]
            assert data2["memory"]["reflection_applied"] is True

        # -----------------------------------------------------------------
        # STEP 4: ISOLATION - Unrelated project does not receive these memories
        # -----------------------------------------------------------------
        with patch.object(genai.GenerativeModel, "generate_content_async", AsyncMock(return_value=review_1_ai_response)) as mock_ai_unrelated:
            res_unrelated = client.post(
                "/review",
                json={
                    "code": "def get_stats(): pass",
                    "language": "python",
                    "project_id": "analytics-service",  # Different project!
                    "developer_id": "other-dev"
                }
            )
            assert res_unrelated.status_code == 200
            prompt_unrelated = mock_ai_unrelated.call_args[0][0]
            # Must NOT contain search-service's Memcached/Redis rejection
            assert "search-service" not in prompt_unrelated
            assert "DO NOT RECOMMEND: Project 'search-service'" not in prompt_unrelated
