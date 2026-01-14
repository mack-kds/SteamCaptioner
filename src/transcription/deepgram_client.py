"""Deepgram streaming transcription client."""

import asyncio
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional, List
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
)


@dataclass
class Word:
    """A single transcribed word with timing."""
    word: str
    start: float
    end: float
    confidence: float


@dataclass
class Transcript:
    """A transcription result."""
    text: str
    is_final: bool
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    words: List[Word] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "is_final": self.is_final,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
        }


class DeepgramTranscriber:
    """
    Streaming transcription using Deepgram's live API.
    
    Handles connection, audio streaming, and transcript callbacks.
    """
    
    def __init__(self, api_key: str, feed_id: str):
        """
        Initialize the transcriber.
        
        Args:
            api_key: Deepgram API key.
            feed_id: Identifier for this feed (for logging).
        """
        self.api_key = api_key
        self.feed_id = feed_id
        
        self._client: Optional[DeepgramClient] = None
        self._connection = None
        self._is_connected = False
        self._transcript_callback: Optional[Callable[[Transcript], None]] = None
        self._error_callback: Optional[Callable[[Exception], None]] = None
        
        # For running async in sync context
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
    
    def on_transcript(self, callback: Callable[[Transcript], None]) -> None:
        """Register callback for transcript events."""
        self._transcript_callback = callback
    
    def on_error(self, callback: Callable[[Exception], None]) -> None:
        """Register callback for error events."""
        self._error_callback = callback
    
    def start(self) -> bool:
        """
        Start the transcription connection.
        
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            self._client = DeepgramClient(self.api_key)
            self._connection = self._client.listen.live.v("1")
            
            # Set up event handlers
            self._connection.on(LiveTranscriptionEvents.Transcript, self._handle_transcript)
            self._connection.on(LiveTranscriptionEvents.Error, self._handle_error)
            self._connection.on(LiveTranscriptionEvents.Close, self._handle_close)
            
            # Configure options for real-time transcription
            options = LiveOptions(
                model="nova-2",
                language="en-US",
                smart_format=True,
                interim_results=True,
                punctuate=True,
                profanity_filter=True,  # Replace profanity with asterisks
                encoding="linear16",
                sample_rate=16000,
                channels=1,
            )
            
            # Start the connection
            result = self._connection.start(options)
            self._is_connected = result
            
            if result:
                print(f"[{self.feed_id}] Deepgram connected")
            else:
                print(f"[{self.feed_id}] Deepgram connection failed")
            
            return result
            
        except Exception as e:
            print(f"[{self.feed_id}] Deepgram start error: {e}")
            if self._error_callback:
                self._error_callback(e)
            return False
    
    def send_audio(self, audio_bytes: bytes) -> None:
        """
        Send audio data to Deepgram.
        
        Args:
            audio_bytes: Audio data in LINEAR16 format.
        """
        if self._connection and self._is_connected:
            try:
                self._connection.send(audio_bytes)
            except Exception as e:
                print(f"[{self.feed_id}] Send error: {e}")
    
    def stop(self) -> None:
        """Stop the transcription connection."""
        self._is_connected = False
        
        if self._connection:
            try:
                self._connection.finish()
            except Exception as e:
                print(f"[{self.feed_id}] Stop error: {e}")
            self._connection = None
        
        print(f"[{self.feed_id}] Deepgram disconnected")
    
    def _handle_transcript(self, *args, **kwargs) -> None:
        """Handle incoming transcript from Deepgram."""
        try:
            # The result is passed as the second argument
            result = args[1] if len(args) > 1 else kwargs.get('result')
            
            if result and result.channel and result.channel.alternatives:
                alt = result.channel.alternatives[0]
                text = alt.transcript
                
                if text:  # Only process non-empty transcripts
                    is_final = result.is_final
                    confidence = alt.confidence if hasattr(alt, 'confidence') else 0.0
                    
                    transcript = Transcript(
                        text=text,
                        is_final=is_final,
                        confidence=confidence,
                    )
                    
                    if self._transcript_callback:
                        self._transcript_callback(transcript)
                        
        except Exception as e:
            print(f"[{self.feed_id}] Transcript handling error: {e}")
    
    def _handle_error(self, *args, **kwargs) -> None:
        """Handle Deepgram errors."""
        error = args[1] if len(args) > 1 else kwargs.get('error', 'Unknown error')
        print(f"[{self.feed_id}] Deepgram error: {error}")
        
        if self._error_callback:
            self._error_callback(Exception(str(error)))
    
    def _handle_close(self, *args, **kwargs) -> None:
        """Handle connection close."""
        print(f"[{self.feed_id}] Deepgram connection closed")
        self._is_connected = False
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Deepgram."""
        return self._is_connected

