"""Android device driver using ADB protocol."""
import subprocess
import tempfile
import time
from pathlib import Path
from subprocess import TimeoutExpired
from typing import Optional

from gtframe.device.base_driver import BaseDriver, DeviceState
from gtframe.exceptions import DeviceNotConnectedError

_KEY_MAP = {
    "HOME": "KEYCODE_HOME",
    "BACK": "KEYCODE_BACK",
    "MENU": "KEYCODE_MENU",
    "VOLUME_UP": "KEYCODE_VOLUME_UP",
    "VOLUME_DOWN": "KEYCODE_VOLUME_DOWN",
    "POWER": "KEYCODE_POWER",
    "ENTER": "KEYCODE_ENTER",
    "DEL": "KEYCODE_DEL",
}


class AndroidDriver(BaseDriver):
    """Driver for Android devices communicating via ADB."""

    def __init__(
        self,
        device_id: Optional[str] = None,
        adb_path: str = "adb",
        package_name: Optional[str] = None,
    ):
        self.device_id = device_id
        self.adb_path = adb_path
        self.package_name = package_name

    # ── internal helpers ────────────────────────────────────────

    def _adb_cmd(self, *args: str) -> list[str]:
        """Build the full ADB command list."""
        cmd = [self.adb_path]
        if self.device_id:
            cmd += ["-s", self.device_id]
        cmd.extend(args)
        return cmd

    def _adb(self, *args: str, timeout: int = 30) -> str:
        """Execute an ADB command and return stdout."""
        cmd = self._adb_cmd(*args)
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
        except TimeoutExpired as e:
            raise DeviceNotConnectedError(
                f"ADB command timed out after {timeout}s: {' '.join(cmd)}"
            ) from e

        if result.returncode != 0:
            raise DeviceNotConnectedError(
                f"ADB command failed (rc={result.returncode}): {' '.join(cmd)}\n"
                f"stderr: {result.stderr.strip()}"
            )
        return result.stdout.strip()

    # ── lifecycle ───────────────────────────────────────────────

    def connect(self) -> bool:
        """Verify the device is visible in adb devices."""
        output = self._adb("devices")
        for line in output.splitlines():
            # Skip header and empty lines
            if "List of devices" in line or not line.strip():
                continue
            parts = line.strip().split()
            if len(parts) >= 2 and parts[0] == self.device_id:
                if parts[1] == "device":
                    self._connected = True
                    return True

        raise DeviceNotConnectedError(
            f"Device {self.device_id} not found in adb devices"
        )

    def disconnect(self) -> None:
        """Mark the device as disconnected."""
        self._connected = False

    def reconnect(self) -> bool:
        """Kill and restart ADB server, then reconnect."""
        self._adb("kill-server", timeout=10)
        self._adb("start-server", timeout=10)
        return self.connect()

    # ── input ───────────────────────────────────────────────────

    def tap(self, x: int, y: int) -> None:
        """Tap at screen coordinates via ADB."""
        self._adb("shell", "input", "tap", str(x), str(y))

    def swipe(
        self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.1
    ) -> None:
        """Swipe from (x1,y1) to (x2,y2) over *duration* milliseconds."""
        ms = int(duration * 1000)
        self._adb(
            "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(ms)
        )

    def press_key(self, key: str) -> None:
        """Press a named hardware key."""
        keycode = _KEY_MAP.get(key.upper(), key.upper())
        self._adb("shell", "input", "keyevent", keycode)

    # ── app management ──────────────────────────────────────────

    def install_app(self, app_path: str) -> None:
        """Install an APK via ADB."""
        self._adb("install", "-r", app_path, timeout=120)

    def launch_app(self, package_name: str) -> None:
        """Launch an app by package name using monkey."""
        self._adb(
            "shell",
            "monkey",
            "-p",
            package_name,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
            timeout=30,
        )

    def close_app(self, package_name: str) -> None:
        """Force-stop an app by package name."""
        self._adb("shell", "am", "force-stop", package_name)

    def reset_app(self, package_name: str) -> None:
        """Clear app data via pm clear."""
        self._adb("shell", "pm", "clear", package_name)

    # ── state & screenshot ──────────────────────────────────────

    def take_screenshot(self) -> bytes:
        """Capture screen via screencap and pull the file."""
        remote_path = "/sdcard/screen.png"
        self._adb("shell", "screencap", "-p", remote_path)

        tmp = Path(tempfile.mktemp(suffix=".png"))
        try:
            self._adb("pull", remote_path, str(tmp))
            data = tmp.read_bytes()
        finally:
            if tmp.exists():
                tmp.unlink()
        return data

    def get_state(self) -> DeviceState:
        """Parse GAME_TEST logcat tags for state info."""
        try:
            output = self._adb("logcat", "-d", "-s", "GAME_TEST")
        except DeviceNotConnectedError:
            return DeviceState(screen_name="unknown", is_idle=True, extra={})

        screen_name = "unknown"
        is_idle = True

        for line in output.splitlines():
            if "screen:" in line:
                idx = line.index("screen:")
                screen_name = line[idx + len("screen:"):].strip()
            if "is_idle:" in line:
                idx = line.index("is_idle:")
                val = line[idx + len("is_idle:"):].strip()
                is_idle = val.lower() == "true"

        return DeviceState(screen_name=screen_name, is_idle=is_idle, extra={})

    def wait_for_idle(self, timeout: int = 30) -> None:
        """Poll get_state() until is_idle=True or timeout."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = self.get_state()
            if state.is_idle:
                return
            time.sleep(1)
        raise TimeoutError(f"Device did not become idle within {timeout}s")

    def pull_log(self) -> list[str]:
        """Pull full device log."""
        output = self._adb("logcat", "-d")
        return output.splitlines() if output else []
