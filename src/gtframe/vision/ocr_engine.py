"""OCR engine using PaddleOCR with lazy initialization."""
from typing import Optional


class OCREngine:
    """Text recognition engine using PaddleOCR."""

    def __init__(self, lang: str = "ch"):
        self.lang = lang
        self._ocr = None
        self._available = True

    def _lazy_init(self):
        if self._ocr is None and self._available:
            try:
                from paddleocr import PaddleOCR
                self._ocr = PaddleOCR(use_angle_cls=True, lang=self.lang, show_log=False)
            except ImportError:
                self._available = False

    def find_text(self, text: str, screenshot: bytes, engine_name: Optional[str] = None) -> list[dict]:
        """Search for *text* in *screenshot* via OCR.

        Returns list of matches: [{text, x, y, confidence}, ...]
        Empty list if not found or OCR unavailable.
        """
        self._lazy_init()
        if self._ocr is None:
            return []
        import cv2
        import numpy as np

        buf = np.frombuffer(screenshot, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)

        results = self._ocr.ocr(img, cls=True)
        matches = []
        for line in results or []:
            for word in line or []:
                bbox, (recognized_text, confidence) = word
                if text in recognized_text:
                    x = int(bbox[0][0] + bbox[2][0]) // 2
                    y = int(bbox[0][1] + bbox[2][1]) // 2
                    matches.append({
                        "text": recognized_text,
                        "x": x,
                        "y": y,
                        "confidence": float(confidence),
                    })
        return matches

    def recognize_all(self, screenshot: bytes) -> list[dict]:
        """Recognize all text in the screenshot."""
        self._lazy_init()
        if self._ocr is None:
            return []
        import cv2
        import numpy as np

        buf = np.frombuffer(screenshot, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)

        results = self._ocr.ocr(img, cls=True)
        all_text = []
        for line in results or []:
            for word in line or []:
                bbox, (text, confidence) = word
                all_text.append({
                    "text": text,
                    "x": int((bbox[0][0] + bbox[2][0]) / 2),
                    "y": int((bbox[0][1] + bbox[2][1]) / 2),
                    "confidence": float(confidence),
                })
        return all_text
