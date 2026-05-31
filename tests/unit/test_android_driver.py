"""Unit tests for AndroidDriver with mocked ADB."""
import os
import subprocess
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from gtframe.device.android_driver import AndroidDriver
from gtframe.exceptions import DeviceNotConnectedError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_subprocess():
    with patch("gtframe.device.android_driver.subprocess") as mock:
        yield mock


@pytest.fixture
def driver():
    return AndroidDriver(device_id="emulator-5554")


@pytest.fixture
def auto_driver():
    """Driver without device_id — should auto-discover."""
    return AndroidDriver()


# ---------------------------------------------------------------------------
# _adb helper
# ---------------------------------------------------------------------------


def test_adb_success(mock_subprocess, driver):
    """_adb() should return stdout on success."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "success\n"
    mock_subprocess.run.return_value = mock_process

    result = driver._adb("shell", "echo", "hello")
    assert result == "success"

    # Verify correct command construction
    expected_cmd = ["adb", "-s", "emulator-5554", "shell", "echo", "hello"]
    mock_subprocess.run.assert_called_once_with(
        expected_cmd, capture_output=True, text=True, timeout=30
    )


def test_adb_failure(mock_subprocess, driver):
    """_adb() should raise DeviceNotConnectedError on non-zero returncode."""
    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_process.stdout = ""
    mock_subprocess.run.return_value = mock_process

    with pytest.raises(DeviceNotConnectedError):
        driver._adb("shell", "echo", "fail")


def test_adb_timeout(mock_subprocess, driver):
    """_adb() should raise DeviceNotConnectedError on timeout."""
    mock_subprocess.run.side_effect = subprocess.TimeoutExpired(cmd="adb", timeout=30)

    with pytest.raises(DeviceNotConnectedError):
        driver._adb("shell", "echo", "timeout")


# ---------------------------------------------------------------------------
# connect
# ---------------------------------------------------------------------------


def test_connect_device_found(mock_subprocess, driver):
    """connect() should return True when device is in adb devices list."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = (
        "List of devices attached\nemulator-5554\tdevice\n"
    )
    mock_subprocess.run.return_value = mock_process

    assert driver.connect() is True
    assert driver.is_connected() is True


def test_connect_device_not_found(mock_subprocess, driver):
    """connect() should raise DeviceNotConnectedError when specific device not listed."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "List of devices attached\n\n"
    mock_subprocess.run.return_value = mock_process

    with pytest.raises(DeviceNotConnectedError):
        driver.connect()
    assert driver.is_connected() is False


def test_connect_auto_discover(mock_subprocess, auto_driver):
    """connect() without device_id should pick the first available device."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = (
        "List of devices attached\n"
        "0123456789abcdef\tdevice\n"
    )
    mock_subprocess.run.return_value = mock_process

    assert auto_driver.connect() is True
    assert auto_driver.is_connected() is True
    assert auto_driver.device_id == "0123456789abcdef"


# ---------------------------------------------------------------------------
# screenshot
# ---------------------------------------------------------------------------


def test_take_screenshot(mock_subprocess, driver):
    """take_screenshot() should pull PNG bytes from device."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = ""
    mock_subprocess.run.return_value = mock_process

    # Create a real temp file so take_screenshot can read it after "adb pull"
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(b"real_png_bytes")
        tmp_path = tmp.name

    try:
        with patch("gtframe.device.android_driver.tempfile.mktemp",
                   return_value=tmp_path):
            result = driver.take_screenshot()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    assert result == b"real_png_bytes"

    # Find calls to screencap and pull
    call_args_list = [call[0] for call in mock_subprocess.run.call_args_list]
    assert any("screencap" in " ".join(args[0]) for args in call_args_list)
    assert any("pull" in " ".join(args[0]) for args in call_args_list)


# ---------------------------------------------------------------------------
# tap / swipe / press_key
# ---------------------------------------------------------------------------


def test_tap(mock_subprocess, driver):
    """tap() should send input tap command."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_subprocess.run.return_value = mock_process

    driver.tap(100, 200)
    cmd_called = mock_subprocess.run.call_args[0][0]
    assert "input" in cmd_called
    assert "tap" in cmd_called
    assert "100" in cmd_called
    assert "200" in cmd_called


def test_swipe(mock_subprocess, driver):
    """swipe() should send input swipe command."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_subprocess.run.return_value = mock_process

    driver.swipe(0, 100, 200, 300, duration=0.5)
    cmd_called = mock_subprocess.run.call_args[0][0]
    assert "input" in cmd_called
    assert "swipe" in cmd_called


def test_press_key_home(mock_subprocess, driver):
    """press_key('HOME') should send keyevent KEYCODE_HOME."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_subprocess.run.return_value = mock_process

    driver.press_key("HOME")
    cmd_called = mock_subprocess.run.call_args[0][0]
    assert "keyevent" in cmd_called
    assert "KEYCODE_HOME" in cmd_called or "3" in cmd_called


