"""Command-line interface for gtframe."""
import argparse
import sys
from pathlib import Path

from gtframe.config import Config
from gtframe.device.device_pool import DevicePool
from gtframe.exceptions import GTFrameError
from gtframe.orchestrator.test_runner import TestRunner
from gtframe.report.reporter import Reporter
from gtframe.vision.engine import VisionEngine


def main():
    import sys as _sys

    if len(_sys.argv) >= 2 and _sys.argv[1] == "web":
        _run_web()
        return

    _run_cli()


def _run_web():
    import sys as _sys
    # Remove the "web" subcommand from argv so argparse doesn't see it
    _sys.argv = [_sys.argv[0]] + _sys.argv[2:]

    import uvicorn
    from gtframe.web.app import app

    parser = argparse.ArgumentParser(prog="gtframe web")
    parser.add_argument("--port", type=int, default=8765, help="Web UI port (default: 8765)")
    parser.add_argument("--config", help="Path to config YAML file")
    args = parser.parse_args()

    if args.config:
        try:
            Config.get().load(args.config)
        except GTFrameError as e:
            print(f"Config error: {e}", file=sys.stderr)
            sys.exit(1)

    print(f"[gtframe] Web UI starting at http://localhost:{args.port}")
    print("   Press Ctrl+C to stop")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


def _run_cli():
    parser = argparse.ArgumentParser(
        prog="gtframe",
        description="Automated game testing framework",
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="Path to a YAML test case file or a directory of test cases",
    )
    parser.add_argument("--device", help="Device name to use for testing")
    parser.add_argument("--config", help="Path to config YAML file")
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available devices and exit",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize project directory structure",
    )

    args = parser.parse_args()

    # Load config
    if args.config:
        try:
            Config.get().load(args.config)
        except GTFrameError as e:
            print(f"Config error: {e}", file=sys.stderr)
            sys.exit(1)

    # --init
    if args.init:
        init_directories()
        print("Project structure initialized.")
        return

    # --list-devices
    if args.list_devices:
        pool = DevicePool()
        devices = pool.auto_discover()
        if devices:
            print("Available devices:")
            for name, dtype in devices.items():
                print(f"  {name} ({dtype})")
        else:
            print("No devices found.")
        return

    # Run test
    if not args.target:
        parser.print_help()
        sys.exit(1)

    target_path = Path(args.target)
    if not target_path.exists():
        print(f"Error: target not found: {args.target}", file=sys.stderr)
        sys.exit(1)

    # Setup
    device_pool = DevicePool()

    # Auto-discover and register
    devices = device_pool.auto_discover()
    if not devices:
        print("Error: no devices available", file=sys.stderr)
        sys.exit(1)

    # Use first available device if --device not specified
    device_name = args.device or next(iter(devices))

    try:
        vision = VisionEngine()
        runner = TestRunner(device_pool, vision)
        reporter = Reporter()

        if target_path.is_file():
            results = runner.run_file(str(target_path))
        else:
            results_map = runner.run_dir(str(target_path))
            # Flatten for report
            all_results = []
            for case_results in results_map.values():
                all_results.extend(case_results)
            results = all_results

        passed = sum(1 for r in results if r.passed)
        total = len(results)
        print(f"Results: {passed}/{total} passed")

        if passed < total:
            sys.exit(1)

    except GTFrameError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def init_directories():
    """Create the initial project directory structure."""
    dirs = [
        "cases/_shared",
        "cases/_archived",
        "templates",
        "baselines",
        "reports",
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()
