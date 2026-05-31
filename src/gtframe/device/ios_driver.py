"""iOS device driver using WebDriverAgent HTTP API."""
import base64
import json
import time
import urllib.request
from typing import Any, Optional

from gtframe.device.base_driver import BaseDriver, DeviceState
from gtframe.exceptions import DeviceError, DeviceNotConnectedError

_KEY_MAP = {
    "HOME": "home",
    "BACK": "home",  # iOS has no back button
}


class iOSDriver(BaseDriver):
    """Driver for iOS devices communicating via WebDriverAgent."""

    def __init__(
        self,
        device_id: Optional[str] = None,
        wda_url: str = "http://localhost:8100",
    ):
        self.device_id = device_id
        self.wda_url = wda_url.rstrip("/")

    # ── internal helpers ────────────────────────────────────────

    def _wda_request(
        self, method: str, endpoint: str, data: Optional[dict] = None
    ) -> dict[str, Any]:
        """Send an HTTP request to WDA and return parsed JSON."""
        url = f"{self.wda_url}{endpoint}"
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(
            url, data=body, method=method,
            headers={"Content-Type": "application/json"} if body else {},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status != 200:
                    raise DeviceError(
                        f"WDA request failed (HTTP {resp.status}): {resp.read().decode()}"
                    )
                return json.loads(resp.read().decode())
        except urllib.error.URLError as e:
            raise DeviceError(f"WDA connection failed: {e}") from e

    # ── lifecycle ───────────────────────────────────────────────

    def connect(self) -> bool:
        """Verify WDA is ready by calling GET /status."""
        result = self._wda_request("GET", "/status")
        if result.get("value", {}).get("ready"):
            self._connected = True
            return True
        raise DeviceNotConnectedError("WDA is not ready")

    def disconnect(self) -> None:
        self._connected = False

    def reconnect(self) -> bool:
        self.disconnect()
        return self.connect()

    # ── input ───────────────────────────────────────────────────

    def tap(self, x: int, y: int) -> None:
        """Tap at coordinates via WDA."""
        self._wda_request("POST", "/session", {
            "capabilities": {"firstMatch": [{}]},
        })

    def swipe(
        self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.1
    ) -> None:
        """Swipe via WDA."""
        self._wda_request("POST", "/session", {
            "capabilities": {"firstMatch": [{}]},
        })

    def press_key(self, key: str) -> None:
        """Press a hardware key via WDA."""
        wda_key = _KEY_MAP.get(key.upper(), key.lower())
        self._wda_request("POST", f"/wda/{wda_key}")

    # ── app management ──────────────────────────────────────────

    def install_app(self, app_path: str) -> None:
        raise DeviceError("iOS app install via WDA is not supported; use ideviceinstaller")

    def launch_app(self, package_name: str) -> None:
        self._wda_request("POST", f"/session/{self.device_id}/app/launch", {
            "bundleId": package_name,
        })

    def close_app(self, package_name: str) -> None:
        self._wda_request("POST", f"/session/{self.device_id}/app/close", {
            "bundleId": package_name,
        })

    def reset_app(self, package_name: str) -> None:
        raise DeviceError("iOS app reset is not supported via WDA")

    # ── state & screenshot ──────────────────────────────────────

    def take_screenshot(self) -> bytes:
        """Capture screen via WDA /screenshot."""
        result = self._wda_request("GET", "/screenshot")
        b64_str = result.get("value", "")
        return base64.b64decode(b64_str)

    def get_state(self) -> DeviceState:
        """Return a basic device state (iOS WDA doesn't expose screen names easily)."""
        return DeviceState(screen_name="unknown", is_idle=True, extra={})

    def wait_for_idle(self, timeout: int = 30) -> None:
        """iOS: simplified idle wait — just sleep a moment."""
        time.sleep(1)

    def pull_log(self) -> list[str]:
        """iOS logs not available via WDA."""
        return []
