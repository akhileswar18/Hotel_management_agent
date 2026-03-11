"""
Centralized application settings powered by pydantic.

Provides a single place to fetch environment-driven configuration such
as primary voice language, Whisper hints, and TTS voice mappings.
"""

from functools import lru_cache
from typing import Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment/.env."""

    voice_primary_language: str = Field(
        default="te-IN", alias="VOICE_PRIMARY_LANGUAGE"
    )
    voice_fallback_languages: List[str] = Field(
        default_factory=lambda: ["hi-IN", "en-IN"],
        alias="VOICE_FALLBACK_LANGUAGES",
    )
    whisper_language_hint: Optional[str] = Field(
        default="te",
        alias="WHISPER_LANGUAGE_HINT",
        description="Preferred Whisper decode language (None for auto).",
    )
    tts_voice_ids: Dict[str, str] = Field(
        default_factory=lambda: {
            "te-IN": "Microsoft Vallu (Natural) - Telugu (India)",
            "hi-IN": "Microsoft Hemant - Hindi (India)",
            "en-IN": "Microsoft Heera - English (India)",
        },
        alias="TTS_VOICE_IDS",
        description="Mapping of language code to pyttsx3 voice id.",
    )
    menu_synonyms_file: str = Field(
        default="assets/localization/menus_te.json",
        alias="MENU_SYNONYMS_FILE",
    )
    llm_provider: str = Field(default="groq", alias="LLM_PROVIDER")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience singleton for modules that prefer direct import
settings: Settings = get_settings()
