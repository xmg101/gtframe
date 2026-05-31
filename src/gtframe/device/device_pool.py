"""Device pool for managing multiple device drivers."""
from typing import Optional

from gtframe.device.base_driver import BaseDriver
from gtframe.exceptions import DeviceError


class DevicePool:
    """Central registry for device drivers.

    Handles registration, lookup, and lifecycle management of
    Android/iOS/Editor device drivers.
    """

    def __init__(self):
        self._drivers: dict[str, BaseDriver] = {}

    def register(self, name: str, driver: BaseDriver) -> None:
        """Register a driver by name and call connect()."""
        driver.connect()
        self._drivers[name] = driver

    def get(self, name: str) -> BaseDriver:
        """Return a registered driver by name."""
        driver = self._drivers.get(name)
        if driver is None:
            raise DeviceError(f"Device '{name}' not registered")
        return driver

    def unregister(self, name: str) -> None:
        """Disconnect and remove a registered driver."""
        driver = self._drivers.pop(name, None)
        if driver is not None:
            driver.disconnect()

    def list_devices(self) -> list[str]:
        """Return names of all registered devices."""
        return list(self._drivers.keys())

    def auto_discover(self) -> dict[str, str]:
        """Auto-discover available devices.

        Returns dict mapping device name → device type string.
        Currently only ADB detection is implemented.
        """
        found: dict[str, str] = {}
        try:
            from gtframe.device.android_driver import AndroidDriver

            d = AndroidDriver()
            d.connect()
            d.disconnect()
            found["android_01"] = "android"
        except Exception:
            pass

        try:
            from gtframe.device.ios_driver import iOSDriver

            d = iOSDriver()
            d.connect()
            d.disconnect()
            found["ios_01"] = "ios"
        except Exception:
            pass

        return found
