"""End-to-End Productization Test for Phase 3:
Review 1 -> Feedback Reject -> Verify Stats/Timeline -> Review 2 -> Verify Explainability & Explorer.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from activity_tracker import get_activity_tracker


@pytest.fixture(autouse=True)
def reset_tracker():
    tracker = get_activity_tracker()
    tracker.reset_for_tests()
    yield
    tracker.reset_for_tests()


@pytest.mark.asyncio
async def test_phase3_end_to_end_productized_learning_workflow(monkeypatch):
    """Verify complete Phase 3 productized workflow:
    1. Check initial empty dashboard stats.
    2. Run Review 1 (baseline) -> generates Redis suggestion.
    3. Submit Developer Feedback (Reject Redis -> project uses PostgreSQL caching).
    4. Verify timeline and dashboard stats reflect real activity.
    5. Run Review 2 -> memory is recalled, Redis suppressed, and explainability tags as LEARNED CONTEXT.
    6. Verify memory explorer contains the durable feedback item.
    """
    import main

    # 1. Initial truthful dashboard state
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/dashboard/stats")
        assert resp.status_code == 200
        stats = resp.json()["stats"]
        assert stats["total_reviews"] == 0
        assert stats["feedback_events"]["total"] == 0

    # 2. Review 1 - Baseline review proposing Redis caching
    async def fake_review1_llm(*args, **kwargs):
        class FakeResponse:
            text = """{
                "issues": {"critical": 0, "high": 1, "medium": 0, "low": 0},
                "details": [
                    {
                        "severity": "high",
                        "title": "Slow Query Performance",
                        "description": "Repeated database queries detected without caching layer.",
                        "suggestion": "Use Redis distributed caching for session lookups."
                    }
                ]
            }"""
        return FakeResponse()

    monkeypatch.setattr(main.genai.GenerativeModel, "generate_content_async", fake_review1_llm)

    # First review: no memories in Hindsight
    async def fake_recall_empty(*args, **kwargs):
        return []

    monkeypatch.setattr(main.hindsight_service, "recall_memory", fake_recall_empty)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.post("/review", json={
            "code": "def get_session(token): return db.query('SELECT * FROM sessions WHERE token = ?', token)",
            "language": "python",
            "project_id": "cache-service-v3",
            "developer_id": "dev-alice",
        })
        assert r1.status_code == 200
        data1 = r1.json()
        assert data1["details"][0]["origin"] == "new_finding"
        assert data1["details"][0]["influenced_by_memory"] is False
        assert "Redis" in data1["details"][0]["suggestion"]

    # 3. Submit Developer Feedback: Reject Redis
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        fb_resp = await ac.post("/review/feedback", json={
            "project_id": "cache-service-v3",
            "developer_id": "dev-alice",
            "action": "reject",
            "issue_title": "Slow Query Performance",
            "recommendation": "Use Redis distributed caching for session lookups.",
            "reason": "Project standardizes on PostgreSQL unlogged tables for caching; Redis is not allowed.",
            "language": "python"
        })
        assert fb_resp.status_code == 200
        assert fb_resp.json()["status"] == "recorded"
        assert fb_resp.json()["action"] == "reject"

    # 4. Verify Dashboard & Timeline have updated with real data
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        stats_resp = await ac.get("/dashboard/stats")
        stats2 = stats_resp.json()["stats"]
        assert stats2["total_reviews"] == 1
        assert stats2["feedback_events"]["total"] == 1
        assert stats2["feedback_events"]["rejected"] == 1

        timeline_resp = await ac.get("/learning/timeline?project_id=cache-service-v3")
        timeline = timeline_resp.json()["events"]
        assert len(timeline) >= 2
        assert timeline[0]["type"] == "feedback_reject"
        assert timeline[1]["type"] == "review"

    # 5. Review 2 - Next review recalls the rejected suggestion
    async def fake_review2_llm(self, prompt, *args, **kwargs):
        # Prompt must include the negative constraint from MemoryContextBuilder
        assert "DO NOT RECOMMEND" in prompt or "REJECTED" in prompt
        assert "Redis" in prompt

        class FakeResponse:
            text = """{
                "issues": {"critical": 0, "high": 1, "medium": 0, "low": 0},
                "details": [
                    {
                        "severity": "high",
                        "title": "Uncached Query Bottleneck",
                        "description": "Query lacks caching; aligns with PostgreSQL caching convention.",
                        "suggestion": "Use PostgreSQL unlogged caching table adhering to project memory."
                    }
                ]
            }"""
        return FakeResponse()

    monkeypatch.setattr(main.genai.GenerativeModel, "generate_content_async", fake_review2_llm)

    # Mock recall to return the rejected recommendation memory
    recalled_rejected_mem = [
        {
            "text": "Developer rejected 'Slow Query Performance': Use Redis. Reason: Project standardizes on PostgreSQL unlogged tables for caching; Redis is not allowed.",
            "category": "rejected_pattern",
            "metadata": {"category": "rejected_pattern"}
        }
    ]

    async def fake_recall_with_rejected(*args, **kwargs):
        return recalled_rejected_mem

    monkeypatch.setattr(main.hindsight_service, "recall_memory", fake_recall_with_rejected)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r2 = await ac.post("/review", json={
            "code": "def get_user_stats(uid): return db.query('SELECT * FROM stats WHERE user_id = ?', uid)",
            "language": "python",
            "project_id": "cache-service-v3",
            "developer_id": "dev-alice",
        })
        assert r2.status_code == 200
        data2 = r2.json()

        # Verify adaptation:
        # 1. No Redis
        assert "Redis" not in data2["details"][0]["suggestion"]
        assert "PostgreSQL" in data2["details"][0]["suggestion"]
        # 2. Explainability tags
        assert data2["details"][0]["origin"] == "learned_context"
        assert data2["details"][0]["influenced_by_memory"] is True
        assert data2["details"][0]["evidence_level"] == "repeated_pattern"
        assert "explainability" in data2
        assert data2["explainability"]["learned_context_findings_count"] == 1

    # 6. Verify Memory Explorer contains the feedback record
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        explorer_resp = await ac.get("/memory/explorer?project_id=cache-service-v3")
        assert explorer_resp.status_code == 200
        memories = explorer_resp.json()["memories"]
        assert len(memories) >= 1
        assert any("Redis" in m["text"] for m in memories)
