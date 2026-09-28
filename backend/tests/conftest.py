import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Set test environment variables before importing app
os.environ["GEMINI_API_KEY"] = "mock-test-gemini-key-1234567890"
os.environ["HINDSIGHT_ENABLED"] = "true"
os.environ["HINDSIGHT_BASE_URL"] = "http://localhost:8888"
os.environ["HINDSIGHT_BANK_ID"] = "test-bank"
os.environ["DEFAULT_PROJECT_ID"] = "test-project"

from main import app
from config import Settings


@pytest.fixture
def test_settings():
    return Settings(
        gemini_api_key="mock-gemini-key",
        gemini_model="gemini-2.5-flash",
        hindsight_enabled=True,
        hindsight_base_url="http://localhost:8888",
        hindsight_bank_id="test-bank",
        default_project_id="test-project",
    )


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
