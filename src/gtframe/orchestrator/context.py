"""Step execution context for passing data between steps."""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class StepContext:
    """Context maintained throughout a test case execution."""
    step_index: int = 0
    screenshots: list[dict[str, Any]] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    values: dict[str, Any] = field(default_factory=dict)

    def save(self, key: str, value: Any) -> None:
        """Save a value to the context."""
        self.values[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the context."""
        return self.values.get(key, default)
