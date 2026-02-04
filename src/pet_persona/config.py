"""Configuration management for Pet Persona AI."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Base paths
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent.parent)
    data_dir: Optional[Path] = Field(default=None)

    # Database
    database_url: str = "sqlite:///data/pet_persona.db"

    # API Keys
    youtube_api_key: str = ""
    openai_api_key: str = ""

    # Embedding model
    embedding_model: str = "all-MiniLM-L6-v2"

    # Rate limiting
    wikipedia_rate_limit_requests: int = 50
    wikipedia_rate_limit_period: int = 60  # seconds
    youtube_rate_limit_requests: int = 100
    youtube_rate_limit_period: int = 60  # seconds

    # Cache settings
    cache_enabled: bool = True
    cache_ttl_hours: int = 24

    # Logging
    log_level: str = "INFO"

    # Voice settings
    stt_provider: Literal["faster_whisper", "none"] = "faster_whisper"
    tts_provider: Literal["pyttsx3", "none"] = "pyttsx3"
    audio_sample_rate: int = 16000
    audio_language: str = "en"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.data_dir is None:
            self.data_dir = self.base_dir / "data"

    @property
    def raw_wikipedia_dir(self) -> Path:
        """Directory for raw Wikipedia data."""
        path = self.data_dir / "raw" / "wikipedia"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def raw_youtube_dir(self) -> Path:
        """Directory for raw YouTube data."""
        path = self.data_dir / "raw" / "youtube"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def processed_breeds_dir(self) -> Path:
        """Directory for processed breed data."""
        path = self.data_dir / "processed" / "breeds"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def outputs_dir(self) -> Path:
        """Directory for output files."""
        path = self.data_dir / "outputs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def cache_dir(self) -> Path:
        """Directory for cache files."""
        path = self.data_dir / "cache"
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
