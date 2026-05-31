"""Tests for VisionCache."""
import json
import os
import tempfile
import time

import pytest

from gtframe.vision.cache import VisionCache


@pytest.fixture
def cache_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def _make_screenshot(size=100):
    return b"A" * size


def test_set_and_get(cache_dir):
    """set() then get() should return the same data."""
    cache = VisionCache(cache_dir=cache_dir, ttl=3600)
    cache.set("Is this the main menu?", _make_screenshot(), {"passed": True})
    result = cache.get("Is this the main menu?", _make_screenshot())
    assert result == {"passed": True}


def test_get_miss(cache_dir):
    """get() should return None for a prompt/screenshot combo never set."""
    cache = VisionCache(cache_dir=cache_dir, ttl=3600)
    result = cache.get("Some other question", _make_screenshot())
    assert result is None


def test_different_screenshot_different_key(cache_dir):
    """Different screenshots for the same prompt should produce different cache keys."""
    cache = VisionCache(cache_dir=cache_dir, ttl=3600)
    cache.set("prompt", _make_screenshot(100), {"data": "first"})
    result = cache.get("prompt", _make_screenshot(200))
    assert result is None, "Different screenshot should miss cache"


def test_expired_entry(cache_dir):
    """get() should return None for expired cache entries."""
    cache = VisionCache(cache_dir=cache_dir, ttl=1)
    cache.set("prompt", _make_screenshot(), {"data": "value"})
    time.sleep(1.1)
    result = cache.get("prompt", _make_screenshot())
    assert result is None
