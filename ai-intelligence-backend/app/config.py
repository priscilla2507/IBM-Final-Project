"""
app/config.py

Application configuration loaded from environment variables.
No secrets or model names are hardcoded.
"""

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    # ── Gemini API ────────────────────────────────────────────────────── #
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key. Required at runtime.",
    )
    gemini_model: str = Field(
        default="",
        description=(
            "Gemini model name. Set GEMINI_MODEL in your environment. "
            "Example: gemini-2.0-flash"
        ),
    )

    # ── Image upload limits ───────────────────────────────────────────── #
    max_image_size_mb: int = Field(
        default=10,
        description="Maximum allowed upload size in megabytes.",
    )

    # ── API metadata ──────────────────────────────────────────────────── #
    app_title: str = "ChhayaRakshak AI"
    app_version: str = "0.1.0"
    app_description: str = (
        "AI backend for urban heat protection and cooling intervention planning."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


def require_gemini_config(settings: Settings) -> tuple[str, str]:
    """
    Validate that both GEMINI_API_KEY and GEMINI_MODEL are set.
    Call this in any service function that needs Gemini before making an API call.
    Raises ValueError with a clear message if either is missing.
    Returns (api_key, model_name) on success.
    """
    errors: list[str] = []
    if not settings.gemini_api_key:
        errors.append("GEMINI_API_KEY is not set.")
    if not settings.gemini_model:
        errors.append("GEMINI_MODEL is not set.")
    if errors:
        raise ValueError(
            "Gemini configuration is incomplete: " + " ".join(errors)
        )
    return settings.gemini_api_key, settings.gemini_model
