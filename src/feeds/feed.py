"""Caption feed management."""

import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Set, List, Optional

from ..transcription.deepgram_client import Transcript


@dataclass
class Caption:
    """A single caption entry."""
    id: str
    feed_id: str
    text: str
    is_final: bool
    timestamp: datetime
    confidence: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "feed_id": self.feed_id,
            "text": self.text,
            "is_final": self.is_final,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
        }


class Feed:
    """
    Manages a single caption feed.
    
    Stores caption history and notifies subscribers of updates.
    """
    
    def __init__(
        self,
        feed_id: str,
        name: str,
        channel: int,
        vmix_input: str = "",
        max_captions: int = 1000,
    ):
        """
        Initialize a feed.
        
        Args:
            feed_id: Unique identifier for this feed.
            name: Display name for the feed.
            channel: Audio channel index (0-based).
            vmix_input: vMix title input name.
            max_captions: Maximum captions to store in history.
        """
        self.id = feed_id
        self.name = name
        self.channel = channel
        self.vmix_input = vmix_input
        
        self._captions: deque[Caption] = deque(maxlen=max_captions)
        self._current_interim: Optional[str] = None
        self._subscribers: Set[Callable[[Caption], None]] = set()
        self._enabled = True
    
    def add_transcript(self, transcript: Transcript) -> Caption:
        """
        Add a transcript to the feed.
        
        Args:
            transcript: The transcript from Deepgram.
            
        Returns:
            The created Caption object.
        """
        caption = Caption(
            id=str(uuid.uuid4()),
            feed_id=self.id,
            text=transcript.text,
            is_final=transcript.is_final,
            timestamp=transcript.timestamp,
            confidence=transcript.confidence,
        )
        
        if transcript.is_final:
            self._captions.append(caption)
            self._current_interim = None
        else:
            self._current_interim = transcript.text
        
        # Notify subscribers
        self._notify_subscribers(caption)
        
        return caption
    
    def get_history(self, minutes: int = 10) -> List[Caption]:
        """
        Get captions from the last N minutes.
        
        Args:
            minutes: Number of minutes of history to retrieve.
            
        Returns:
            List of Caption objects.
        """
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [c for c in self._captions if c.timestamp >= cutoff]
    
    def get_current_text(self) -> str:
        """
        Get the current caption text (final or interim).
        
        Returns:
            Current caption text.
        """
        if self._current_interim:
            return self._current_interim
        elif self._captions:
            return self._captions[-1].text
        return ""
    
    def subscribe(self, callback: Callable[[Caption], None]) -> None:
        """Subscribe to caption updates."""
        self._subscribers.add(callback)
    
    def unsubscribe(self, callback: Callable[[Caption], None]) -> None:
        """Unsubscribe from caption updates."""
        self._subscribers.discard(callback)
    
    def _notify_subscribers(self, caption: Caption) -> None:
        """Notify all subscribers of a new caption."""
        for callback in self._subscribers.copy():
            try:
                callback(caption)
            except Exception as e:
                print(f"Error notifying subscriber: {e}")
    
    @property
    def enabled(self) -> bool:
        """Check if feed is enabled."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable the feed."""
        self._enabled = value
    
    @property
    def caption_count(self) -> int:
        """Get number of stored captions."""
        return len(self._captions)
    
    def to_dict(self) -> dict:
        """Convert feed info to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "channel": self.channel,
            "vmix_input": self.vmix_input,
            "enabled": self._enabled,
            "caption_count": self.caption_count,
        }

