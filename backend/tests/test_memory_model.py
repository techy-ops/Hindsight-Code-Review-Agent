import pytest
from memory_model import sanitize_text, extract_durable_knowledge, MemoryRecord


def test_sanitize_text_redacts_keys_and_passwords():
    raw_text = (
        "Found hardcoded key: AIzaSyDjsizdWXqGiem4JLWyZIQGOJGdZdKC_Mc and "
        "openai: sk-1234567890abcdef1234567890 and "
        "AWS: AKIA1234567890ABCDEF and "
        "bearer: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz and "
        "password = 'super_secret_password_123'"
    )
    sanitized = sanitize_text(raw_text)
    assert "AIzaSyDjsizdWXqGiem4JLWyZIQGOJGdZdKC_Mc" not in sanitized
    assert "sk-1234567890abcdef1234567890" not in sanitized
    assert "AKIA1234567890ABCDEF" not in sanitized
    assert "super_secret_password_123" not in sanitized
    assert "[REDACTED" in sanitized


def test_extract_durable_knowledge_normal_review():
    review_output = {
        "issues": {"critical": 1, "high": 1, "medium": 1, "low": 0},
        "details": [
            {
                "severity": "critical",
                "title": "SQL Injection Vulnerability",
                "description": "User input is directly concatenated into database query string.",
                "suggestion": "Use parameterized queries with SQLAlchemy or asyncpg."
            },
            {
                "severity": "high",
                "title": "O(N^2) Performance Bottleneck in nested iteration",
                "description": "Nested loop causes exponential time complexity on large datasets.",
                "suggestion": "Use dictionary indexing for O(1) lookups."
            },
            {
                "severity": "medium",
                "title": "Repository Pattern Architectural Rule",
                "description": "Direct database queries inside controller violate repository abstraction.",
                "suggestion": "Route queries through the repository layer."
            },
            {
                "severity": "low",
                "title": "Naming Convention Inconsistency",
                "description": "Variable names use camelCase instead of snake_case.",
                "suggestion": "Use snake_case for all Python variables per PEP 8."
            }
        ]
    }
    code = "def query_user(user_id): return db.execute('SELECT * FROM users WHERE id = ' + user_id)"
    
    records = extract_durable_knowledge(
        code=code,
        language="python",
        review_output=review_output,
        project_id="billing-service"
    )

    assert len(records) == 4
    categories = [r.category for r in records]
    assert "vulnerability" in categories
    assert "performance" in categories
    assert "architecture" in categories
    assert "convention" in categories

    # Verify project isolation tags
    for r in records:
        assert r.project_id == "billing-service"
        assert r.language == "python"
        assert "project:billing-service" in r.tags
        assert "lang:python" in r.tags


def test_extract_durable_knowledge_handles_empty_or_malformed():
    assert extract_durable_knowledge("", "python", {}) == []
    assert extract_durable_knowledge("code", "python", {"details": "not-a-list"}) == []
    assert extract_durable_knowledge("code", "python", {"details": [{}]}) == []
