"""Global configuration (singleton pattern)."""
from pathlib import Path
from typing import Optional

import yaml

from gtframe.exceptions import ConfigError


class Config:
    """Singleton configuration loaded from YAML with defaults."""

    _instance: Optional["Config"] = None

    def __init__(self):
        self.cases_dir: str = ""
        self.report_dir: str = ""
        self.screenshot_dir: str = ""
        self.video_dir: str = ""
        self.log_dir: str = ""
        self.default_timeout: int = 30
        self.default_retry: int = 2
        self.is_idle_timeout: int = 5
        self.opencv_threshold: float = 0.85
        self.ocr_lang: str = "ch"
        self.claude_model: Optional[str] = None
        self.video_fps: int = 10
        self.video_crash_window: int = 5

    @classmethod
    def get(cls) -> "Config":
        """Return the global singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load(self, path: str) -> None:
        """Load configuration values from a YAML file, overriding defaults."""
        p = Path(path)
        if not p.exists():
            raise ConfigError(f"Config file not found: {path}")

        try:
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in config file: {e}") from e

        if data is None:
            return

        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
