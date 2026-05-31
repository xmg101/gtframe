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

    def diagnose_discovery(self) -> dict[str, str]:
        """Check whether ADB and WDA tools are available.

        Returns a dict with diagnostic messages per platform,
        instead of silently swallowing errors.
        """
        diagnoses: dict[str, str] = {}
        import shutil

        # Check ADB
        adb_path = shutil.which("adb")
        if adb_path:
            try:
                import subprocess
                result = subprocess.run(
                    ["adb", "devices"], capture_output=True, text=True, timeout=10
                )
                devices_found = False
                for line in result.stdout.splitlines():
                    if "\tdevice" in line and "List" not in line:
                        devices_found = True
                        break
                if devices_found:
                    diagnoses["android"] = "ok"
                else:
                    diagnoses["android"] = "ADB 已安装，但未检测到已连接的 Android 设备，请确认 USB 调试已开启"
            except Exception as e:
                diagnoses["android"] = f"ADB 执行失败: {e}"
        else:
            diagnoses["android"] = "ADB 未安装，请安装 Android SDK Platform Tools (https://developer.android.com/studio/releases/platform-tools)"

        # Check WDA / iOS
        wda_url = shutil.which("ideviceinstaller")
        if wda_url:
            diagnoses["ios"] = "ios 工具链已安装，可通过 WDA 连接（需 Mac 环境）"
        else:
            diagnoses["ios"] = "iOS 检测需要 Mac 环境 + WebDriverAgent"

        return diagnoses
