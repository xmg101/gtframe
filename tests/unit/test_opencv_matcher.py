"""Tests for OpenCV template matcher and pixel comparator."""
import os
import tempfile

import numpy as np
import pytest

from gtframe.vision.opencv_matcher import OpenCVMatcher


@pytest.fixture
def template_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def matcher(template_dir):
    return OpenCVMatcher(template_dir=template_dir, threshold=0.8)


def _create_test_image(width=100, height=80, color=(200, 100, 50)):
    """Create a simple solid-color test image as PNG bytes."""
    import cv2
    img = np.full((height, width, 3), color, dtype=np.uint8)
    success, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def _save_template(template_dir, name, data):
    path = os.path.join(template_dir, name)
    with open(path, "wb") as f:
        f.write(data)
    return path


def test_match_template_found(matcher, template_dir):
    """match() should find coordinates when template is embedded in screenshot."""
    import cv2
    # Screenshot: a 100x100 image with a 40x40 unique pattern placed at (30, 30)
    screenshot = np.zeros((100, 100, 3), dtype=np.uint8)
    # Fill with gradient rows to give texture
    for y in range(100):
        screenshot[y, :] = (y * 2 % 256, y * 3 % 256, y * 5 % 256)

    # Create a distinctive pattern and place it at (30, 30)
    tile = np.zeros((40, 40, 3), dtype=np.uint8)
    tile[:20, :20] = (200, 200, 200)
    tile[20:, 20:] = (200, 200, 200)
    tile[:20, 20:] = (30, 30, 30)
    tile[20:, :20] = (30, 30, 30)
    screenshot[30:70, 30:70] = tile

    # Save template = the distinctive pattern
    success, buf = cv2.imencode(".png", tile)
    _save_template(template_dir, "tile.png", buf.tobytes())

    success, buf = cv2.imencode(".png", screenshot)
    screenshot_bytes = buf.tobytes()

    result = matcher.match("tile", screenshot_bytes)
    assert result is not None, f"Expected to find template, got None"
    # center of 40x40 tile at (30,30) → x=50, y=50
    assert 40 <= result["x"] <= 60, f"x={result['x']} out of range"
    assert 40 <= result["y"] <= 60, f"y={result['y']} out of range"


def test_match_template_not_found(matcher, template_dir):
    """match() should return None when template is not in screenshot."""
    import cv2
    # Screenshot: gradient image with no repeating patterns
    screenshot = np.zeros((100, 100, 3), dtype=np.uint8)
    for y in range(100):
        for x in range(100):
            screenshot[y, x] = ((x * y) % 200, (x + y) % 200, (x * y * 7) % 256)

    # Template: a 20x20 pattern that does NOT appear in the screenshot
    template = np.zeros((20, 20, 3), dtype=np.uint8)
    template[:, :] = (255, 0, 0)

    success, buf = cv2.imencode(".png", template)
    _save_template(template_dir, "red_square.png", buf.tobytes())

    success, buf = cv2.imencode(".png", screenshot)
    screenshot_bytes = buf.tobytes()

    result = matcher.match("red_square", screenshot_bytes)
    assert result is None, f"Expected None, got {result}"


def test_compare_same_image(matcher):
    """compare() should return True for identical images."""
    data = _create_test_image()
    assert matcher.compare(data, data) is True


def test_compare_different_images(matcher):
    """compare() should return False for significantly different images."""
    img1 = _create_test_image(color=(200, 100, 50))
    img2 = _create_test_image(color=(50, 100, 200))
    assert matcher.compare(img1, img2) is False
