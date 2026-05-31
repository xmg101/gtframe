"""Test runner that orchestrates full test case execution."""
import time
from typing import Optional

from gtframe.device.device_pool import DevicePool
from gtframe.orchestrator.context import StepContext
from gtframe.orchestrator.step_executor import StepExecutor, StepResult
from gtframe.orchestrator.yaml_parser import TestCaseDefinition, YAMLParser


class TestRunner:
    """Orchestrates test case execution from YAML definitions."""

    def __init__(self, device_pool: DevicePool, vision: object):
        self.device_pool = device_pool
        self.vision = vision

    def run_file(self, yaml_path: str) -> list[StepResult]:
        """Parse a YAML file and execute the test case."""
        case = YAMLParser.parse(yaml_path)
        return self._run_case(case)

    def run_dir(self, cases_dir: str) -> dict[str, list[StepResult]]:
        """Execute all test cases in a directory."""
        cases = YAMLParser.load_cases(cases_dir)
        results: dict[str, list[StepResult]] = {}
        for case in cases:
            results[case.name] = self._run_case(case)
        return results

    def _run_case(self, case: TestCaseDefinition) -> list[StepResult]:
        """Execute a single test case against its device."""
        driver = self.device_pool.get(case.device or "default")
        executor = StepExecutor(driver, self.vision)
        ctx = StepContext()
        results: list[StepResult] = []

        for step in case.steps:
            max_attempts = (step.retry or case.retry) + 1  # retry count + initial attempt
            last_result: Optional[StepResult] = None

            for attempt in range(max_attempts):
                last_result = executor.execute(step, ctx)
                results.append(last_result)
                if last_result.passed:
                    break
                time.sleep(1)

            ctx.step_index += 1

        return results
