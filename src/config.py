"""Configuration management for StreamCaptioner."""

import json
import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class FeedConfig(BaseModel):
    """Configuration for a single caption feed."""
    id: str
    name: str
    channel: int  # 0-based channel index
    vmix_input: str = ""
    enabled: bool = True


class AudioConfig(BaseModel):
    """Audio device configuration."""
    device_name: str = "Focusrite"
    sample_rate: int = 16000
    channels: int = 2
    chunk_size: int = 4096


class VMixConfig(BaseModel):
    """vMix integration configuration."""
    host: str = "127.0.0.1"
    port: int = 8088  # HTTP API port (web controller)
    enabled: bool = True
    file_output_enabled: bool = True
    file_output_dir: str = "output/captions"


class WebConfig(BaseModel):
    """Web server configuration."""
    host: str = "0.0.0.0"
    port: int = 8080


class AppConfig(BaseModel):
    """Main application configuration."""
    audio: AudioConfig = Field(default_factory=AudioConfig)
    feeds: List[FeedConfig] = Field(default_factory=list)
    vmix: VMixConfig = Field(default_factory=VMixConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    caption_history_minutes: int = 10


class Settings(BaseSettings):
    """Environment-based settings (secrets)."""
    deepgram_api_key: str = Field(default="", alias="DEEPGRAM_API_KEY")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


# Global instances
_config: Optional[AppConfig] = None
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get environment settings (API keys, etc.)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_config() -> AppConfig:
    """Get application configuration."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def load_config(config_path: str = "config.json") -> AppConfig:
    """Load configuration from JSON file."""
    global _config
    path = Path(config_path)
    
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _config = AppConfig(**data)
    else:
        # Create default config
        _config = AppConfig(
            feeds=[
                FeedConfig(
                    id="announcements",
                    name="Announcements",
                    channel=0,
                    vmix_input="Announcements"  # Must match vMix title name exactly
                ),
                FeedConfig(
                    id="referee_main",
                    name="Referee - Main Field",
                    channel=1,
                    vmix_input="Referee - Main Field"  # Must match vMix title name exactly
                ),
            ]
        )
        save_config(_config, config_path)
    
    return _config


def save_config(config: AppConfig, config_path: str = "config.json") -> None:
    """Save configuration to JSON file."""
    global _config
    path = Path(config_path)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=4)
    
    _config = config


def reload_config(config_path: str = "config.json") -> AppConfig:
    """Force reload configuration from file."""
    global _config
    _config = None
    return load_config(config_path)

