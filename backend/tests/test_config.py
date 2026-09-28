import os
import pytest
from config import Settings, get_settings


def test_config_loads_defaults():
    settings = Settings()
    assert settings.hindsight_bank_id is not None
    assert settings.hindsight_timeout > 0
    assert settings.hindsight_max_recall_results >= 1
    assert settings.default_project_id is not None


def test_config_env_overrides(monkeypatch):
    monkeypatch.setenv("HINDSIGHT_BANK_ID", "custom-bank-name")
    monkeypatch.setenv("HINDSIGHT_TIMEOUT", "15.5")
    monkeypatch.setenv("HINDSIGHT_MAX_RECALL_RESULTS", "10")
    monkeypatch.setenv("HINDSIGHT_ENABLED", "false")

    settings = Settings()
    assert settings.hindsight_bank_id == "custom-bank-name"
    assert settings.hindsight_timeout == 15.5
    assert settings.hindsight_max_recall_results == 10
    assert settings.hindsight_enabled is False


def test_config_safe_dict_never_exposes_secrets():
    settings = Settings(
        gemini_api_key="super-secret-gemini-key",
        hindsight_api_key="super-secret-hindsight-token",
    )
    safe = settings.safe_dict()
    # Confirm raw keys are never in safe_dict
    assert "super-secret-gemini-key" not in str(safe)
    assert "super-secret-hindsight-token" not in str(safe)
    assert safe["gemini_api_key_configured"] is True
    assert safe["hindsight_api_key_configured"] is True
