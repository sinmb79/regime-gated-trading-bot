from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any, Dict, List


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_bool(value: Any) -> bool:
    return bool(value)


def _extract_section_metrics(section: Dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(section, dict):
        return {}, {}
    metrics = section.get("metrics")
    if not isinstance(metrics, dict):
        metrics = section.get("overall_metrics")
    if not isinstance(metrics, dict):
        metrics = {}
    gate = section.get("gate")
    if not isinstance(gate, dict):
        gate = section.get("overall_gate")
    if not isinstance(gate, dict):
        gate = {}
    return metrics, gate


def build_validation_snapshot(report: Dict[str, Any], source_path: str = "") -> Dict[str, Any]:
    validation = report.get("validation", {}) if isinstance(report, dict) else {}
    backtest = validation.get("backtest") if isinstance(validation, dict) else None
    walk_forward = validation.get("walk_forward") if isinstance(validation, dict) else None
    back_metrics, back_gate = _extract_section_metrics(backtest if isinstance(backtest, dict) else None)
    walk_metrics, walk_gate = _extract_section_metrics(walk_forward if isinstance(walk_forward, dict) else None)

    preferred = walk_metrics if walk_metrics else back_metrics
    snapshot = {
        "timestamp": str(report.get("timestamp", "")),
        "overall_passed": _safe_bool(validation.get("overall_passed", False)),
        "next_step": str(validation.get("next_step", "")),
        "source_path": str(source_path or ""),
        "has_backtest": bool(backtest),
        "has_walk_forward": bool(walk_forward),
        "backtest_passed": _safe_bool(back_gate.get("passed", False)) if back_gate else None,
        "walk_forward_passed": _safe_bool(walk_gate.get("passed", False)) if walk_gate else None,
        "pnl_total_usdt": _safe_float(preferred.get("pnl_total_usdt", 0.0)),
        "win_rate": _safe_float(preferred.get("win_rate", 0.0)),
        "max_drawdown_pct": _safe_float(preferred.get("max_drawdown_pct", 0.0)),
        "filled_trades": int(_safe_float(preferred.get("filled_trades", 0))),
        "reject_rate": _safe_float(preferred.get("reject_rate", 0.0)),
        "backtest_pnl_total_usdt": _safe_float(back_metrics.get("pnl_total_usdt", 0.0)),
        "backtest_win_rate": _safe_float(back_metrics.get("win_rate", 0.0)),
        "backtest_max_drawdown_pct": _safe_float(back_metrics.get("max_drawdown_pct", 0.0)),
        "walk_forward_pnl_total_usdt": _safe_float(walk_metrics.get("pnl_total_usdt", 0.0)),
        "walk_forward_win_rate": _safe_float(walk_metrics.get("win_rate", 0.0)),
        "walk_forward_max_drawdown_pct": _safe_float(walk_metrics.get("max_drawdown_pct", 0.0)),
    }
    return snapshot


def save_validation_snapshot(report: Dict[str, Any], history_path: str | Path, source_path: str = "") -> Dict[str, Any]:
    target = Path(history_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    snapshot = build_validation_snapshot(report, source_path=source_path)
    with target.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
    return snapshot


def load_validation_history(history_path: str | Path, limit: int = 30) -> List[Dict[str, Any]]:
    target = Path(history_path)
    if not target.exists():
        return []
    max_rows = max(1, int(limit))
    buf: deque[Dict[str, Any]] = deque(maxlen=max_rows)
    for line in target.read_text(encoding="utf-8-sig").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except Exception:
            continue
        if isinstance(row, dict):
            buf.append(row)
    return list(reversed(list(buf)))


def build_validation_history_payload(
    rows: List[Dict[str, Any]],
    limit: int,
    history_path: str,
) -> Dict[str, Any]:
    total = len(rows)
    passed = sum(1 for row in rows if bool(row.get("overall_passed", False)))
    pass_rate = (passed / total) if total > 0 else 0.0
    latest = rows[0] if rows else None
    avg_pnl = sum(_safe_float(r.get("pnl_total_usdt", 0.0)) for r in rows) / total if total > 0 else 0.0
    avg_win = sum(_safe_float(r.get("win_rate", 0.0)) for r in rows) / total if total > 0 else 0.0
    avg_dd = sum(_safe_float(r.get("max_drawdown_pct", 0.0)) for r in rows) / total if total > 0 else 0.0
    return {
        "limit": int(limit),
        "history_path": str(history_path),
        "total_runs": total,
        "passed_runs": passed,
        "pass_rate": pass_rate,
        "avg_pnl_total_usdt": avg_pnl,
        "avg_win_rate": avg_win,
        "avg_max_drawdown_pct": avg_dd,
        "latest": latest,
        "recent_runs": rows,
    }

