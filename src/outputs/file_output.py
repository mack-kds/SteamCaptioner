"""File-based caption output for vMix data source backup."""

import os
from pathlib import Path
from typing import Dict
from datetime import datetime


class FileOutput:
    """
    Writes captions to text files.
    
    vMix can read from these files as a data source,
    providing a backup method for caption display.
    """
    
    def __init__(self, output_dir: str = "output/captions"):
        """
        Initialize file output.
        
        Args:
            output_dir: Directory to write caption files.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._last_text: Dict[str, str] = {}
    
    def write_caption(self, feed_id: str, text: str) -> bool:
        """
        Write caption text to a feed-specific file.
        
        Only writes if text has changed to reduce disk I/O.
        
        Args:
            feed_id: The feed identifier.
            text: Caption text to write.
            
        Returns:
            True if written, False if unchanged or error.
        """
        # Skip if text hasn't changed
        if self._last_text.get(feed_id) == text:
            return False
        
        try:
            file_path = self.output_dir / f"{feed_id}.txt"
            file_path.write_text(text, encoding='utf-8')
            self._last_text[feed_id] = text
            return True
        except Exception as e:
            print(f"File output error for {feed_id}: {e}")
            return False
    
    def clear_caption(self, feed_id: str) -> bool:
        """
        Clear the caption file for a feed.
        
        Args:
            feed_id: The feed identifier.
            
        Returns:
            True if cleared, False on error.
        """
        return self.write_caption(feed_id, "")
    
    def clear_all(self) -> None:
        """Clear all caption files."""
        for feed_id in list(self._last_text.keys()):
            self.clear_caption(feed_id)
    
    def get_file_path(self, feed_id: str) -> Path:
        """
        Get the file path for a feed.
        
        Args:
            feed_id: The feed identifier.
            
        Returns:
            Path to the caption file.
        """
        return self.output_dir / f"{feed_id}.txt"
    
    def write_history(self, feed_id: str, captions: list) -> bool:
        """
        Write caption history to a separate file.
        
        Args:
            feed_id: The feed identifier.
            captions: List of Caption objects.
            
        Returns:
            True if written, False on error.
        """
        try:
            file_path = self.output_dir / f"{feed_id}_history.txt"
            
            lines = []
            for caption in captions:
                timestamp = caption.timestamp.strftime("%H:%M:%S")
                lines.append(f"[{timestamp}] {caption.text}")
            
            file_path.write_text("\n".join(lines), encoding='utf-8')
            return True
        except Exception as e:
            print(f"History output error for {feed_id}: {e}")
            return False


if __name__ == "__main__":
    # Test file output
    output = FileOutput()
    
    output.write_caption("test_feed", "Hello, this is a test caption!")
    print(f"Written to: {output.get_file_path('test_feed')}")
    
    output.write_caption("test_feed", "Updated caption text.")
    print("Caption updated")
    
    output.clear_caption("test_feed")
    print("Caption cleared")

