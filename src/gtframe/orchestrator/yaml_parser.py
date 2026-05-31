"""YAML test case parser."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from gtframe.exceptions import YAMLError


@dataclass
class StepDefinition:
    """Definition of a single test step."""
    action: str = ""
    target: Optional[str] = None
    text: Optional[str] = None
    description: Optional[str] = None
    timeout: Optional[int] = None
    retry: Optional[int] = None
    prompt: Optional[str] = None
    screenshot: bool = False
    engine: Optional[str] = None
    level: Optional[str] = None
    ai_fallback: bool = False
    script: Optional[str] = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class TestCaseDefinition:
    """Definition of a complete test case."""
    name: str
    game: Optional[str] = None
    device: Optional[str] = None
    timeout: int = 30
    retry: int = 2
    steps: list[StepDefinition] = field(default_factory=list)


class YAMLParser:
    """Parse YAML test case files into TestCaseDefinition objects."""

    _REQUIRED_FIELDS = {"name", "steps"}

    @classmethod
    def parse(cls, path: str) -> TestCaseDefinition:
        """Parse a single YAML file into a TestCaseDefinition."""
        p = Path(path)
        if not p.exists():
            raise YAMLError(f"Test case file not found: {path}")

        try:
            with open(p, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise YAMLError(f"Invalid YAML in '{path}': {e}") from e

        if not isinstance(raw, dict):
            raise YAMLError(f"YAML must be a mapping, got {type(raw).__name__}")

        missing = cls._REQUIRED_FIELDS - set(raw.keys())
        if missing:
            raise YAMLError(f"Missing required field(s) in '{path}': {', '.join(sorted(missing))}")

        steps = [StepDefinition(**s) if isinstance(s, dict) else StepDefinition() for s in raw.get("steps", [])]

        return TestCaseDefinition(
            name=raw["name"],
            game=raw.get("game"),
            device=raw.get("device"),
            timeout=raw.get("timeout", 30),
            retry=raw.get("retry", 2),
            steps=steps,
        )

    @classmethod
    def load_cases(cls, cases_dir: str) -> list[TestCaseDefinition]:
        """Load all valid YAML test cases from a directory.

        Skips:
        - Files starting with '_'
        - Contents of '_archived/' directory
        """
        p = Path(cases_dir)
        if not p.exists():
            return []

        cases: list[TestCaseDefinition] = []
        for yaml_path in sorted(p.rglob("*.yaml")):
            rel = yaml_path.relative_to(p)
            parts = rel.parts

            # Skip files inside _archived/
            if "_archived" in parts:
                continue

            # Skip files with _ prefix
            if parts[-1].startswith("_"):
                continue

            try:
                cases.append(cls.parse(str(yaml_path)))
            except YAMLError:
                continue  # silently skip invalid files

        return cases
