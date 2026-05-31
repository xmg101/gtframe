"""Tests for StepExecutor."""
import pytest

from gtframe.orchestrator.step_executor import StepExecutor, StepResult
from gtframe.orchestrator.yaml_parser import StepDefinition
from gtframe.orchestrator.context import StepContext
from gtframe.device.base_driver import BaseDriver, DeviceState


class MockDriver(BaseDriver):
    """Simulated device driver."""

    def __init__(self):
        self._tapped = []
        self._swiped = []
        self._keys = []
        self._screen_name = "main_menu"
        self._is_idle = True

    def connect(self):
        self._connected = True
        return True

    def disconnect(self):
        self._connected = False

    def take_screenshot(self):
        return b"fake_screenshot_png"

    def tap(self, x, y):
        self._tapped.append((x, y))

    def swipe(self, x1, y1, x2, y2, duration=0.1):
        self._swiped.append((x1, y1, x2, y2, duration))

    def press_key(self, key):
        self._keys.append(key)

    def install_app(self, app_path):
        pass

    def launch_app(self, package_name):
        pass

    def close_app(self, package_name):
        pass

    def reset_app(self, package_name):
        pass

    def wait_for_idle(self, timeout=30):
        pass

    def get_state(self):
        return DeviceState(screen_name=self._screen_name, is_idle=self._is_idle)

    def pull_log(self):
        return []

    def reconnect(self):
        return True


class MockVision:
    """Simulated vision engine."""

    def __init__(self):
        self.texts_found = True
        self.ai_result = {"passed": True, "reason": "Looks good"}

    def locate(self, target, screenshot):
        if target == "missing":
            return None
        return {"x": 100, "y": 200}

    def find_text(self, text, screenshot, engine=None):
        if self.texts_found:
            return [{"text": text, "x": 50, "y": 100, "confidence": 0.95}]
        return []

    def ask_ai(self, prompt, screenshot):
        return self.ai_result

    def compare_snapshot(self, baseline, screenshot, threshold=0.9):
        return True


@pytest.fixture
def driver():
    return MockDriver()


@pytest.fixture
def vision():
    return MockVision()


@pytest.fixture
def executor(driver, vision):
    return StepExecutor(driver, vision)


@pytest.fixture
def ctx():
    return StepContext()


# ── wait_for_screen ─────────────────────────────────────────────


def test_wait_for_screen_match(executor, driver, ctx):
    """wait_for_screen matching screen name should pass."""
    driver._screen_name = "main_menu"
    step = StepDefinition(action="wait_for_screen", target="main_menu")
    result = executor.execute(step, ctx)
    assert result.passed is True


def test_wait_for_screen_no_match(executor, driver, ctx):
    """wait_for_screen with wrong screen should fail."""
    driver._screen_name = "loading"
    step = StepDefinition(action="wait_for_screen", target="main_menu", timeout=2)
    result = executor.execute(step, ctx)
    assert result.passed is False
    assert result.error is not None


# ── click ───────────────────────────────────────────────────────


def test_click_target(executor, driver, ctx):
    """click with a target should call driver.tap with located coordinates."""
    step = StepDefinition(action="click", target="start_button")
    result = executor.execute(step, ctx)
    assert result.passed is True
    assert len(driver._tapped) == 1
    assert driver._tapped[0] == (100, 200)


def test_click_missing_target(executor, driver, ctx):
    """click with unresolvable target should fail."""
    step = StepDefinition(action="click", target="missing")
    result = executor.execute(step, ctx)
    assert result.passed is False
    assert result.error is not None


# ── assert_ocr ──────────────────────────────────────────────────


def test_assert_ocr_found(executor, vision, ctx):
    """assert_ocr finding text should pass."""
    vision.texts_found = True
    step = StepDefinition(action="assert_ocr", text="开始游戏", engine="ocr")
    result = executor.execute(step, ctx)
    assert result.passed is True


def test_assert_ocr_not_found(executor, vision, ctx):
    """assert_ocr not finding text should fail."""
    vision.texts_found = False
    step = StepDefinition(action="assert_ocr", text="不存在的文字", engine="ocr")
    result = executor.execute(step, ctx)
    assert result.passed is False
    assert result.error is not None


# ── assert_ai ───────────────────────────────────────────────────


def test_assert_ai_passes(executor, vision, ctx):
    """assert_ai should return result with ai_response."""
    step = StepDefinition(action="assert_ai", prompt="Is this the game main menu?")
    result = executor.execute(step, ctx)
    assert result.passed is True
    assert result.ai_response is not None


# ── press_key ───────────────────────────────────────────────────


def test_press_key(executor, driver, ctx):
    """press_key should route to driver.press_key."""
    step = StepDefinition(action="press_key", target="HOME")
    result = executor.execute(step, ctx)
    assert result.passed is True
    assert "HOME" in driver._keys


# ── unknown action ──────────────────────────────────────────────


def test_unknown_action(executor, driver, ctx):
    """unknown action should fail with an error message."""
    step = StepDefinition(action="nonexistent_action")
    result = executor.execute(step, ctx)
    assert result.passed is False
    assert result.error is not None
    assert "unknown" in result.error.lower() or "unsupported" in result.error.lower()


# ── swipe ───────────────────────────────────────────────────────


def test_swipe(executor, driver, ctx):
    """swipe action should call driver.swipe with params."""
    step = StepDefinition(
        action="swipe",
        params={"x1": 0, "y1": 100, "x2": 200, "y2": 300, "duration": 0.5},
    )
    result = executor.execute(step, ctx)
    assert result.passed is True
    assert len(driver._swiped) == 1


# ── assert_snapshot ─────────────────────────────────────────────


def test_assert_snapshot(executor, ctx):
    """assert_snapshot should pass with a valid baseline."""
    step = StepDefinition(action="assert_snapshot", target="baseline_main_menu")
    result = executor.execute(step, ctx)
    assert result.passed is True
