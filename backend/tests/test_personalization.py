import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import google.generativeai as genai
from main import app, hindsight_service
from memory_model import calibrate_confidence_wording
from memory_context_builder import build_memory_context


def test_rejected_recommendation_suppression_in_prompt():
    memories = [
        {
            "id": "mem-rej-1",
            "text": "Project 'orders-service' team decision [REJECTED]: Suggestion 'Use Redis for order caching' was REJECTED. Reason: 'Order caching uses internal SQLite in-memory'. Policy: Do NOT suggest 'Use Redis for order caching'.",
            "category": "rejected_recommendation",
            "tags": ["project:orders-service", "category:rejected_recommendation"]
        },
        {
            "id": "mem-conv-1",
            "text": "Always use Pydantic models for request bodies.",
            "category": "convention",
            "tags": ["project:orders-service", "category:convention"]
        }
    ]

    context = build_memory_context(memories, project_id="orders-service", language="python")
    
    # Must contain high priority section instructing the reviewer NOT to repeat the rejected suggestion
    assert "[Team Decisions: REJECTED Suggestions (DO NOT REPEAT)]" in context
    assert "DO NOT RECOMMEND:" in context
    assert "Use Redis for order caching" in context
    assert "CRITICAL REVIEW POLICIES:" in context
    assert "DO NOT recommend practices that have been explicitly REJECTED" in context


def test_developer_memory_scoping_and_isolation():
    # Memories for developer Alice and developer Bob
    mem_alice = [
        {
            "id": "m1",
            "text": "Developer 'alice' prefers functional list comprehensions over map/filter.",
            "category": "convention",
            "metadata": {"developer_id": "alice"},
            "tags": ["project:core-api", "developer:alice"]
        }
    ]
    mem_bob = [
        {
            "id": "m2",
            "text": "Developer 'bob' prefers explicit for-loops with detailed logging.",
            "category": "convention",
            "metadata": {"developer_id": "bob"},
            "tags": ["project:core-api", "developer:bob"]
        }
    ]

    # Context for Alice
    context_alice = build_memory_context(mem_alice, project_id="core-api", developer_id="alice")
    assert "[Developer Personalization (alice)]" in context_alice
    assert "list comprehensions" in context_alice
    assert "bob" not in context_alice

    # Context for Bob
    context_bob = build_memory_context(mem_bob, project_id="core-api", developer_id="bob")
    assert "[Developer Personalization (bob)]" in context_bob
    assert "explicit for-loops" in context_bob
    assert "alice" not in context_bob


def test_confidence_calibration_wording():
    # 1 occurrence -> cautious phrasing
    wording_isolated = calibrate_confidence_wording("Use structlog for structured logging", frequency=1)
    assert wording_isolated.startswith("Observed in prior review:")
    assert "always" not in wording_isolated.lower()

    # 2-3 occurrences -> frequent pattern
    wording_frequent = calibrate_confidence_wording("Use dataclasses for DTOs", frequency=2)
    assert wording_frequent.startswith("Frequent project pattern:")

    # 4+ occurrences or explicit convention -> established convention
    wording_convention = calibrate_confidence_wording("PEP 8 snake_case naming", frequency=5, is_explicit_convention=True)
    assert wording_convention.startswith("Established team convention:")


def test_project_memory_scoping_isolation():
    bank_project_a = hindsight_service.resolve_bank_id("checkout-service")
    bank_project_b = hindsight_service.resolve_bank_id("inventory-service")

    # Distinct namespaces
    assert bank_project_a != bank_project_b
    assert "checkout-service" in bank_project_a
    assert "inventory-service" in bank_project_b
