"""Exception hierarchy for gtframe."""


class GTFrameError(Exception):
    """Base exception for all gtframe errors."""


class DeviceError(GTFrameError):
    """Base exception for device-related errors."""


class DeviceNotConnectedError(DeviceError):
    """Device is not connected or became disconnected."""


class StepTimeoutError(GTFrameError):
    """A test step timed out."""


class VisionMatchError(GTFrameError):
    """Vision engine failed to find a match."""


class AITimeoutError(GTFrameError):
    """AI vision engine timed out or returned an error."""


class ConfigError(GTFrameError):
    """Configuration loading or validation error."""


class YAMLError(GTFrameError):
    """YAML parsing error for test case files."""
