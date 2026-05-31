"""Tests for YAML test case parser."""
import os
import tempfile

import pytest

from gtframe.orchestrator.yaml_parser import YAMLParser, TestCaseDefinition, StepDefinition
from gtframe.exceptions import YAMLError

SAMPLE_YAML = """
name: test_main_menu
game: my_casual_game
device: android_01
timeout: 60
retry: 3
steps:
  - action: wait_for_screen
    target: main_menu
    timeout: 15

  - action: click
    target: start_button
    description: Click the start button

  - action: assert_ocr
    text: 开始游戏
    engine: ocr
    level: error

  - action: assert_ai
    prompt: 当前画面是否为游戏主界面？
    screenshot: true
    ai_fallback: true
"""


# ---------------------------------------------------------------------------
# parse()
# ---------------------------------------------------------------------------


def test_parse_valid_yaml():
    """parse() should return TestCaseDefinition with correct fields."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(SAMPLE_YAML)
        path = f.name

    try:
        case = YAMLParser.parse(path)
        assert isinstance(case, TestCaseDefinition)
        assert case.name == "test_main_menu"
        assert case.game == "my_casual_game"
        assert case.device == "android_01"
        assert case.timeout == 60
        assert case.retry == 3
        assert len(case.steps) == 4

        # Check first step
        assert case.steps[0].action == "wait_for_screen"
        assert case.steps[0].target == "main_menu"
        assert case.steps[0].timeout == 15

        # Check second step
        assert case.steps[1].action == "click"
        assert case.steps[1].target == "start_button"
        assert case.steps[1].description == "Click the start button"

        # Check third step (OCR assertion)
        assert case.steps[2].action == "assert_ocr"
        assert case.steps[2].text == "开始游戏"
        assert case.steps[2].engine == "ocr"
        assert case.steps[2].level == "error"

        # Check fourth step (AI assertion)
        assert case.steps[3].action == "assert_ai"
        assert case.steps[3].prompt == "当前画面是否为游戏主界面？"
        assert case.steps[3].screenshot is True
        assert case.steps[3].ai_fallback is True
    finally:
        os.unlink(path)


def test_parse_nonexistent_file():
    """parse() on nonexistent path should raise YAMLError."""
    with pytest.raises(YAMLError, match="not found"):
        YAMLParser.parse("/nonexistent/test_case.yaml")


def test_parse_invalid_yaml():
    """parse() on malformed YAML should raise YAMLError."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(": bad yaml ::: [[]]")
        path = f.name

    try:
        with pytest.raises(YAMLError, match="Invalid YAML"):
            YAMLParser.parse(path)
    finally:
        os.unlink(path)


def test_parse_missing_required_field():
    """parse() on YAML without 'name' should raise YAMLError."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write("steps: []\n")
        path = f.name

    try:
        with pytest.raises(YAMLError, match="name"):
            YAMLParser.parse(path)
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# load_cases()
# ---------------------------------------------------------------------------


def test_load_cases_from_dir():
    """load_cases() should find all .yaml files (excluding _ prefix and _archived)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create valid case files with unique names
        for i, fname in enumerate(["test_a.yaml", "test_b.yaml", "test_c.yaml"]):
            content = SAMPLE_YAML.replace("test_main_menu", f"test_{chr(ord('a') + i)}")
            with open(os.path.join(tmpdir, fname), "w", encoding="utf-8") as f:
                f.write(content)

        # Create files that should be skipped
        with open(os.path.join(tmpdir, "_hidden.yaml"), "w", encoding="utf-8") as f:
            f.write(SAMPLE_YAML)

        # Create _archived subdir with cases
        archived = os.path.join(tmpdir, "_archived")
        os.makedirs(archived)
        with open(os.path.join(archived, "old_case.yaml"), "w", encoding="utf-8") as f:
            f.write(SAMPLE_YAML)

        cases = YAMLParser.load_cases(tmpdir)
        names = [c.name for c in cases]
        assert sorted(names) == ["test_a", "test_b", "test_c"]


def test_load_cases_nonexistent_dir():
    """load_cases() on nonexistent dir should return empty list."""
    cases = YAMLParser.load_cases("/nonexistent/cases/")
    assert cases == []
