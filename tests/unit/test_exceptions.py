"""Tests for exception hierarchy."""
from gtframe.exceptions import (
    GTFrameError,
    DeviceError,
    DeviceNotConnectedError,
    StepTimeoutError,
    VisionMatchError,
    AITimeoutError,
    ConfigError,
    YAMLError,
)


def test_gtframe_error_base():
    """GTFrameError should be the base exception, catchable via except GTFrameError."""
    assert issubclass(DeviceError, GTFrameError)
    assert issubclass(StepTimeoutError, GTFrameError)
    assert issubclass(VisionMatchError, GTFrameError)
    assert issubclass(AITimeoutError, GTFrameError)
    assert issubclass(ConfigError, GTFrameError)
    assert issubclass(YAMLError, GTFrameError)
    assert issubclass(DeviceNotConnectedError, DeviceError)


def test_gtframe_error_default_message():
    """GTFrameError can be raised with no args."""
    exc = GTFrameError()
    assert str(exc) == ""


def test_gtframe_error_custom_message():
    """GTFrameError stores message."""
    exc = GTFrameError("something went wrong")
    assert str(exc) == "something went wrong"


def test_device_not_connected_error():
    """DeviceNotConnectedError should be distinguishable from generic DeviceError."""
    general = DeviceError("device problem")
    specific = DeviceNotConnectedError("device ADB123 not found")
    assert isinstance(specific, DeviceError)
    assert not isinstance(general, DeviceNotConnectedError)


def test_all_exceptions_accept_message():
    """All exception types accept an optional message string."""
    for exc_cls in [
        DeviceError,
        DeviceNotConnectedError,
        StepTimeoutError,
        VisionMatchError,
        AITimeoutError,
        ConfigError,
        YAMLError,
    ]:
        exc = exc_cls("test message")
        assert str(exc) == "test message", f"{exc_cls.__name__} failed"
