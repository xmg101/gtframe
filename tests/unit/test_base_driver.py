"""Tests for BaseDriver abstract interface."""
from abc import ABC
from gtframe.device.base_driver import BaseDriver, DeviceState


class ConcreteDriver(BaseDriver):
    """Minimal concrete implementation for testing."""

    def connect(self):
        self._connected = True
        return True

    def disconnect(self):
        self._connected = False

    def take_screenshot(self):
        return b"fake_png_data"

    def tap(self, x, y):
        pass

    def swipe(self, x1, y1, x2, y2, duration=0.1):
        pass

    def press_key(self, key):
        pass

    def install_app(self, app_path):
        pass

    def launch_app(self, package_name):
        pass

    def close_app(self, package_name):
        pass

    def wait_for_idle(self, timeout=30):
        pass

    def get_state(self):
        return DeviceState(screen_name="main_menu", is_idle=True, extra={})

    def pull_log(self):
        return []

    def reconnect(self):
        self._connected = True
        return True

    def reset_app(self, package_name):
        pass


def test_base_driver_is_abstract():
    """BaseDriver should not be directly instantiable (abstract)."""
    try:
        BaseDriver()  # type: ignore
        assert False, "Should have raised TypeError"
    except TypeError:
        pass


def test_concrete_driver_connect():
    """connect() should return True on success."""
    d = ConcreteDriver()
    assert d.connect() is True


def test_concrete_driver_is_connected_default():
    """is_connected() should return False before connect()."""
    d = ConcreteDriver()
    assert d.is_connected() is False


def test_concrete_driver_is_connected_after_connect():
    """is_connected() should return True after connect()."""
    d = ConcreteDriver()
    d.connect()
    assert d.is_connected() is True


def test_concrete_driver_screenshot():
    """take_screenshot() should return bytes."""
    d = ConcreteDriver()
    data = d.take_screenshot()
    assert isinstance(data, bytes)
    assert data == b"fake_png_data"


def test_concrete_driver_get_state():
    """get_state() should return DeviceState with correct fields."""
    d = ConcreteDriver()
    state = d.get_state()
    assert isinstance(state, DeviceState)
    assert state.screen_name == "main_menu"
    assert state.is_idle is True
    assert isinstance(state.extra, dict)


def test_concrete_driver_disconnect():
    """disconnect() should change is_connected to False."""
    d = ConcreteDriver()
    d.connect()
    assert d.is_connected() is True
    d.disconnect()
    assert d.is_connected() is False
