"""Unit tests for iOSDriver with mocked WDA HTTP."""
import json
from unittest.mock import patch, MagicMock

import pytest

from gtframe.device.ios_driver import iOSDriver
from gtframe.exceptions import DeviceError, DeviceNotConnectedError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_urlopen():
    with patch("gtframe.device.ios_driver.urllib.request.urlopen") as mock:
        yield mock


@pytest.fixture
def driver():
    return iOSDriver(device_id="test-iphone")


# ---------------------------------------------------------------------------
# _wda_request
# ---------------------------------------------------------------------------


def _make_response(data: dict, status=200):
    """Helper: create a mock HTTP response."""
    m = MagicMock()
    m.status = status
    body = json.dumps(data).encode()
    m.read.return_value = body
    m.__enter__.return_value = m
    return m


def test_wda_request_success(mock_urlopen, driver):
    """_wda_request() should return parsed JSON on success."""
    mock_urlopen.return_value = _make_response({"value": {"ready": True}})
    result = driver._wda_request("GET", "/status")
    assert result == {"value": {"ready": True}}


def test_wda_request_failure(mock_urlopen, driver):
    """_wda_request() should raise DeviceError on non-200."""
    mock_urlopen.return_value = _make_response({"error": "not ready"}, status=500)
    with pytest.raises(DeviceError):
        driver._wda_request("GET", "/status")


# ---------------------------------------------------------------------------
# connect
# ---------------------------------------------------------------------------


def test_connect_ready(mock_urlopen, driver):
    """connect() should return True when WDA is ready."""
    mock_urlopen.return_value = _make_response({"value": {"ready": True}})
    assert driver.connect() is True
    assert driver.is_connected() is True


def test_connect_not_ready(mock_urlopen, driver):
    """connect() should return False when WDA is not ready."""
    mock_urlopen.return_value = _make_response({"value": {"ready": False}})
    with pytest.raises(DeviceNotConnectedError):
        driver.connect()


# ---------------------------------------------------------------------------
# screenshot
# ---------------------------------------------------------------------------


def test_take_screenshot(mock_urlopen, driver):
    """take_screenshot() should return decoded base64 bytes."""
    import base64
    original = b"fake_png_bytes"
    b64data = base64.b64encode(original).decode()
    mock_urlopen.return_value = _make_response({"value": b64data})
    result = driver.take_screenshot()
    assert result == original


# ---------------------------------------------------------------------------
# tap / swipe / press_key / app management / state
# ---------------------------------------------------------------------------


def test_tap(mock_urlopen, driver):
    """tap() should send a WDA tap request."""
    mock_urlopen.return_value = _make_response({"value": {}})
    driver.tap(100, 200)
    # Verify the request was made
    assert mock_urlopen.called


def test_swipe(mock_urlopen, driver):
    """swipe() should send a WDA swipe request."""
    mock_urlopen.return_value = _make_response({"value": {}})
    driver.swipe(0, 100, 200, 300, duration=0.5)
    assert mock_urlopen.called


def test_press_key_home(mock_urlopen, driver):
    """press_key('HOME') should send WDA home request."""
    mock_urlopen.return_value = _make_response({"value": {}})
    driver.press_key("HOME")
    assert mock_urlopen.called


def test_get_state(mock_urlopen, driver):
    """get_state() should return device state."""
    mock_urlopen.return_value = _make_response({"value": {}})
    state = driver.get_state()
    assert state.screen_name == "unknown"
    assert state.is_idle is True


def test_disconnect(mock_urlopen, driver):
    """disconnect() should set connected flag to False."""
    driver._connected = True
    driver.disconnect()
    assert driver.is_connected() is False
