from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_path(path_value: str, root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = (root / path).resolve()
    return path


def _get_json(url: str, timeout: int = 4) -> dict[str, Any]:
    req = Request(url=url, method="GET")
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def _extract_json_block(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("empty output")
    try:
        return json.loads(raw)
    except Exception:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < start:
            raise
        return json.loads(raw[start : end + 1])


def _decode_output(raw: bytes | None) -> str:
    data = raw or b""
    for enc in ("utf-8", "cp949", "mbcs"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")


def _run_live_readiness(config_path: Path, root: Path) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str((root / "src").resolve())
    cmd = [
        sys.executable,
        "-m",
        "trading_system.main",
        "--config",
        str(config_path),
        "--live-readiness",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(root),
        env=env,
        capture_output=True,
    )
    stdout_text = _decode_output(proc.stdout)
    stderr_text = _decode_output(proc.stderr)
    if proc.returncode != 0:
        detail = (stderr_text or stdout_text or "").strip()
        raise RuntimeError(detail or f"live-readiness failed (code={proc.returncode})")
    return _extract_json_block(stdout_text)


def run_healthcheck(args: argparse.Namespace) -> int:
    root = _root_dir()
    config_path = _resolve_path(str(args.config), root)
    result: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "dashboard": {
            "host": str(args.listen_host),
            "port": int(args.listen_port),
            "reachable": False,
            "running": False,
            "mode": "",
            "cycle_count": 0,
        },
        "readiness": None,
        "checks": [],
        "overall_passed": False,
    }

    def add_check(code: str, passed: bool, detail: str) -> None:
        result["checks"].append(
            {
                "code": str(code),
                "passed": bool(passed),
                "detail": str(detail),
            }
        )

    status_url = f"http://{args.listen_host}:{int(args.listen_port)}/api/status"
    try:
        status = _get_json(status_url, timeout=4)
        result["dashboard"]["reachable"] = True
        result["dashboard"]["running"] = bool(status.get("running", False))
        result["dashboard"]["mode"] = str(status.get("mode", ""))
        result["dashboard"]["cycle_count"] = int(status.get("cycle_count", 0) or 0)
        add_check("dashboard_status_api", True, "status api reachable")
    except Exception as exc:
        add_check("dashboard_status_api", False, str(exc))

    if bool(args.include_readiness):
        try:
            payload = _run_live_readiness(config_path=config_path, root=root)
            result["readiness"] = payload
            add_check(
                "live_readiness_cli",
                bool(payload.get("overall_passed", False)),
                "live readiness executed",
            )
        except Exception as exc:
            add_check("live_readiness_cli", False, str(exc))

    all_passed = all(bool(item.get("passed", False)) for item in result["checks"])
    result["overall_passed"] = all_passed
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all_passed else 1


def _copy_if_exists(source: Path, destination: Path) -> bool:
    if not source.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    else:
        shutil.copy2(source, destination)
    return True


def run_backup(args: argparse.Namespace) -> int:
    root = _root_dir()
    output_dir = _resolve_path(str(args.output_dir), root)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    staging_dir = output_dir / f"backup_stage_{ts}"
    bundle_dir = staging_dir / "trading_system_backup"
    zip_path = output_dir / f"trading_system_backup_{ts}.zip"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "root": str(root),
        "entries": [],
    }

    paths: list[tuple[Path, Path]] = [
        (root / "configs", bundle_dir / "configs"),
        (root / "docs", bundle_dir / "docs"),
        (root / "data", bundle_dir / "data"),
        (root / "README.md", bundle_dir / "README.md"),
    ]
    if bool(args.include_logs):
        paths.append((root / "logs", bundle_dir / "logs"))

    for source, destination in paths:
        copied = _copy_if_exists(source, destination)
        manifest["entries"].append(
            {
                "source": str(source),
                "destination": str(destination),
                "copied": bool(copied),
            }
        )

    (bundle_dir / "backup_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if zip_path.exists():
        zip_path.unlink()
    archive_base = str(zip_path.with_suffix(""))
    shutil.make_archive(archive_base, "zip", root_dir=str(bundle_dir))
    shutil.rmtree(staging_dir, ignore_errors=True)

    print(f"백업 완료: {zip_path}")
    return 0


def run_watchdog(args: argparse.Namespace) -> int:
    root = _root_dir()
    config_path = _resolve_path(str(args.config), root)
    check_interval = max(3, int(args.check_interval_seconds))
    restart_cooldown = max(5, int(args.restart_cooldown_seconds))
    status_url = f"http://{args.listen_host}:{int(args.listen_port)}/api/status"
    logs_dir = (root / "logs").resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "watchdog.log"
    start_system_bat = (root / "start-system.bat").resolve()

    def write_log(message: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {message}"
        print(line)
        with log_path.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")

    def dashboard_alive() -> bool:
        try:
            _ = _get_json(status_url, timeout=4)
            return True
        except Exception:
            return False

    def start_dashboard_web() -> None:
        cmd = [
            str(start_system_bat),
            "web",
            str(config_path),
            str(args.listen_host),
            str(args.listen_port),
        ]
        subprocess.Popen(cmd, cwd=str(root))

    write_log(
        f"watchdog started (host={args.listen_host} port={args.listen_port} "
        f"interval={check_interval}s cooldown={restart_cooldown}s)"
    )

    last_restart_at = 0.0
    try:
        while True:
            if dashboard_alive():
                time.sleep(check_interval)
                continue

            elapsed = time.time() - last_restart_at
            if elapsed < restart_cooldown:
                write_log(
                    f"dashboard unreachable but restart cooldown active "
                    f"({elapsed:.1f}s/{restart_cooldown}s)"
                )
                time.sleep(check_interval)
                continue

            write_log("dashboard unreachable -> restarting web dashboard")
            try:
                start_dashboard_web()
                last_restart_at = time.time()
            except Exception as exc:
                write_log(f"restart failed: {exc}")

            time.sleep(check_interval)
    except KeyboardInterrupt:
        write_log("watchdog stopped by user")
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Trading system operations tool")
    sub = parser.add_subparsers(dest="command", required=True)

    p_health = sub.add_parser("healthcheck", help="Run dashboard health checks")
    p_health.add_argument("--config", default="configs/default.json")
    p_health.add_argument("--listen-host", default="127.0.0.1")
    p_health.add_argument("--listen-port", type=int, default=8000)
    p_health.add_argument("--include-readiness", action="store_true")
    p_health.set_defaults(func=run_healthcheck)

    p_backup = sub.add_parser("backup", help="Create backup zip")
    p_backup.add_argument("--output-dir", default="backups")
    p_backup.add_argument("--include-logs", dest="include_logs", action="store_true", default=True)
    p_backup.add_argument("--no-include-logs", dest="include_logs", action="store_false")
    p_backup.set_defaults(func=run_backup)

    p_watchdog = sub.add_parser("watchdog", help="Run web dashboard watchdog loop")
    p_watchdog.add_argument("--config", default="configs/default.json")
    p_watchdog.add_argument("--listen-host", default="127.0.0.1")
    p_watchdog.add_argument("--listen-port", type=int, default=8000)
    p_watchdog.add_argument("--check-interval-seconds", type=int, default=15)
    p_watchdog.add_argument("--restart-cooldown-seconds", type=int, default=20)
    p_watchdog.set_defaults(func=run_watchdog)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    fn = getattr(args, "func", None)
    if fn is None:
        parser.print_help()
        return 2
    return int(fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
