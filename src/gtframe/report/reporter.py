"""Test report generator with JSON and HTML output."""
import json
import shutil
import time
from pathlib import Path
from typing import Optional

from gtframe.orchestrator.context import StepContext
from gtframe.orchestrator.step_executor import StepResult
from gtframe.orchestrator.yaml_parser import TestCaseDefinition


class Reporter:
    """Generate structured test reports with screenshots, logs, and device info."""

    def __init__(self, report_dir: str = "reports"):
        self.report_dir = Path(report_dir)
        self.screenshots_dir = self.report_dir / "screenshots"
        self.videos_dir = self.report_dir / "videos"
        self.logs_dir = self.report_dir / "logs"
        for d in [self.report_dir, self.screenshots_dir, self.videos_dir, self.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        case: TestCaseDefinition,
        results: list[StepResult],
        ctx: StepContext,
        elapsed: float,
    ) -> str:
        """Generate a timestamped report directory and return its path."""
        timestamp = int(time.time())
        report_name = f"{case.name}_{timestamp}"
        report_path = self.report_dir / report_name
        report_path.mkdir(parents=True, exist_ok=True)

        # Save screenshots
        screenshot_paths = []
        for i, sr in enumerate(results):
            if sr.screenshot:
                fname = f"step_{i:02d}_{sr.step.action}.png"
                spath = report_path / fname
                with open(spath, "wb") as f:
                    f.write(sr.screenshot)
                screenshot_paths.append(str(spath))
            else:
                screenshot_paths.append(None)

        # Build step data
        total = len(results)
        passed_count = sum(1 for r in results if r.passed)

        steps_data = []
        for i, (sr, spath) in enumerate(zip(results, screenshot_paths)):
            steps_data.append({
                "index": i,
                "action": sr.step.action,
                "target": sr.step.target,
                "description": sr.step.description,
                "passed": sr.passed,
                "duration": round(sr.duration, 3),
                "error": sr.error,
                "screenshot": spath,
                "ai_response": sr.ai_response,
            })

        report_data = {
            "name": case.name,
            "game": case.game,
            "device": case.device,
            "elapsed": round(elapsed, 2),
            "total": total,
            "passed": passed_count,
            "failed": total - passed_count,
            "status": "PASS" if passed_count == total else "FAIL",
            "steps": steps_data,
        }

        # Write JSON
        json_path = report_path / "report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        # Write HTML
        html_path = report_path / "report.html"
        html = self._generate_html(report_data)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        return str(json_path)

    def _generate_html(self, data: dict) -> str:
        """Generate a self-contained HTML report."""
        status_color = "#4caf50" if data["status"] == "PASS" else "#f44336"
        steps_html = ""

        for s in data["steps"]:
            step_color = "#4caf50" if s["passed"] else "#f44336"
            screenshot_html = ""
            if s["screenshot"]:
                screenshot_html = f'<img src="{s["screenshot"]}" style="max-width:320px;border:1px solid #ccc;margin-top:8px" />'

            ai_html = ""
            if s["ai_response"]:
                ai_html = f'<pre style="background:#f5f5f5;padding:8px">{json.dumps(s["ai_response"], ensure_ascii=False, indent=2)}</pre>'

            error_html = ""
            if s["error"]:
                error_html = f'<pre style="background:#fff3f3;padding:8px;color:#d32f2f">{s["error"]}</pre>'

            steps_html += f"""
            <div style="margin:12px 0;padding:12px;border-left:4px solid {step_color};background:#fafafa">
                <strong>#{s["index"]}</strong> {s["action"]}
                <span style="float:right;color:{step_color};font-weight:bold">{'PASS' if s["passed"] else 'FAIL'}</span>
                <br/><small>{s["target"] or ""} — {s["duration"]}s</small>
                <br/><small>{s["description"] or ""}</small>
                {error_html}
                {screenshot_html}
                {ai_html}
            </div>
            """

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>{data["name"]} — Test Report</title></head>
<body style="font-family:-apple-system,sans-serif;max-width:960px;margin:0 auto;padding:20px">
    <h1 style="color:{status_color}">{data["status"]} — {data["name"]}</h1>
    <p>Game: {data["game"]} | Device: {data["device"]} | Elapsed: {data["elapsed"]}s</p>
    <p>Passed: {data["passed"]}/{data["total"]}</p>
    <hr/>
    {steps_html}
</body>
</html>"""
        return html
