"""OpenCV-based template matcher and pixel comparator."""
import functools
from pathlib import Path

import cv2
import numpy as np


class OpenCVMatcher:
    """Template matching and image comparison using OpenCV."""

    def __init__(self, template_dir: str = "templates", threshold: float = 0.85):
        self.template_dir = template_dir
        self.threshold = threshold
        self._template_cache: dict[str, np.ndarray] = {}
        self._scales = [1.0, 0.75, 0.5, 1.25, 1.5]

    def _load_image(self, data: bytes) -> np.ndarray:
        buf = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image data")
        return img

    def _load_template(self, name: str) -> np.ndarray:
        if name in self._template_cache:
            return self._template_cache[name]

        path = Path(self.template_dir) / name
        if not path.suffix:
            path = path.with_suffix(".png")

        if not path.exists():
            raise FileNotFoundError(f"Template not found: {path}")

        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Failed to load template: {path}")

        self._template_cache[name] = img
        return img

    def match(self, template_name: str, screenshot: bytes) -> dict | None:
        """Try to locate *template_name* inside *screenshot* via multi-scale matching.

        Returns {"x": center_x, "y": center_y, "confidence": score} or None.
        """
        try:
            template = self._load_template(template_name)
        except (FileNotFoundError, ValueError):
            return None

        gray = self._load_image(screenshot)
        if len(gray.shape) == 3:
            gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)

        t_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        # Skip templates with near-zero variance (TM_CCOEFF_NORMED is undefined)
        if np.std(t_gray) < 1.0:
            return None

        best_val = -1
        best_pt = None

        for scale in self._scales:
            w = int(t_gray.shape[1] * scale)
            h = int(t_gray.shape[0] * scale)
            if w < 4 or h < 4:
                continue
            resized = cv2.resize(t_gray, (w, h), interpolation=cv2.INTER_AREA)
            if gray.shape[0] < h or gray.shape[1] < w:
                continue

            result = cv2.matchTemplate(gray, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val > best_val:
                best_val = max_val
                best_pt = max_loc
                best_w, best_h = w, h

        if best_val >= self.threshold and best_pt is not None:
            cx = best_pt[0] + best_w // 2
            cy = best_pt[1] + best_h // 2
            return {"x": cx, "y": cy, "confidence": float(best_val)}

        return None

    def compare(self, baseline: bytes, current: bytes, threshold: float | None = None) -> bool:
        """Pixel-level comparison of two images."""
        img1 = self._load_image(baseline)
        img2 = self._load_image(current)

        if img1.shape != img2.shape:
            return False

        diff = cv2.absdiff(img1, img2)
        mean_diff = float(np.mean(diff))
        t = threshold if threshold is not None else self.threshold
        return mean_diff < (1.0 - t) * 255
