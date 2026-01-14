"""Tests for feed management."""

import pytest
from datetime import datetime

from src.feeds import Feed, Caption, FeedManager
from src.config import FeedConfig
from src.transcription.deepgram_client import Transcript


def test_feed_creation():
    """Test creating a feed."""
    feed = Feed(
        feed_id="test",
        name="Test Feed",
        channel=0,
        vmix_input="TestInput"
    )
    
    assert feed.id == "test"
    assert feed.name == "Test Feed"
    assert feed.channel == 0
    assert feed.vmix_input == "TestInput"
    assert feed.enabled is True
    assert feed.caption_count == 0


def test_feed_add_transcript():
    """Test adding a transcript to a feed."""
    feed = Feed(feed_id="test", name="Test", channel=0)
    
    transcript = Transcript(
        text="Hello world",
        is_final=True,
        confidence=0.95,
        timestamp=datetime.now()
    )
    
    caption = feed.add_transcript(transcript)
    
    assert caption.text == "Hello world"
    assert caption.is_final is True
    assert caption.feed_id == "test"
    assert feed.caption_count == 1


def test_feed_get_current_text():
    """Test getting current caption text."""
    feed = Feed(feed_id="test", name="Test", channel=0)
    
    # Initially empty
    assert feed.get_current_text() == ""
    
    # Add a final transcript
    transcript = Transcript(text="First caption", is_final=True, confidence=0.9)
    feed.add_transcript(transcript)
    
    assert feed.get_current_text() == "First caption"
    
    # Add an interim transcript
    interim = Transcript(text="Partial...", is_final=False, confidence=0.5)
    feed.add_transcript(interim)
    
    assert feed.get_current_text() == "Partial..."


def test_feed_manager():
    """Test feed manager operations."""
    manager = FeedManager()
    
    config = FeedConfig(
        id="announcements",
        name="Announcements",
        channel=0,
        vmix_input="Ann_Caption"
    )
    
    feed = manager.create_feed(config)
    
    assert feed.id == "announcements"
    assert manager.get_feed("announcements") is not None
    assert len(manager.list_feeds()) == 1
    
    # Remove feed
    assert manager.remove_feed("announcements") is True
    assert manager.get_feed("announcements") is None


def test_feed_subscription():
    """Test feed subscription callbacks."""
    feed = Feed(feed_id="test", name="Test", channel=0)
    
    received_captions = []
    
    def on_caption(caption: Caption):
        received_captions.append(caption)
    
    feed.subscribe(on_caption)
    
    transcript = Transcript(text="Test message", is_final=True, confidence=0.9)
    feed.add_transcript(transcript)
    
    assert len(received_captions) == 1
    assert received_captions[0].text == "Test message"
    
    # Unsubscribe
    feed.unsubscribe(on_caption)
    feed.add_transcript(transcript)
    
    # Should still be 1 since we unsubscribed
    assert len(received_captions) == 1

