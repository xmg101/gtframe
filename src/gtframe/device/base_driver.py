"""Base driver and device abstractions."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DeviceState:
    """Represents the current state of a device."""
    screen_name: str = ""
    is_idle: bool = True
    extra: dict[str, Any] = field(default_factory=dict)


class BaseDriver(ABC):
    """Abstract base class for all device drivers.

    Subclasses must implement all abstract methods to support
    device-specific operations like screenshot, tap, swipe, etc.
    """

    _connected: bool = False

    # ── lifecycle ──────────────────────────────────────────────

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the device."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection to the device."""

    @abstractmethod
    def reconnect(self) -> bool:
        """Reconnect to the device."""

    # ── input ──────────────────────────────────────────────────

    @abstractmethod
    def tap(self, x: int, y: int) -> None:
        """Tap at the given screen coordinates."""

    @abstractmethod
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.1) -> None:
        """Swipe from (x1, y1) to (x2, y2) over the given duration."""

    @abstractmethod
    def press_key(self, key: str) -> None:
        """Press a hardware key (e.g. HOME, BACK, MENU)."""

    # ── app management ─────────────────────────────────────────

    @abstractmethod
    def install_app(self, app_path: str) -> None:
        """Install an application from the given path."""

    @abstractmethod
    def launch_app(self, package_name: str) -> None:
        """Launch an application by package name."""

    @abstractmethod
    def close_app(self, package_name: str) -> None:
        """Close an application by package name."""

    @abstractmethod
    def reset_app(self, package_name: str) -> None:
        """Reset application data for the given package."""

    # ── state & screenshot ─────────────────────────────────────

    @abstractmethod
    def take_screenshot(self) -> bytes:
        """Capture the current screen and return raw image bytes."""

    @abstractmethod
    def get_state(self) -> DeviceState:
        """Return the current device state."""

    @abstractmethod
    def wait_for_idle(self, timeout: int = 30) -> None:
        """Block until the device becomes idle or timeout expires."""

    @abstractmethod
    def pull_log(self) -> list[str]:
        """Pull device log lines."""

    # ── helper ─────────────────────────────────────────────────

    def is_connected(self) -> bool:
        """Return whether the driver is currently connected."""
        return self._connected
