"""Configuration module for AI Code Review Agent with Hindsight integration.

Centralizes environment variable loading, validation, and safe defaults.
Never exposes raw secrets or credentials in logs or debug endpoints.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Locate and load .env file from backend directory or parent
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")
load_dotenv(dotenv_path=BASE_DIR.parent / ".env")


class Settings(BaseModel):
    """Application settings and configuration."""
    
    # Gemini configuration
    gemini_api_key: str = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", "")
    )
    gemini_model: str = Field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    )

    # Hindsight configuration
    hindsight_enabled: bool = Field(
        default_factory=lambda: os.getenv("HINDSIGHT_ENABLED", "true").lower() in ("true", "1", "yes")
    )
    hindsight_base_url: str = Field(
        default_factory=lambda: os.getenv("HINDSIGHT_BASE_URL", "http://localhost:8888").rstrip("/")
    )
    hindsight_api_key: str = Field(
        default_factory=lambda: os.getenv("HINDSIGHT_API_KEY", "")
    )
    hindsight_bank_id: str = Field(
        default_factory=lambda: os.getenv("HINDSIGHT_BANK_ID", "code-review-agent")
    )
    hindsight_timeout: float = Field(
        default_factory=lambda: float(os.getenv("HINDSIGHT_TIMEOUT", "10.0"))
    )
    hindsight_max_recall_results: int = Field(
        default_factory=lambda: int(os.getenv("HINDSIGHT_MAX_RECALL_RESULTS", "5"))
    )

    # Phase 2: Reflection and Personalization settings
    hindsight_reflect_enabled: bool = Field(
        default_factory=lambda: os.getenv("HINDSIGHT_REFLECT_ENABLED", "true").lower() in ("true", "1", "yes")
    )
    hindsight_reflect_budget: str = Field(
        default_factory=lambda: os.getenv("HINDSIGHT_REFLECT_BUDGET", "low")
    )
    hindsight_min_memories_for_reflection: int = Field(
        default_factory=lambda: int(os.getenv("HINDSIGHT_MIN_MEMORIES_FOR_REFLECTION", "2"))
    )
    hindsight_developer_memory_enabled: bool = Field(
        default_factory=lambda: os.getenv("HINDSIGHT_DEVELOPER_MEMORY_ENABLED", "true").lower() in ("true", "1", "yes")
    )

    # Scoping defaults
    default_project_id: str = Field(
        default_factory=lambda: os.getenv("DEFAULT_PROJECT_ID", "default-project")
    )

    def is_hindsight_configured(self) -> bool:
        """Check if Hindsight is enabled and configured."""
        return bool(self.hindsight_enabled and self.hindsight_base_url)

    def safe_dict(self) -> dict:
        """Return non-sensitive configuration dictionary safe for logging and debug endpoints."""
        return {
            "gemini_model": self.gemini_model,
            "gemini_api_key_configured": bool(self.gemini_api_key),
            "hindsight_enabled": self.hindsight_enabled,
            "hindsight_base_url": self.hindsight_base_url,
            "hindsight_bank_id": self.hindsight_bank_id,
            "hindsight_api_key_configured": bool(self.hindsight_api_key),
            "hindsight_timeout": self.hindsight_timeout,
            "hindsight_max_recall_results": self.hindsight_max_recall_results,
            "hindsight_reflect_enabled": self.hindsight_reflect_enabled,
            "hindsight_reflect_budget": self.hindsight_reflect_budget,
            "hindsight_min_memories_for_reflection": self.hindsight_min_memories_for_reflection,
            "hindsight_developer_memory_enabled": self.hindsight_developer_memory_enabled,
            "default_project_id": self.default_project_id,
        }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency helper to retrieve application settings."""
    return settings
