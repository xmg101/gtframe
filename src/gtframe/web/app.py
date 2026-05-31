# src/gtframe/web/app.py
import asyncio
import json
import re
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from gtframe.config import Config
from gtframe.device.device_pool import DevicePool
from gtframe.orchestrator.context import StepContext
from gtframe.orchestrator.test_runner import TestRunner
from gtframe.report.reporter import Reporter
from gtframe.vision.engine import VisionEngine

app = FastAPI(title="gtframe")

# ── static files & templates ────────────────────────────────────
HERE = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")

import jinja2
_templates = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(HERE / "templates")),
    autoescape=True,
)


def _render(name: str, **ctx) -> str:
    return _templates.get_template(name).render(**ctx)


# ── shared state ────────────────────────────────────────────────
_device_pool: Optional[DevicePool] = None
_vision: Optional[VisionEngine] = None
_reporter: Optional[Reporter] = None
_run_tasks: dict[str, asyncio.Task] = {}
_run_logs: dict[str, list[str]] = {}
_run_lock: asyncio.Lock = asyncio.Lock()


def _ensure_services():
    global _device_pool, _vision, _reporter
    if _device_pool is None:
        _device_pool = DevicePool()
    if _vision is None:
        _vision = VisionEngine()
    if _reporter is None:
        _reporter = Reporter()
    return _device_pool, _vision, _reporter


def _cases_dir() -> Path:
    return Path(Config.get().cases_dir or "cases")


def _reports_dir() -> Path:
    return Path(Config.get().report_dir or "reports")


# ── page routes ─────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    _, _, reporter = _ensure_services()
    stats = _gather_stats()
    return HTMLResponse(_render("dashboard.html", active="dashboard", stats=stats))


@app.get("/run", response_class=HTMLResponse)
async def run_page():
    pool, _, _ = _ensure_services()
    cases = _list_cases()
    return HTMLResponse(_render("run.html", active="run", cases=cases, devices=pool.list_devices()))


@app.get("/reports", response_class=HTMLResponse)
async def reports_page():
    _, _, _ = _ensure_services()
    reports = _list_reports()
    return HTMLResponse(_render("reports.html", active="reports", reports=reports))


@app.get("/reports/{report_id}", response_class=HTMLResponse)
async def report_detail(report_id: str):
    _, _, _ = _ensure_services()
    report_data = _load_report(report_id)
    if report_data is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return HTMLResponse(_render("report_detail.html", active="reports", report=report_data))


@app.get("/cases", response_class=HTMLResponse)
async def cases_page():
    cases = _list_cases()
    return HTMLResponse(_render("cases.html", active="cases", cases=cases))


@app.get("/devices", response_class=HTMLResponse)
async def devices_page():
    pool, _, _ = _ensure_services()
    return HTMLResponse(_render("devices.html", active="devices", devices=pool.list_devices()))


# ── API routes ─────────────────────────────────────────────────


@app.get("/api/stats")
async def api_stats():
    return _gather_stats()


@app.get("/api/devices")
async def api_devices():
    pool, _, _ = _ensure_services()
    return {"devices": pool.list_devices()}


@app.post("/api/devices/scan")
async def api_devices_scan():
    pool, _, _ = _ensure_services()
    found = pool.auto_discover()
    return {"devices": found}


@app.get("/api/devices/diagnose")
async def api_devices_diagnose():
    pool, _, _ = _ensure_services()
    diagnoses = pool.diagnose_discovery()
    # Check if install action is possible
    import shutil
    can_install = shutil.which("adb") is None
    return {"diagnoses": diagnoses, "can_install_adb": can_install}


@app.post("/api/devices/install-adb")
async def api_devices_install_adb():
    pool, _, _ = _ensure_services()
    try:
        result = await _install_adb()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cases")
async def api_cases():
    return {"cases": _list_cases()}


@app.get("/api/cases/{case_name}")
async def api_case_detail(case_name: str):
    cases_dir = _cases_dir()
    for yaml_path in sorted(cases_dir.rglob("*.yaml")):
        if yaml_path.stem == case_name:
            content = yaml_path.read_text(encoding="utf-8")
            return {"name": case_name, "content": content}
    raise HTTPException(status_code=404, detail="Case not found")


