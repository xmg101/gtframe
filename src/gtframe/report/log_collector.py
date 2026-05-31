"""Device log collector for test reporting."""
import time
from pathlib import Path
from typing import Optional

from gtframe.device.base_driver import BaseDriver


class LogCollector:
    """Collect and save device logs for a test."""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def collect(self, driver: BaseDriver, test_name: str) -> Optional[str]:
        """Pull logs from driver and save to file. Returns file path or None."""
        try:
            lines = driver.pull_log()
        except Exception:
            return None

        if not lines:
            return None

        # Keep only last 500 lines
        lines = lines[-500:]
        timestamp = int(time.time())
        filename = f"{test_name}_{timestamp}.log"
        filepath = self.log_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return str(filepath)
