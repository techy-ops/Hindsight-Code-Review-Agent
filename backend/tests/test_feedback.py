import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from main import app, hindsight_service
from memory_model import FeedbackRequest, create_feedback_memory_record


def test_feedback_request_validation():
    # Valid actions
    fb1 = FeedbackRequest(
        project_id="test-p",
        issue_title="Bug",
        recommendation="Fix it",
        action="accept"
    )
    assert fb1.action == "accept"

    fb2 = FeedbackRequest(
        project_id="test-p",
        issue_title="Bug",
        recommendation="Fix it",
        action="reject",
        reason="Not applicable"
    )
    assert fb2.action == "reject"

    fb3 = FeedbackRequest(
        project_id="test-p",
        issue_title="Bug",
        recommendation="Fix it",
        action="fixed"
    )
    assert fb3.action == "fixed"

    # Invalid action raises ValidationError
    with pytest.raises(ValueError):
        FeedbackRequest(
            project_id="test-p",
            issue_title="Bug",
            recommendation="Fix it",
            action="invalid-action"
        )


def test_create_feedback_memory_record_reject():
    fb = FeedbackRequest(
        project_id="billing-api",
        developer_id="dev-carol",
        issue_title="Use Redis caching",
        recommendation="Configure Redis cluster",
        action="reject",
        reason="Project uses PostgreSQL UNLOGGED tables for cache"
    )
    rec = create_feedback_memory_record(fb)
    assert rec.category == "rejected_recommendation"
    assert "REJECTED" in rec.content
    assert "PostgreSQL UNLOGGED tables" in rec.content
    assert "Do NOT suggest 'Configure Redis cluster'" in rec.content
    assert "project:billing-api" in rec.tags
    assert "developer:dev-carol" in rec.tags
    assert "action:reject" in rec.tags


def test_create_feedback_memory_record_accept():
    fb = FeedbackRequest(
        project_id="billing-api",
        developer_id="dev-carol",
        issue_title="Type Annotations",
        recommendation="Add Python type hints to all route handlers",
        action="accept"
    )
    rec = create_feedback_memory_record(fb)
    assert rec.category == "convention"
    assert "ACCEPTED" in rec.content
    assert "project:billing-api" in rec.tags
    assert "action:accept" in rec.tags


def test_create_feedback_memory_record_fixed():
    fb = FeedbackRequest(
        project_id="billing-api",
        issue_title="SQL Injection",
        recommendation="Use parameterized query",
        action="fixed"
    )
    rec = create_feedback_memory_record(fb)
    assert rec.category == "resolution"
    assert "FIXED" in rec.content
    assert "action:fixed" in rec.tags


def test_submit_feedback_accept_endpoint(client):
    with patch.object(hindsight_service, "retain_feedback", AsyncMock(return_value=True)):
        res = client.post(
            "/review/feedback",
            json={
                "project_id": "proj-alpha",
                "developer_id": "dev-1",
                "issue_title": "Use async file I/O",
                "recommendation": "Use aiofiles instead of open()",
                "action": "accept"
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "recorded"
        assert data["action"] == "accept"
        assert data["retained"] is True
        assert data["developer_id"] == "dev-1"


def test_submit_feedback_reject_endpoint(client):
    with patch.object(hindsight_service, "retain_feedback", AsyncMock(return_value=True)):
        res = client.post(
            "/review/feedback",
            json={
                "project_id": "proj-alpha",
                "developer_id": "dev-2",
                "issue_title": "Use Redis Cache",
                "recommendation": "Install redis",
                "action": "reject",
                "reason": "Team standard is Memcached"
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "recorded"
        assert data["action"] == "reject"
        assert data["retained"] is True


def test_submit_feedback_fixed_endpoint(client):
    with patch.object(hindsight_service, "retain_feedback", AsyncMock(return_value=True)):
        res = client.post(
            "/review/feedback",
            json={
                "project_id": "proj-alpha",
                "issue_title": "Missing validation",
                "recommendation": "Add pydantic validator",
                "action": "fixed"
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "recorded"
        assert data["action"] == "fixed"


def test_feedback_failure_does_not_break_review_or_crash_endpoint(client):
    # When Hindsight retain raises an exception or fails
    with patch.object(hindsight_service, "retain_feedback", AsyncMock(side_effect=Exception("Hindsight connection timeout"))):
        res = client.post(
            "/review/feedback",
            json={
                "project_id": "proj-alpha",
                "issue_title": "Test",
                "recommendation": "Rec",
                "action": "accept"
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "recorded"
        assert data["retained"] is False