@app.delete("/api/cases/{case_name}")
async def api_case_delete(case_name: str):
    cases_dir = _cases_dir()
    for yaml_path in sorted(cases_dir.rglob("*.yaml")):
        if yaml_path.stem == case_name:
            yaml_path.unlink()
            return {"deleted": case_name}
    raise HTTPException(status_code=404, detail="Case not found")


@app.post("/api/cases")
async def api_case_save(data: dict):
    cases_dir = _cases_dir()
    name = data.get("name", "").strip()
    content = data.get("content", "").strip()
    if not name or not content:
        raise HTTPException(status_code=400, detail="name and content required")
    if not re.match(r"^[a-zA-Z0-9_\-]+$", name):
        raise HTTPException(status_code=400, detail="Invalid case name (use letters, digits, _, -)")
    # Resolve and verify within cases_dir
    path = (cases_dir / f"{name}.yaml").resolve()
    if not str(path).startswith(str(cases_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid case name")
    path.write_text(content, encoding="utf-8")
    return {"saved": name}


@app.post("/api/run")
async def api_run(data: dict):
    run_id = str(uuid.uuid4())[:8]
    _run_logs[run_id] = []
    task = asyncio.create_task(_execute_run(run_id, data))
    _run_tasks[run_id] = task
    return {"run_id": run_id}


@app.get("/api/run/{run_id}/log")
async def api_run_log(request: Request, run_id: str):
    async def event_generator():
        last_index = 0
        while True:
            if await request.is_disconnected():
                break
            logs = _run_logs.get(run_id, [])
            while last_index < len(logs):
                yield {"data": logs[last_index]}
                last_index += 1
            if run_id not in _run_tasks or _run_tasks[run_id].done():
                if last_index >= len(logs):
                    yield {"data": "[DONE]"}
                    break
            await asyncio.sleep(0.1)
    return EventSourceResponse(event_generator())


@app.get("/api/reports")
async def api_reports():
    return {"reports": _list_reports()}


@app.get("/api/reports/{report_id}")
async def api_report_detail(report_id: str):
    data = _load_report(report_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return data


@app.get("/api/reports/{report_id}/screenshot/{step_index}")
async def api_report_screenshot(report_id: str, step_index: int):
    report_dir = _reports_dir() / report_id
    if not report_dir.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    screenshots = sorted(report_dir.glob("step_*.png"))
    if step_index < 0 or step_index >= len(screenshots):
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(str(screenshots[step_index]), media_type="image/png")


# ── helpers ─────────────────────────────────────────────────────


def _list_cases() -> list[dict]:
    cases_dir = _cases_dir()
    cases = []
    for yaml_path in sorted(cases_dir.rglob("*.yaml")):
        if yaml_path.name.startswith("_") or "_archived" in yaml_path.parts:
            continue
        cases.append({
            "name": yaml_path.stem,
            "path": str(yaml_path),
            "steps": _count_steps(yaml_path),
        })
    return cases


def _count_steps(path: Path) -> int:
    try:
        from gtframe.orchestrator.yaml_parser import YAMLParser
        case = YAMLParser.parse(str(path))
        return len(case.steps)
    except Exception:
        return 0


def _gather_stats() -> dict:
    cases = _list_cases()
    reports_dir = _reports_dir()
    recent = []
    for rep_dir in sorted(reports_dir.iterdir()):
        json_path = rep_dir / "report.json"
        if json_path.exists():
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                data["id"] = rep_dir.name
                recent.append(data)
            except Exception:
                pass
    recent = recent[-10:]

    pool, _, _ = _ensure_services()
    devices = pool.list_devices()

    return {
        "total_cases": len(cases),
        "recent_runs": len(recent),
        "pass_rate": round((sum(1 for r in recent if r.get("status") == "PASS") / len(recent) * 100) if recent else 0),
        "online_devices": len(devices),
        "recent": recent,
    }


def _list_reports() -> list[dict]:
    reports_dir = _reports_dir()
    reports = []
    for rep_dir in sorted(reports_dir.iterdir(), reverse=True):
        json_path = rep_dir / "report.json"
        if json_path.exists():
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                data["id"] = rep_dir.name
                reports.append(data)
            except Exception:
                pass
    return reports


def _load_report(report_id: str) -> Optional[dict]:
    report_dir = _reports_dir() / report_id
    json_path = report_dir / "report.json"
    if not json_path.exists():
        return None
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        data["id"] = report_id
        return data
    except Exception:
        return None


async def _execute_run(run_id: str, data: dict):
    pool, vision, reporter = _ensure_services()
    case_names = data.get("cases", [])
    device_name = data.get("device", "")
    logs = _run_logs[run_id]

    logs.append(json.dumps({"type": "info", "msg": f"Starting run {run_id}"}))

    try:
        async with _run_lock:
            if device_name not in pool.list_devices():
                found = pool.auto_discover()
                if not found:
                    logs.append(json.dumps({"type": "fail", "msg": "No devices available"}))
                    return

            runner = TestRunner(pool, vision)
            all_results = []
            start_time = __import__("time").time()

            for case_name in case_names:
                logs.append(json.dumps({"type": "info", "msg": f"Running: {case_name}"}))
                case_path = _find_case_yaml(case_name)
                if not case_path:
                    logs.append(json.dumps({"type": "fail", "msg": f"Case not found: {case_name}"}))
                    continue

                # Run in thread pool to avoid blocking the event loop
                results = await asyncio.to_thread(runner.run_file, str(case_path))
                passed = sum(1 for r in results if r.passed)

                for r in results:
                    logs.append(json.dumps({
                        "type": "pass" if r.passed else "fail",
                        "step": r.step.action,
                        "target": r.step.target,
                        "duration": round(r.duration, 2),
                        "error": r.error,
                    }))
                logs.append(json.dumps({"type": "summary", "passed": passed, "total": len(results)}))
                all_results.extend(results)

            passed_total = sum(1 for r in all_results if r.passed)
            logs.append(json.dumps({
                "type": "done",
                "passed": passed_total,
                "total": len(all_results),
            }))
    except Exception as e:
        logs.append(json.dumps({"type": "fail", "msg": str(e)}))


def _find_case_yaml(name: str) -> Optional[Path]:
    cases_dir = _cases_dir()
    for yaml_path in cases_dir.rglob("*.yaml"):
        if yaml_path.stem == name and not yaml_path.name.startswith("_"):
            return yaml_path
    return None


async def _install_adb() -> dict:
    """Download and install ADB on Windows."""
    import os
    import shutil
    import subprocess
    import tempfile
    import zipfile

    import httpx

    # Windows platform-tools download URL
    url = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
    install_dir = os.path.expanduser("~/.gtframe/platform-tools")

    # Create temp dir for download
    tmp = tempfile.mktemp(suffix=".zip")

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(tmp, "wb") as f:
                f.write(response.content)

        # Extract
        os.makedirs(install_dir, exist_ok=True)
        with zipfile.ZipFile(tmp, "r") as zf:
            zf.extractall(install_dir)

        # Find adb.exe
        adb_path = None
        for root, _dirs, files in os.walk(install_dir):
            if "adb.exe" in files:
                adb_path = os.path.join(root, "adb.exe")
                break

        if not adb_path:
            return {"success": False, "message": "下载完成但未找到 adb.exe"}

        # Add to PATH for this session + future
        adb_dir = os.path.dirname(adb_path)
        os.environ["PATH"] = adb_dir + os.pathsep + os.environ.get("PATH", "")

        # Also add to user PATH permanently via registry
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                "Environment",
                0,
                winreg.KEY_SET_VALUE | winreg.KEY_READ,
            )
            current_path = winreg.QueryValueEx(key, "PATH")[0] or ""
            if adb_dir not in current_path:
                new_path = adb_dir + ";" + current_path
                winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
                winreg.CloseKey(key)
                # Notify system
                subprocess.run(
                    "setx PATH \"" + new_path + "\"",
                    shell=True, capture_output=True, timeout=10,
                )
        except Exception:
            pass  # PATH update is a best-effort

        return {
            "success": True,
            "message": f"ADB 已安装到 {adb_path}",
            "adb_path": adb_path,
        }
    except Exception as e:
        return {"success": False, "message": f"安装失败: {e}"}
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
