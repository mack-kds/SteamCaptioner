"""Tests for audio module."""

import pytest
from src.audio import list_input_devices, find_device_by_name, get_device_info


def test_list_input_devices():
    """Test that we can list audio devices."""
    devices = list_input_devices()
    # Should return a list (may be empty if no devices)
    assert isinstance(devices, list)


def test_device_has_required_fields():
    """Test that devices have required fields."""
    devices = list_input_devices()
    
    for device in devices:
        assert hasattr(device, 'id')
        assert hasattr(device, 'name')
        assert hasattr(device, 'channels')
        assert hasattr(device, 'default_sample_rate')
        assert hasattr(device, 'is_default')
        
        assert isinstance(device.id, int)
        assert isinstance(device.name, str)
        assert isinstance(device.channels, int)
        assert device.channels > 0


def test_find_device_by_name_not_found():
    """Test finding a device that doesn't exist."""
    device = find_device_by_name("NonExistentDevice12345")
    assert device is None


def test_get_device_info_invalid_id():
    """Test getting info for invalid device ID."""
    device = get_device_info(-999)
    assert device is None

