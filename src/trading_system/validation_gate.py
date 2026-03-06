from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .config import AppConfig


def _parse_iso(ts: str) -> datetime | None:
    raw = str(ts or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except Exception:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _truthy_env(value: str | None) -> bool:
    raw = str(value or "").strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def _resolve_bypass(config: AppConfig) -> tuple[bool, str]:
    if _truthy_env(os.getenv("TRADING_SYSTEM_SKIP_VALIDATION_GATE")):
        return True, "env:TRADING_SYSTEM_SKIP_VALIDATION_GATE"
    cfg = config.validation_gate
    if bool(cfg.allow_bypass) and bool(cfg.bypass):
        return True, "config:validation_gate.bypass"
    return False, ""


def evaluate_validation_gate(config: AppConfig, base_dir: str | Path | None = None) -> Dict[str, Any]:
    cfg = config.validation_gate
    enforced = bool(cfg.enforce_for_live or cfg.enforce_for_auto_learning)
    bypassed, bypass_reason = _resolve_bypass(config)

    report_path = Path(cfg.report_path)
    if not report_path.is_absolute():
        root = Path(base_dir) if base_dir else Path.cwd()
        report_path = (root / report_path).resolve()

    result: Dict[str, Any] = {
        "enabled": enforced,
        "passed": True,
        "status": "disabled",
        "report_path": str(report_path),
        "report_exists": False,
        "report_timestamp": None,
        "report_age_days": None,
        "overall_passed": None,
        "next_step": None,
        "bypassed": False,
        "bypass_reason": "",
        "errors": [],
        "warnings": [],
    }

    if bypassed:
        result["enabled"] = False
        result["passed"] = True
        result["status"] = "bypassed"
        result["bypassed"] = True
        result["bypass_reason"] = bypass_reason
        result["warnings"].append(f"validation gate bypassed by {bypass_reason}")
        return result

    if not enforced:
        return result

    result["status"] = "checking"
    if not report_path.exists():
        result["passed"] = False
        result["status"] = "failed"
        result["errors"].append("validation report not found")
        return result

    result["report_exists"] = True
    try:
        raw = json.loads(report_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        result["passed"] = False
        result["status"] = "failed"
        result["errors"].append(f"validation report parse failed: {exc}")
        return result

    validation = raw.get("validation", {}) if isinstance(raw, dict) else {}
    overall_passed = bool(validation.get("overall_passed", False))
    result["overall_passed"] = overall_passed
    result["next_step"] = validation.get("next_step")

    if cfg.require_overall_passed and not overall_passed:
        result["errors"].append("validation.overall_passed is false")

    ts = _parse_iso(str(raw.get("timestamp", "")))
    if ts is None:
        result["warnings"].append("report timestamp missing or invalid")
    else:
        now_utc = datetime.now(timezone.utc)
        age_days = max(0.0, (now_utc - ts).total_seconds() / 86400.0)
        result["report_timestamp"] = ts.isoformat()
        result["report_age_days"] = age_days
        max_age = max(0, int(cfg.max_report_age_days or 0))
        if max_age > 0 and age_days > max_age:
            result["errors"].append(f"validation report is too old ({age_days:.1f}d > {max_age}d)")

    result["passed"] = len(result["errors"]) == 0
    result["status"] = "passed" if result["passed"] else "failed"
    return result
