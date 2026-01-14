"""Audio capture with channel selection."""

import threading
import queue
from typing import Callable, Optional, List
import numpy as np
import sounddevice as sd


class AudioCapture:
    """
    Captures audio from a specific channel of an audio device.
    
    Designed for streaming to speech-to-text services like Deepgram.
    """
    
    def __init__(
        self,
        device_id: int,
        channels: List[int],  # List of channel indices (0-based)
        sample_rate: int = 16000,
        chunk_size: int = 4096,
    ):
        """
        Initialize audio capture.
        
        Args:
            device_id: Audio device index.
            channels: List of channel indices to capture (0-based).
            sample_rate: Sample rate in Hz (16000 recommended for Deepgram).
            chunk_size: Number of samples per chunk.
        """
        self.device_id = device_id
        self.channels = channels
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        
        self._stream: Optional[sd.InputStream] = None
        self._callback: Optional[Callable[[bytes], None]] = None
        self._running = False
        self._audio_queue: queue.Queue = queue.Queue()
        self._process_thread: Optional[threading.Thread] = None
        
        # Get device info to know total channels
        device_info = sd.query_devices(device_id)
        self._device_channels = device_info['max_input_channels']
        
        # Validate channels
        for ch in channels:
            if ch < 0 or ch >= self._device_channels:
                raise ValueError(
                    f"Channel {ch} out of range. Device has {self._device_channels} channels."
                )
    
    def start(self, callback: Callable[[bytes], None]) -> None:
        """
        Start capturing audio.
        
        Args:
            callback: Function to call with audio bytes (LINEAR16 format).
        """
        if self._running:
            return
        
        self._callback = callback
        self._running = True
        
        # Start processing thread
        self._process_thread = threading.Thread(target=self._process_audio, daemon=True)
        self._process_thread.start()
        
        # Start audio stream - capture all device channels, we'll extract what we need
        self._stream = sd.InputStream(
            device=self.device_id,
            channels=self._device_channels,
            samplerate=self.sample_rate,
            blocksize=self.chunk_size,
            dtype=np.float32,
            callback=self._audio_callback,
        )
        self._stream.start()
    
    def stop(self) -> None:
        """Stop capturing audio."""
        self._running = False
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        if self._process_thread:
            self._process_thread.join(timeout=1.0)
            self._process_thread = None
    
    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """Internal callback from sounddevice."""
        if status:
            print(f"Audio status: {status}")
        
        if self._running:
            # Put audio data in queue for processing
            self._audio_queue.put(indata.copy())
    
    def _process_audio(self) -> None:
        """Process audio in separate thread to avoid blocking."""
        while self._running:
            try:
                indata = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            
            # Extract and mix selected channels
            if len(self.channels) == 1:
                # Single channel
                channel_data = indata[:, self.channels[0]]
            else:
                # Multiple channels - average them
                channel_data = np.mean(indata[:, self.channels], axis=1)
            
            # Convert float32 [-1.0, 1.0] to int16 for LINEAR16 format
            audio_int16 = (channel_data * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
            
            # Call the callback with audio bytes
            if self._callback:
                try:
                    self._callback(audio_bytes)
                except Exception as e:
                    print(f"Error in audio callback: {e}")
    
    @property
    def is_running(self) -> bool:
        """Check if capture is running."""
        return self._running


if __name__ == "__main__":
    # Test audio capture
    from .device_manager import list_input_devices, find_device_by_name
    
    # Find default device or Focusrite
    device = find_device_by_name("Focusrite")
    if not device:
        devices = list_input_devices()
        if devices:
            device = devices[0]
    
    if device:
        print(f"Testing capture from: {device.name}")
        
        def on_audio(audio_bytes: bytes):
            print(f"Received {len(audio_bytes)} bytes")
        
        capture = AudioCapture(device.id, channels=[0], sample_rate=16000)
        capture.start(on_audio)
        
        import time
        time.sleep(3)
        
        capture.stop()
        print("Capture stopped")
    else:
        print("No audio device found")

