"""Tests for configuration module."""

import pytest
import json
import tempfile
from pathlib import Path

from src.config import (
    AppConfig,
    AudioConfig,
    FeedConfig,
    VMixConfig,
    WebConfig,
    load_config,
    save_config,
)


def test_default_audio_config():
    """Test default audio configuration."""
    config = AudioConfig()
    
    assert config.device_name == "Focusrite"
    assert config.sample_rate == 16000
    assert config.channels == 2
    assert config.chunk_size == 4096


def test_feed_config():
    """Test feed configuration."""
    config = FeedConfig(
        id="test",
        name="Test Feed",
        channel=0,
        vmix_input="TestInput"
    )
    
    assert config.id == "test"
    assert config.name == "Test Feed"
    assert config.channel == 0
    assert config.enabled is True


def test_vmix_config_defaults():
    """Test vMix configuration defaults."""
    config = VMixConfig()
    
    assert config.host == "127.0.0.1"
    assert config.port == 8088  # HTTP API port
    assert config.enabled is True
    assert config.file_output_enabled is True


def test_web_config_defaults():
    """Test web configuration defaults."""
    config = WebConfig()
    
    assert config.host == "0.0.0.0"
    assert config.port == 8080


def test_app_config_with_feeds():
    """Test app configuration with feeds."""
    config = AppConfig(
        feeds=[
            FeedConfig(id="feed1", name="Feed 1", channel=0),
            FeedConfig(id="feed2", name="Feed 2", channel=1),
        ]
    )
    
    assert len(config.feeds) == 2
    assert config.feeds[0].id == "feed1"
    assert config.feeds[1].id == "feed2"


def test_save_and_load_config():
    """Test saving and loading configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.json"
        
        # Create config
        config = AppConfig(
            feeds=[
                FeedConfig(id="test", name="Test", channel=0)
            ],
            caption_history_minutes=15
        )
        
        # Save
        save_config(config, str(config_path))
        
        # Verify file exists
        assert config_path.exists()
        
        # Load and verify
        loaded = load_config(str(config_path))
        
        assert len(loaded.feeds) == 1
        assert loaded.feeds[0].id == "test"
        assert loaded.caption_history_minutes == 15

