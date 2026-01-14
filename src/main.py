"""Main entry point for StreamCaptioner."""

import threading
import time
import socket
from typing import Dict, Optional

import uvicorn

from .config import get_config, get_settings, FeedConfig
from .audio import AudioDevice, AudioCapture
from .transcription import DeepgramTranscriber, Transcript
from .feeds import FeedManager, get_feed_manager, Caption
from .outputs import VMixClient, FileOutput
from .web.server import app as web_app, broadcast_caption
from .gui import StreamCaptionerGUI


class StreamCaptionerApp:
    """Main application controller."""
    
    def __init__(self):
        self.config = get_config()
        self.settings = get_settings()
        
        # Components
        self.feed_manager: FeedManager = get_feed_manager()
        self.vmix_client: Optional[VMixClient] = None
        self.file_output: Optional[FileOutput] = None
        self.gui: Optional[StreamCaptionerGUI] = None
        
        # Audio captures and transcribers per feed
        self.captures: Dict[str, AudioCapture] = {}
        self.transcribers: Dict[str, DeepgramTranscriber] = {}
        
        # Server thread
        self.server_thread: Optional[threading.Thread] = None
        self.server: Optional[uvicorn.Server] = None
        
        self._running = False
    
    def initialize(self):
        """Initialize all components."""
        # Create feeds from config
        for feed_config in self.config.feeds:
            self.feed_manager.create_feed(feed_config)
        
        # Initialize vMix client
        if self.config.vmix.enabled:
            self.vmix_client = VMixClient(
                host=self.config.vmix.host,
                port=self.config.vmix.port
            )
        
        # Initialize file output
        if self.config.vmix.file_output_enabled:
            self.file_output = FileOutput(self.config.vmix.file_output_dir)
        
        # Subscribe to feed updates for outputs
        self.feed_manager.subscribe_all(self._on_caption)
    
    def _on_caption(self, feed_id: str, caption: Caption):
        """Handle new caption from any feed."""
        feed = self.feed_manager.get_feed(feed_id)
        if not feed:
            return

        # Send to vMix
        if self.vmix_client and feed.vmix_input:
            self.vmix_client.set_input_text(feed.vmix_input, caption.text)

        # Write to file
        if self.file_output:
            self.file_output.write_caption(feed_id, caption.text)

        # Broadcast to web clients
        try:
            broadcast_caption(feed_id, caption)
        except Exception as e:
            pass  # Web broadcast is best-effort
    
    def start_captioning(self, device: AudioDevice):
        """Start captioning with the selected device."""
        if self._running:
            return
        
        self._running = True
        
        # Connect to vMix
        if self.vmix_client:
            if self.vmix_client.connect():
                print("Connected to vMix")
            else:
                print("Warning: Could not connect to vMix")
        
        # Start transcription for each feed
        for feed in self.feed_manager.get_enabled_feeds():
            self._start_feed(device, feed.id, feed.channel)
            if self.gui:
                self.gui.update_feed_status(feed.id, "Active")
    
    def _start_feed(self, device: AudioDevice, feed_id: str, channel: int):
        """Start audio capture and transcription for a feed."""
        # Validate channel before starting
        if channel >= device.channels:
            error_msg = f"Channel {channel} not available on {device.name} (has {device.channels} channels)"
            print(f"[{feed_id}] Error: {error_msg}")
            if self.gui:
                self.gui.update_feed_status(feed_id, f"Error: Ch {channel} unavailable")
            return

        # Create transcriber
        transcriber = DeepgramTranscriber(
            api_key=self.settings.deepgram_api_key,
            feed_id=feed_id
        )

        # Set up transcript callback
        def on_transcript(transcript: Transcript):
            self.feed_manager.add_transcript(feed_id, transcript)

        transcriber.on_transcript(on_transcript)

        # Start transcriber
        if not transcriber.start():
            print(f"Failed to start transcriber for {feed_id}")
            if self.gui:
                self.gui.update_feed_status(feed_id, "Error: Transcriber failed")
            return

        self.transcribers[feed_id] = transcriber

        # Create audio capture
        try:
            capture = AudioCapture(
                device_id=device.id,
                channels=[channel],
                sample_rate=self.config.audio.sample_rate,
                chunk_size=self.config.audio.chunk_size
            )
        except ValueError as e:
            print(f"[{feed_id}] Audio capture error: {e}")
            if self.gui:
                self.gui.update_feed_status(feed_id, "Error: Audio capture")
            transcriber.stop()
            del self.transcribers[feed_id]
            return

        # Start capture, sending audio to transcriber
        capture.start(transcriber.send_audio)
        self.captures[feed_id] = capture

        print(f"Started feed: {feed_id} on channel {channel}")
    
    def stop_captioning(self):
        """Stop all captioning."""
        self._running = False
        
        # Stop all captures
        for feed_id, capture in self.captures.items():
            capture.stop()
            if self.gui:
                self.gui.update_feed_status(feed_id, "Stopped")
        self.captures.clear()
        
        # Stop all transcribers
        for transcriber in self.transcribers.values():
            transcriber.stop()
        self.transcribers.clear()
        
        # Disconnect vMix
        if self.vmix_client:
            self.vmix_client.disconnect()
        
        # Clear file outputs
        if self.file_output:
            self.file_output.clear_all()

        print("Captioning stopped")

    def start_web_server(self):
        """Start the web server in a background thread."""
        def run_server():
            config = uvicorn.Config(
                web_app,
                host=self.config.web.host,
                port=self.config.web.port,
                log_level="warning"
            )
            self.server = uvicorn.Server(config)
            self.server.run()

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        # Wait a moment for server to start
        time.sleep(0.5)

        # Get local IP for display
        local_ip = self._get_local_ip()
        url = f"http://{local_ip}:{self.config.web.port}"
        print(f"Web server running at: {url}")

        return url

    def _get_local_ip(self) -> str:
        """Get the local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "localhost"

    def run_with_gui(self):
        """Run the application with GUI."""
        # Initialize components
        self.initialize()

        # Start web server
        url = self.start_web_server()

        # Create and configure GUI
        self.gui = StreamCaptionerGUI()
        self.gui.set_web_url(url)
        self.gui.on_start = self.start_captioning
        self.gui.on_stop = self.stop_captioning

        # Run GUI (blocks until closed)
        try:
            self.gui.run()
        finally:
            self.stop_captioning()

    def run_headless(self, device_name: str = None):
        """Run without GUI (for testing or automation)."""
        from .audio import find_device_by_name, list_input_devices

        # Initialize
        self.initialize()

        # Find device
        if device_name:
            device = find_device_by_name(device_name)
        else:
            devices = list_input_devices()
            device = devices[0] if devices else None

        if not device:
            print("No audio device found!")
            return

        print(f"Using device: {device.name}")

        # Start web server
        url = self.start_web_server()
        print(f"Web UI: {url}")

        # Start captioning
        self.start_captioning(device)

        # Run until interrupted
        try:
            print("Press Ctrl+C to stop...")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
            self.stop_captioning()


def main():
    """Main entry point."""
    app = StreamCaptionerApp()
    app.run_with_gui()


if __name__ == "__main__":
    main()

