"""Tests for Config singleton."""
import tempfile
from pathlib import Path
from gtframe.config import Config
from gtframe.exceptions import ConfigError


# ---------------------------------------------------------------------------
# Reset singleton between tests
# ---------------------------------------------------------------------------

def _reset_config():
    Config._instance = None


def setup_function():
    _reset_config()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_config_get_returns_singleton():
    """Config.get() should always return the same instance."""
    cfg1 = Config.get()
    cfg2 = Config.get()
    assert cfg1 is cfg2


def test_config_default_values():
    """Default config values should be set."""
    cfg = Config.get()
    assert cfg.default_timeout == 30
    assert cfg.default_retry == 2
    assert cfg.is_idle_timeout == 5
    assert cfg.opencv_threshold == 0.85
    assert cfg.ocr_lang == "ch"
    assert cfg.video_fps == 10
    assert cfg.video_crash_window == 5


def test_config_default_paths():
    """Default path fields should be empty strings."""
    cfg = Config.get()
    assert cfg.cases_dir == ""
    assert cfg.report_dir == ""
    assert cfg.screenshot_dir == ""
    assert cfg.video_dir == ""
    assert cfg.log_dir == ""


def test_config_overwrite_from_yaml():
    """load() should overwrite defaults with values from a YAML file."""
    yaml_content = """
default_timeout: 60
default_retry: 3
ocr_lang: en
claude_model: claude-sonnet-4-20250514
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(yaml_content)
        tmp_path = f.name

    try:
        cfg = Config.get()
        report_dir_before = cfg.report_dir
        cfg.load(tmp_path)
        assert cfg.default_timeout == 60
        assert cfg.default_retry == 3
        assert cfg.ocr_lang == "en"
        assert cfg.claude_model == "claude-sonnet-4-20250514"
        # unset fields should keep their defaults
        assert cfg.report_dir == report_dir_before
    finally:
        import os
        os.unlink(tmp_path)


def test_config_load_nonexistent_file():
    """load() on a nonexistent path should raise ConfigError."""
    cfg = Config.get()
    try:
        cfg.load("/nonexistent/config.yaml")
        assert False, "Expected ConfigError"
    except ConfigError:
        pass


def test_config_invalid_yaml():
    """load() on malformed YAML should raise ConfigError."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(": invalid yaml [[[")
        tmp_path = f.name

    try:
        cfg = Config.get()
        try:
            cfg.load(tmp_path)
            assert False, "Expected ConfigError"
        except ConfigError:
            pass
    finally:
        import os
        os.unlink(tmp_path)
