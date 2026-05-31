"""Test step executor with action dispatch."""
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from gtframe.exceptions import VisionMatchError
from gtframe.orchestrator.context import StepContext
from gtframe.orchestrator.yaml_parser import StepDefinition
from gtframe.device.base_driver import BaseDriver


@dataclass
class StepResult:
    """Result of executing a single test step."""
    step: StepDefinition
    passed: bool = False
    duration: float = 0.0
    screenshot: Optional[bytes] = None
    error: Optional[str] = None
    ai_response: Optional[dict[str, Any]] = None


class StepExecutor:
    """Execute test steps by dispatching to the appropriate handler.

    Handles 10 action types: wait_for_screen, click, click_by_text,
    swipe, assert_ocr, assert_ai, assert_snapshot, press_key,
    custom_assert, script.
    """

    def __init__(self, driver: BaseDriver, vision_engine: Any):
        self.driver = driver
        self.vision = vision_engine
        self._custom_assertions: dict[str, Callable] = {}

        self._handlers: dict[str, Callable] = {
            "wait_for_screen": self._handle_wait_for_screen,
            "click": self._handle_click,
            "click_by_text": self._handle_click_by_text,
            "swipe": self._handle_swipe,
            "assert_ocr": self._handle_assert_ocr,
            "assert_ai": self._handle_assert_ai,
            "assert_snapshot": self._handle_assert_snapshot,
            "press_key": self._handle_press_key,
            "custom_assert": self._handle_custom_assert,
            "script": self._handle_script,
        }

    def register_assertion(self, name: str, fn: Callable) -> None:
        """Register a custom assertion function."""
        self._custom_assertions[name] = fn

    def execute(self, step: StepDefinition, ctx: StepContext) -> StepResult:
        """Execute a single test step."""
        start = time.monotonic()

        try:
            result_data = self._dispatch(step, ctx)
            passed = True
            error = None
            ai_response = None

            if isinstance(result_data, dict):
                passed = result_data.get("passed", True)
                error = result_data.get("error")
                ai_response = result_data.get("ai_response")

            screenshot = self.driver.take_screenshot()
            elapsed = time.monotonic() - start
            return StepResult(
                step=step,
                passed=passed,
                duration=elapsed,
                screenshot=screenshot,
                error=error,
                ai_response=ai_response,
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            screenshot = None
            try:
                screenshot = self.driver.take_screenshot()
            except Exception:
                pass
            return StepResult(
                step=step,
                passed=False,
                duration=elapsed,
                screenshot=screenshot,
                error=str(e),
            )

    # ── dispatch ────────────────────────────────────────────────

    def _dispatch(self, step: StepDefinition, ctx: StepContext) -> Any:
        handler = self._handlers.get(step.action)
        if handler is None:
            raise ValueError(f"Unknown action: {step.action}")
        return handler(step, ctx)

    # ── action handlers ─────────────────────────────────────────

    def _handle_wait_for_screen(
        self, step: StepDefinition, ctx: StepContext
    ) -> dict:
        timeout = step.timeout or 30
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = self.driver.get_state()
            if state.screen_name == step.target:
                return {"passed": True}
            time.sleep(1)
        return {
            "passed": False,
            "error": f"Screen '{step.target}' not reached within {timeout}s",
        }

    def _handle_click(self, step: StepDefinition, ctx: StepContext) -> dict:
        screenshot = self.driver.take_screenshot()
        target = step.target or step.text
        if not target:
            return {"passed": False, "error": "No target specified for click"}

        location = self.vision.locate(target, screenshot)
        if location is None:
            return {"passed": False, "error": f"Target '{target}' not found on screen"}

        self.driver.tap(location["x"], location["y"])
        return {"passed": True}

    def _handle_click_by_text(
        self, step: StepDefinition, ctx: StepContext
    ) -> dict:
        screenshot = self.driver.take_screenshot()
        results = self.vision.find_text(step.text, screenshot)
        if not results:
            if step.ai_fallback:
                ai_loc = getattr(self.vision, "ai_locate", None)
                if ai_loc:
                    location = ai_loc(step.text, screenshot)
                    if location:
                        self.driver.tap(location["x"], location["y"])
                        return {"passed": True, "ai_response": {"method": "ai_fallback"}}
            return {"passed": False, "error": f"Text '{step.text}' not found on screen"}

        x, y = results[0]["x"], results[0]["y"]
        self.driver.tap(x, y)
        return {"passed": True}

    def _handle_swipe(self, step: StepDefinition, ctx: StepContext) -> dict:
        p = step.params
        self.driver.swipe(
            p.get("x1", 0),
            p.get("y1", 0),
            p.get("x2", 100),
            p.get("y2", 100),
            duration=p.get("duration", 0.1),
        )
        return {"passed": True}

    def _handle_assert_ocr(
        self, step: StepDefinition, ctx: StepContext
    ) -> dict:
        screenshot = self.driver.take_screenshot()
        results = self.vision.find_text(step.text, screenshot, engine=step.engine)
        if not results:
            return {"passed": False, "error": f"Text '{step.text}' not found on screen"}
        return {"passed": True}

    def _handle_assert_ai(
        self, step: StepDefinition, ctx: StepContext
    ) -> dict:
        screenshot = self.driver.take_screenshot()
        result = self.vision.ask_ai(step.prompt or "", screenshot)
        return {
            "passed": result.get("passed", True),
            "error": result.get("reason") if not result.get("passed") else None,
            "ai_response": result,
        }

    def _handle_assert_snapshot(
        self, step: StepDefinition, ctx: StepContext
    ) -> dict:
        screenshot = self.driver.take_screenshot()
        baseline = step.target or "baseline"
        match = self.vision.compare_snapshot(baseline, screenshot)
        if not match:
            return {"passed": False, "error": f"Snapshot '{baseline}' does not match"}
        return {"passed": True}

    def _handle_press_key(self, step: StepDefinition, ctx: StepContext) -> dict:
        key = step.target or step.text or "HOME"
        self.driver.press_key(key)
        return {"passed": True}

    def _handle_custom_assert(self, step: StepDefinition, ctx: StepContext) -> dict:
        fn = self._custom_assertions.get(step.target or "")
        if fn is None:
            return {"passed": False, "error": f"Custom assertion '{step.target}' not registered"}
        return fn(step, ctx)

    def _handle_script(self, step: StepDefinition, ctx: StepContext) -> dict:
        if step.script:
            local_vars = {"driver": self.driver, "vision": self.vision, "ctx": ctx}
            exec(step.script, {}, local_vars)
        return {"passed": True}
