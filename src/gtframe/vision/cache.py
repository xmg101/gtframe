"""Simple file-based cache for AI vision results."""
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Optional


class VisionCache:
    """Disk-backed cache for AI vision API responses to avoid redundant calls."""

    def __init__(self, cache_dir: str = ".vision_cache", ttl: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl
        self._memory: dict[str, dict] = {}

    def _make_key(self, prompt: str, screenshot: bytes) -> str:
        h = hashlib.md5()
        h.update(screenshot[:4096])
        h.update(prompt.encode())
        return h.hexdigest()[:24]

    def get(self, prompt: str, screenshot: bytes) -> Optional[Any]:
        """Look up a cached result. Returns None if missing or expired."""
        key = self._make_key(prompt, screenshot)
        now = time.time()

        # Check memory cache
        entry = self._memory.get(key)
        if entry and entry.get("expires", 0) > now:
            return entry["data"]

        # Check file cache
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    entry = json.load(f)
                if entry.get("expires", 0) > now:
                    self._memory[key] = entry
                    return entry["data"]
                else:
                    cache_file.unlink(missing_ok=True)
            except (json.JSONDecodeError, OSError):
                pass

        return None

    def set(self, prompt: str, screenshot: bytes, data: Any) -> None:
        """Store a result in the cache."""
        key = self._make_key(prompt, screenshot)
        expires = time.time() + self.ttl
        entry = {"expires": expires, "data": data}

        # Memory cache
        self._memory[key] = entry

        # File cache
        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False)
        except OSError:
            pass

    def clear_expired(self) -> None:
        """Remove expired entries from memory and disk."""
        now = time.time()
        self._memory = {k: v for k, v in self._memory.items() if v.get("expires", 0) > now}

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    entry = json.load(f)
                if entry.get("expires", 0) <= now:
                    cache_file.unlink(missing_ok=True)
            except (json.JSONDecodeError, OSError):
                cache_file.unlink(missing_ok=True)
