"""vMix HTTP API integration for caption output."""

import urllib.parse
import urllib.request
import threading
from typing import Optional


class VMixClient:
    """
    Client for vMix HTTP API.

    Sends caption text to vMix title inputs for overlay display.
    Uses HTTP API which is more reliable than TCP.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8088):
        """
        Initialize vMix client.

        Args:
            host: vMix host address.
            port: vMix HTTP API port (default 8088 for web controller).
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/api/"

        self._connected = False
        self._lock = threading.Lock()

    def connect(self) -> bool:
        """
        Test connection to vMix HTTP API.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            # Test with a simple API call
            url = f"{self.base_url}"
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    self._connected = True
                    print(f"Connected to vMix HTTP API at {self.host}:{self.port}")
                    return True
        except Exception as e:
            print(f"Failed to connect to vMix: {e}")

        self._connected = False
        return False

    def disconnect(self) -> None:
        """Disconnect from vMix (no-op for HTTP)."""
        self._connected = False
        print("Disconnected from vMix")

    def set_text(
        self,
        input_name: str,
        text: str,
        selected_index: int = 0
    ) -> bool:
        """
        Set text on a vMix title input.

        Args:
            input_name: Name of the title input in vMix.
            text: Text to display.
            selected_index: Index of the text field (default 0 for first field).

        Returns:
            True if successful, False otherwise.
        """
        return self._send_api_command(
            "SetText",
            Input=input_name,
            SelectedIndex=str(selected_index),
            Value=text
        )

    def set_input_text(self, input_name: str, text: str) -> bool:
        """
        Simplified method to set text on a title input.

        Uses the first text field (index 0).

        Args:
            input_name: Name of the title input.
            text: Text to display.

        Returns:
            True if successful, False otherwise.
        """
        return self.set_text(input_name, text, selected_index=0)

    def _send_api_command(self, function: str, **params) -> bool:
        """
        Send an API command to vMix.

        Args:
            function: The vMix function name.
            **params: Additional parameters for the function.

        Returns:
            True if successful, False otherwise.
        """
        with self._lock:
            try:
                # Build query parameters
                query_params = {"Function": function}
                query_params.update(params)

                query_string = urllib.parse.urlencode(query_params)
                url = f"{self.base_url}?{query_string}"

                req = urllib.request.Request(url, method='GET')
                with urllib.request.urlopen(req, timeout=5) as response:
                    return response.status == 200

            except Exception as e:
                print(f"vMix API error: {e}")
                return False

    @property
    def is_connected(self) -> bool:
        """Check if connected to vMix."""
        return self._connected

    def test_connection(self) -> bool:
        """
        Test the connection to vMix.

        Returns:
            True if vMix is responding, False otherwise.
        """
        return self.connect()


if __name__ == "__main__":
    # Test vMix connection
    client = VMixClient()
    
    if client.connect():
        print("Testing connection...")
        if client.test_connection():
            print("vMix is responding!")
            
            # Test setting text
            client.set_input_text("TestTitle", "Hello from StreamCaptioner!")
        else:
            print("vMix not responding")
        
        client.disconnect()
    else:
        print("Could not connect to vMix")

