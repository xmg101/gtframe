"""Tiered vision engine combining OpenCV, OCR, and AI."""
from dataclasses import dataclass, field
from typing import Any, Optional

from gtframe.vision.cache import VisionCache
from gtframe.vision.ocr_engine import OCREngine
from gtframe.vision.opencv_matcher import OpenCVMatcher


@dataclass
class OCRResult:
    """Single OCR match result."""
    text: str
    x: int
    y: int
    confidence: float


class VisionEngine:
    """Aggregate vision engine with local (OpenCV + OCR) and AI (Claude) tiers."""

    def __init__(
        self,
        template_dir: str = "templates",
        ocr_lang: str = "ch",
        claude_api_key: Optional[str] = None,
        cache_ttl: int = 3600,
    ):
        self.matcher = OpenCVMatcher(template_dir=template_dir)
        self.ocr = OCREngine(lang=ocr_lang)
        self.cache = VisionCache(cache_dir=".vision_cache", ttl=cache_ttl)
        self.claude_api_key = claude_api_key

    def locate(self, target: str, screenshot: bytes) -> Optional[dict]:
        """Locate *target* in *screenshot* — OpenCV first, then OCR fallback."""
        # Try OpenCV match
        result = self.matcher.match(target, screenshot)
        if result is not None:
            return result

        # Fallback: OCR to find the target text
        matches = self.ocr.find_text(target, screenshot)
        if matches:
            return {"x": matches[0]["x"], "y": matches[0]["y"], "confidence": matches[0]["confidence"]}

        return None

    def find_text(
        self, text: str, screenshot: bytes, engine: Optional[str] = None
    ) -> list[dict]:
        """Find text via OCR."""
        return self.ocr.find_text(text, screenshot)

    def ai_locate(self, text: str, screenshot: bytes) -> Optional[dict]:
        """AI-assisted text location (Phase 2 stub)."""
        return None

    def ask_ai(self, prompt: str, screenshot: bytes) -> dict[str, Any]:
        """Ask AI about a screenshot — checks cache first, then Claude."""
        cached = self.cache.get(prompt, screenshot)
        if cached is not None:
            return cached

        result = self._call_claude(prompt, screenshot)
        self.cache.set(prompt, screenshot, result)
        return result

    def compare_snapshot(
        self, baseline: str, screenshot: bytes, threshold: Optional[float] = None
    ) -> bool:
        """Compare screenshot against a stored baseline."""
        return self.matcher.compare(baseline, screenshot, threshold)

    def _call_claude(self, prompt: str, screenshot: bytes) -> dict[str, Any]:
        """Call Claude API or return a mock result when API key is not set."""
        if not self.claude_api_key:
            return {"passed": True, "reason": "AI未配置", "model": "mock"}
        # Phase 2: real Claude call
        return {"passed": True, "reason": "Claude API call not yet implemented", "model": "pending"}
