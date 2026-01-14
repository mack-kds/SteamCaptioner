"""Feed manager for handling multiple caption feeds."""

from typing import Dict, List, Optional, Callable

from .feed import Feed, Caption
from ..config import FeedConfig
from ..transcription.deepgram_client import Transcript


class FeedManager:
    """
    Manages multiple caption feeds.
    
    Provides centralized access to all feeds and their captions.
    """
    
    def __init__(self):
        """Initialize the feed manager."""
        self._feeds: Dict[str, Feed] = {}
        self._global_subscribers: List[Callable[[str, Caption], None]] = []
    
    def create_feed(self, config: FeedConfig) -> Feed:
        """
        Create and register a new feed.
        
        Args:
            config: Feed configuration.
            
        Returns:
            The created Feed object.
        """
        feed = Feed(
            feed_id=config.id,
            name=config.name,
            channel=config.channel,
            vmix_input=config.vmix_input,
        )
        feed.enabled = config.enabled
        
        self._feeds[config.id] = feed
        return feed
    
    def get_feed(self, feed_id: str) -> Optional[Feed]:
        """
        Get a feed by ID.
        
        Args:
            feed_id: The feed's unique identifier.
            
        Returns:
            Feed if found, None otherwise.
        """
        return self._feeds.get(feed_id)
    
    def list_feeds(self) -> List[Feed]:
        """
        List all registered feeds.
        
        Returns:
            List of all Feed objects.
        """
        return list(self._feeds.values())
    
    def get_enabled_feeds(self) -> List[Feed]:
        """
        Get all enabled feeds.
        
        Returns:
            List of enabled Feed objects.
        """
        return [f for f in self._feeds.values() if f.enabled]
    
    def remove_feed(self, feed_id: str) -> bool:
        """
        Remove a feed.
        
        Args:
            feed_id: The feed's unique identifier.
            
        Returns:
            True if removed, False if not found.
        """
        if feed_id in self._feeds:
            del self._feeds[feed_id]
            return True
        return False
    
    def add_transcript(self, feed_id: str, transcript: Transcript) -> Optional[Caption]:
        """
        Add a transcript to a specific feed.
        
        Args:
            feed_id: The feed's unique identifier.
            transcript: The transcript to add.
            
        Returns:
            The created Caption, or None if feed not found.
        """
        feed = self.get_feed(feed_id)
        if feed and feed.enabled:
            caption = feed.add_transcript(transcript)
            
            # Notify global subscribers
            for callback in self._global_subscribers:
                try:
                    callback(feed_id, caption)
                except Exception as e:
                    print(f"Error in global subscriber: {e}")
            
            return caption
        return None
    
    def subscribe_all(self, callback: Callable[[str, Caption], None]) -> None:
        """
        Subscribe to updates from all feeds.
        
        Args:
            callback: Function called with (feed_id, caption) on updates.
        """
        self._global_subscribers.append(callback)
    
    def unsubscribe_all(self, callback: Callable[[str, Caption], None]) -> None:
        """
        Unsubscribe from all feed updates.
        
        Args:
            callback: The callback to remove.
        """
        if callback in self._global_subscribers:
            self._global_subscribers.remove(callback)
    
    def get_all_feeds_info(self) -> List[dict]:
        """
        Get info for all feeds as dictionaries.
        
        Returns:
            List of feed info dictionaries.
        """
        return [feed.to_dict() for feed in self._feeds.values()]
    
    def clear_all(self) -> None:
        """Remove all feeds."""
        self._feeds.clear()


# Global feed manager instance
_feed_manager: Optional[FeedManager] = None


def get_feed_manager() -> FeedManager:
    """Get the global feed manager instance."""
    global _feed_manager
    if _feed_manager is None:
        _feed_manager = FeedManager()
    return _feed_manager

