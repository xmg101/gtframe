"""End-to-end pipeline test using mock drivers and mock vision."""
import os
import tempfile

import pytest

from gtframe.device.base_driver import BaseDriver, DeviceState
from gtframe.device.device_pool import DevicePool
from gtframe.orchestrator.test_runner import TestRunner
from gtframe.vision.engine import VisionEngine


class MockPipelineDriver(BaseDriver):
    """Mock driver that simulates a real device."""

    def connect(self):
        self._connected = True
        return True

    def disconnect(self):
        self._connected = False

    def take_screenshot(self):
        return b"mock_screenshot_png"

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

    def reset_app(self, package_name):
        pass

    def wait_for_idle(self, timeout=30):
        pass

    def get_state(self):
        return DeviceState(screen_name="main_menu", is_idle=True, extra={})

    def pull_log(self):
        return ["mock log line 1", "mock log line 2"]

    def reconnect(self):
        return True


SAMPLE_CASE_YAML = """
name: test_flow
game: mock_game
device: mock_01
timeout: 30
retry: 1
steps:
  - action: wait_for_screen
    target: main_menu
    timeout: 5

  - action: click
    target: start_button

  - action: assert_ocr
    text: 开始游戏
    engine: ocr

  - action: assert_ai
    prompt: 当前画面是否为游戏主界面？
    screenshot: true
"""


def test_full_pipeline():
    """Run a full pipeline with mock driver and mock vision."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write test YAML
        yaml_path = os.path.join(tmpdir, "test_flow.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(SAMPLE_CASE_YAML)

        # Setup device pool
        pool = DevicePool()
        pool.register("mock_01", MockPipelineDriver())

        # Setup vision engine (will use mock AI since no API key)
        vision = VisionEngine()

        # Run test
        runner = TestRunner(pool, vision)
        results = runner.run_file(yaml_path)

        # Verify pipeline ran without crashing and returns StepResult objects
        assert len(results) > 0
        # wait_for_screen should pass (screen name matches)
        assert results[0].passed, f"Expected wait_for_screen to pass: {results[0].error}"
        # The mock environment has no templates, so click may fail — but the pipeline should complete
        assert all(isinstance(r.passed, bool) for r in results)
        # The report should include screenshots
        assert any(r.screenshot is not None for r in results)


def test_pipeline_failure_detection():
    """Pipeline should detect and report failures correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # YAML with a wait_for_screen that will never match
        failing_yaml = """
name: test_failure
game: mock_game
device: mock_01
timeout: 5
retry: 1
steps:
  - action: wait_for_screen
    target: nonexistent_screen
    timeout: 2
"""
        yaml_path = os.path.join(tmpdir, "test_failure.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(failing_yaml)

        pool = DevicePool()
        pool.register("mock_01", MockPipelineDriver())

        vision = VisionEngine()
        runner = TestRunner(pool, vision)
        results = runner.run_file(yaml_path)

        assert len(results) == 2  # 1 step × (1 retry + 1 initial)
        assert all(not r.passed for r in results)