def test_press_key_back(mock_subprocess, driver):
    """press_key('BACK') should send keyevent KEYCODE_BACK."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_subprocess.run.return_value = mock_process

    driver.press_key("BACK")
    cmd_called = mock_subprocess.run.call_args[0][0]
    assert "keyevent" in cmd_called
    assert "KEYCODE_BACK" in cmd_called or "4" in cmd_called


# ---------------------------------------------------------------------------
# app management
# ---------------------------------------------------------------------------


def test_install_app(mock_subprocess, driver):
    """install_app() should run adb install."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_subprocess.run.return_value = mock_process

    driver.install_app("/tmp/test.apk")
    cmd = mock_subprocess.run.call_args[0][0]
    assert "install" in cmd
    assert "-r" in cmd


def test_launch_app(mock_subprocess, driver):
    """launch_app() should run monkey to launch activity."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_subprocess.run.return_value = mock_process

    driver.launch_app("com.example.game")
    cmd = mock_subprocess.run.call_args[0][0]
    assert "monkey" in cmd or "am" in cmd


def test_close_app(mock_subprocess, driver):
    """close_app() should run am force-stop."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_subprocess.run.return_value = mock_process

    driver.close_app("com.example.game")
    cmd = mock_subprocess.run.call_args[0][0]
    assert "force-stop" in cmd


def test_reset_app(mock_subprocess, driver):
    """reset_app() should run pm clear."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_subprocess.run.return_value = mock_process

    driver.reset_app("com.example.game")
    cmd = mock_subprocess.run.call_args[0][0]
    assert "pm" in cmd and "clear" in cmd


# ---------------------------------------------------------------------------
# get_state / wait_for_idle
# ---------------------------------------------------------------------------


def test_get_state(mock_subprocess, driver):
    """get_state() should parse logcat output for screen name and idle status."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = (
        "05-16 10:00:00.000 12345 12345 D GAME_TEST: screen:loading\n"
        "05-16 10:00:01.000 12345 12345 D GAME_TEST: is_idle:false\n"
    )
    mock_subprocess.run.return_value = mock_process

    state = driver.get_state()
    assert state.screen_name == "loading"
    assert state.is_idle is False


def test_wait_for_idle(mock_subprocess, driver):
    """wait_for_idle() should poll until is_idle=True."""
    # First two polls return idle=False, third returns idle=True
    mock_process_not_idle = MagicMock()
    mock_process_not_idle.returncode = 0
    mock_process_not_idle.stdout = (
        "GAME_TEST: is_idle:false\n"
    )

    mock_process_idle = MagicMock()
    mock_process_idle.returncode = 0
    mock_process_idle.stdout = (
        "GAME_TEST: is_idle:true\n"
    )

    mock_subprocess.run.side_effect = [
        mock_process_not_idle,
        mock_process_not_idle,
        mock_process_idle,
    ]

    # Should not raise — idle detected within timeout
    driver.wait_for_idle(timeout=5)
    assert True


def test_wait_for_idle_timeout(mock_subprocess, driver):
    """wait_for_idle() should raise when timeout expires."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "GAME_TEST: is_idle:false\n"
    mock_subprocess.run.return_value = mock_process

    with pytest.raises(TimeoutError):
        driver.wait_for_idle(timeout=2)  # short timeout


# ---------------------------------------------------------------------------
# pull_log / reconnect / disconnect
# ---------------------------------------------------------------------------


def test_pull_log(mock_subprocess, driver):
    """pull_log() should return log lines."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "line1\nline2\nline3\n"
    mock_subprocess.run.return_value = mock_process

    lines = driver.pull_log()
    assert lines == ["line1", "line2", "line3"]


def test_reconnect(mock_subprocess, driver):
    """reconnect() should kill and restart ADB server."""
    def fake_run(cmd, *args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        # For 'adb devices' command, return the device in the list
        if "devices" in cmd:
            m.stdout = "List of devices attached\nemulator-5554\tdevice\n"
        return m

    mock_subprocess.run.side_effect = fake_run

    result = driver.reconnect()
    assert result is True


def test_disconnect(mock_subprocess, driver):
    """disconnect() should set connected flag to False."""
    driver._connected = True
    driver.disconnect()
    assert driver.is_connected() is False
