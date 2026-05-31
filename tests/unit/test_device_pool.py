"""Tests for DevicePool device management."""
import pytest
from gtframe.device.device_pool import DevicePool
from gtframe.device.base_driver import BaseDriver, DeviceState
from gtframe.exceptions import DeviceError


class MockDriver(BaseDriver):
    """Minimal mock driver for testing."""

    def __init__(self, name="mock"):
        self._name = name

    def connect(self):
        self._connected = True
        return True

    def disconnect(self):
        self._connected = False

    def take_screenshot(self):
        return b"mock"

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
        return DeviceState(screen_name="test", is_idle=True, extra={})

    def pull_log(self):
        return []

    def reconnect(self):
        self._connected = True
        return True

    def reset_app(self, package_name):
        pass


@pytest.fixture
def pool():
    return DevicePool()


def test_register_and_get(pool):
    """register() then get() should return the same driver instance."""
    d = MockDriver()
    pool.register("device_01", d)
    assert pool.get("device_01") is d


def test_get_unregistered_device(pool):
    """get() on an unknown name should raise DeviceError."""
    with pytest.raises(DeviceError, match="not registered"):
        pool.get("nonexistent")


def test_register_calls_connect(pool):
    """register() should call driver.connect()."""
    d = MockDriver()
    assert d.is_connected() is False
    pool.register("device_01", d)
    assert d.is_connected() is True


def test_unregister(pool):
    """unregister() should call disconnect and remove the device."""
    d = MockDriver()
    pool.register("device_01", d)
    pool.unregister("device_01")

    assert d.is_connected() is False
    with pytest.raises(DeviceError, match="not registered"):
        pool.get("device_01")


def test_list_devices(pool):
    """list_devices() should return all registered names."""
    pool.register("a", MockDriver())
    pool.register("b", MockDriver())
    pool.register("c", MockDriver())
    names = pool.list_devices()
    assert sorted(names) == ["a", "b", "c"]


def test_unregister_unknown(pool):
    """unregister() a non-registered name should not raise."""
    pool.unregister("ghost")  # should not raise
