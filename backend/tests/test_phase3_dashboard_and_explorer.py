"""Tests for Phase 3: Dashboard, Memory Explorer, Learning Timeline, and Review Explainability."""

import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from activity_tracker import get_activity_tracker
from memory_context_builder import enrich_review_explainability


@pytest.fixture(autouse=True)
def reset_tracker():
    """Reset activity tracker before each test."""
    tracker = get_activity_tracker()
    tracker.reset_for_tests()
    yield
    tracker.reset_for_tests()


@pytest.mark.asyncio
async def test_dashboard_stats_endpoint_returns_real_data():
    """Verify /dashboard/stats returns real operational numbers from activity tracker."""
    tracker = get_activity_tracker()
    tracker.record_review("test-proj", "python", issues_count=2, influenced_by_memory=True, memories_recalled_count=3)
    tracker.record_retention("test-proj", retained_count=2)
    tracker.record_feedback("test-proj", action="reject", issue_title="Use Redis", reason="Stack uses Postgres")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "hindsight_health" in data
        assert "stats" in data
        stats = data["stats"]
        assert stats["total_reviews"] == 1
        assert stats["memories_recalled"] == 3
        assert stats["memories_retained"] == 2
        assert stats["feedback_events"]["total"] == 1
        assert stats["feedback_events"]["rejected"] == 1
        assert stats["feedback_events"]["accepted"] == 0


@pytest.mark.asyncio
async def test_dashboard_stats_empty_state():
    """Verify truthful empty state when no activity has occurred."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        stats = data["stats"]
        assert stats["total_reviews"] == 0
        assert stats["memories_retained"] == 0
        assert stats["memories_recalled"] == 0
        assert stats["feedback_events"]["total"] == 0


@pytest.mark.asyncio
async def test_memory_explorer_filtering_and_search():
    """Verify /memory/explorer returns memories and filters correctly."""
    tracker = get_activity_tracker()
    tracker.record_retention(
        "proj-alpha",
        retained_count=1,
        records=[{
            "id": "rec-1",
            "text": "Project 'proj-alpha' convention: Always use repository pattern.",
            "category": "convention",
            "source": "review_finding",
        }]
    )
    tracker.record_feedback(
        "proj-alpha",
        action="reject",
        issue_title="Use Redis caching",
        recommendation="Cache results with Redis",
        reason="Stack standardizes on Memcached",
    )
    tracker.record_retention(
        "proj-beta",
        retained_count=1,
        records=[{
            "id": "rec-2",
            "text": "Project 'proj-beta' rule: All HTTP endpoints must authenticate with JWT.",
            "category": "convention",
            "source": "review_finding",
        }]
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Search for Redis in proj-alpha
        resp = await ac.get("/memory/explorer?project_id=proj-alpha&search=Redis")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert "Redis" in data["memories"][0]["text"]

        # 2. Filter by category
        resp = await ac.get("/memory/explorer?category=convention")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["memories"]) >= 2

        # 3. Filter by project
        resp = await ac.get("/memory/explorer?project_id=proj-beta")
        assert resp.status_code == 200
        data = resp.json()
        assert all(m.get("project_id") == "proj-beta" for m in data["memories"])


@pytest.mark.asyncio
async def test_learning_timeline_endpoint():
    """Verify /learning/timeline records events chronologically."""
    tracker = get_activity_tracker()
    tracker.record_review("demo-proj", "python", issues_count=1)
    tracker.record_feedback("demo-proj", action="accept", issue_title="Direct DB Access", recommendation="Use repository")
    tracker.record_reflection("demo-proj", summary_text="Team enforces repository pattern across data layer", facts_count=3)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/learning/timeline?project_id=demo-proj")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        event_types = [e["type"] for e in data["events"]]
        # Latest first
        assert event_types[0] == "reflection"
        assert event_types[1] == "feedback_accept"
        assert event_types[2] == "review"


@pytest.mark.asyncio
async def test_demo_scenarios_endpoint():
    """Verify /demo/scenarios returns Before/After demonstration workflows."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/demo/scenarios")
        assert resp.status_code == 200
        data = resp.json()
        assert "scenarios" in data
        assert len(data["scenarios"]) >= 2
        s1 = data["scenarios"][0]
        assert "step1" in s1 and "step2" in s1 and "step3" in s1
        assert "code" in s1["step1"]


def test_review_explainability_enrichment_logic():
    """Verify review explainability truthfully distinguishes new findings from learned context."""
    raw_details = [
        {
            "severity": "high",
            "title": "Bypassing Repository Pattern",
            "description": "Direct database query execution detected in endpoint handler.",
            "suggestion": "Refactor to use UserRepository abstraction.",
        },
        {
            "severity": "medium",
            "title": "Unclosed File Descriptor",
            "description": "File handle opened with open() without context manager.",
            "suggestion": "Use with open('file.txt') as f: block.",
        },
    ]

    recalled_memories = [
        {
            "text": "Project 'auth-service' convention: Always use repository pattern for database access.",
            "category": "convention",
        }
    ]

    reflection = {
        "text": "Project strictly mandates repository pattern for all database calls.",
        "based_on": ["Memory 1", "Memory 2"],
    }

    result = enrich_review_explainability(
        details=raw_details,
        memories=recalled_memories,
        reflection=reflection,
    )

    enriched = result["details"]
    assert len(enriched) == 2

    # Issue 1: Matched repository pattern convention
    assert enriched[0]["origin"] == "learned_context"
    assert enriched[0]["influenced_by_memory"] is True
    assert enriched[0]["evidence_level"] == "established_convention"
    assert enriched[0]["relevant_memory"] is not None

    # Issue 2: Standard new finding, uninfluenced by memory
    assert enriched[1]["origin"] == "new_finding"
    assert enriched[1]["influenced_by_memory"] is False
    assert enriched[1]["evidence_level"] == "none"
    assert enriched[1]["relevant_memory"] is None

    # Top-level explainability metadata
    explain = result["explainability"]
    assert explain["total_findings"] == 2
    assert explain["learned_context_findings_count"] == 1
    assert explain["new_findings_count"] == 1
    assert len(explain["conventions_applied"]) >= 1
