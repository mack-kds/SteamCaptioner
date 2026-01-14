"""Audio device enumeration and management."""

from dataclasses import dataclass
from typing import List, Optional
import sounddevice as sd


@dataclass
class AudioDevice:
    """Represents an audio input device."""
    id: int
    name: str
    channels: int
    default_sample_rate: float
    is_default: bool
    
    def __str__(self) -> str:
        return f"{self.name} ({self.channels}ch)"


def list_input_devices() -> List[AudioDevice]:
    """
    List all available audio input devices.
    
    Returns:
        List of AudioDevice objects for input devices.
    """
    devices = []
    default_input = sd.default.device[0]  # Default input device index
    
    for i, device in enumerate(sd.query_devices()):
        # Only include input devices (max_input_channels > 0)
        if device['max_input_channels'] > 0:
            devices.append(AudioDevice(
                id=i,
                name=device['name'],
                channels=device['max_input_channels'],
                default_sample_rate=device['default_samplerate'],
                is_default=(i == default_input)
            ))
    
    return devices


def find_device_by_name(partial_name: str) -> Optional[AudioDevice]:
    """
    Find an audio device by partial name match (case-insensitive).
    
    Args:
        partial_name: Partial device name to search for.
        
    Returns:
        AudioDevice if found, None otherwise.
    """
    partial_lower = partial_name.lower()
    
    for device in list_input_devices():
        if partial_lower in device.name.lower():
            return device
    
    return None


def get_device_info(device_id: int) -> Optional[AudioDevice]:
    """
    Get detailed information for a specific device.
    
    Args:
        device_id: The device index.
        
    Returns:
        AudioDevice if found, None otherwise.
    """
    try:
        device = sd.query_devices(device_id)
        if device['max_input_channels'] > 0:
            default_input = sd.default.device[0]
            return AudioDevice(
                id=device_id,
                name=device['name'],
                channels=device['max_input_channels'],
                default_sample_rate=device['default_samplerate'],
                is_default=(device_id == default_input)
            )
    except Exception:
        pass
    
    return None


def get_default_input_device() -> Optional[AudioDevice]:
    """
    Get the system's default input device.
    
    Returns:
        AudioDevice for default input, None if not available.
    """
    try:
        default_id = sd.default.device[0]
        if default_id is not None and default_id >= 0:
            return get_device_info(default_id)
    except Exception:
        pass
    
    return None


def print_devices() -> None:
    """Print all available input devices (for debugging)."""
    print("\nAvailable Audio Input Devices:")
    print("-" * 50)
    
    for device in list_input_devices():
        default_marker = " [DEFAULT]" if device.is_default else ""
        print(f"  [{device.id}] {device.name}")
        print(f"       Channels: {device.channels}, Sample Rate: {device.default_sample_rate}Hz{default_marker}")
    
    print("-" * 50)


if __name__ == "__main__":
    # Test device enumeration
    print_devices()
    
    # Test finding Focusrite
    focusrite = find_device_by_name("Focusrite")
    if focusrite:
        print(f"\nFound Focusrite: {focusrite}")
    else:
        print("\nFocusrite not found")

