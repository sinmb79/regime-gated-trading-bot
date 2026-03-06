from __future__ import annotations

import os
from typing import Any, Dict

from .config import AppConfig


def _has_text(value: str | None) -> bool:
    text = str(value or "").strip()
    return bool(text) and text != "[HIDDEN]"


def _extract_env_key(raw: str | None) -> str:
    text = str(raw or "").strip()
    if text.startswith("${") and text.endswith("}") and len(text) > 3:
        return text[2:-1].strip()
    if text.startswith("$") and len(text) > 1:
        return text[1:].strip()
    return ""


def _has_secret(raw: str | None, env_name: str | None) -> bool:
    if _has_text(raw):
        key = _extract_env_key(raw)
        if key:
            return _has_text(os.getenv(key))
        return True
    if _has_text(env_name):
        return _has_text(os.getenv(str(env_name)))
    return False


def evaluate_live_preflight(config: AppConfig) -> Dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if str(config.mode).lower() != "live":
        return {
            "checked": True,
            "mode": config.mode,
            "passed": True,
            "errors": [],
            "warnings": ["preflight skipped: mode is not live"],
        }

    if not config.live_guard.enabled:
        return {
            "checked": True,
            "mode": config.mode,
            "passed": True,
            "errors": [],
            "warnings": ["live_guard is disabled"],
        }

    exchange = config.exchange
    risk = config.risk_limits
    live_guard = config.live_guard
    notifications = config.notifications

    if str(exchange.type).lower() in {"paper", "mock"}:
        errors.append("exchange.type must be real exchange in live mode")
    if not exchange.allow_live:
        errors.append("exchange.allow_live must be true in live mode")
    if not _has_secret(exchange.api_key, exchange.api_key_env):
        errors.append("exchange api key is missing")
    if not _has_secret(exchange.api_secret, exchange.api_secret_env):
        errors.append("exchange api secret is missing")

    if risk.daily_max_loss_pct > live_guard.max_daily_loss_hard_limit_pct:
        errors.append(
            f"daily_max_loss_pct too high ({risk.daily_max_loss_pct:.3f} > {live_guard.max_daily_loss_hard_limit_pct:.3f})"
        )
    if risk.max_total_exposure > live_guard.max_total_exposure_hard_limit:
        errors.append(
            f"max_total_exposure too high ({risk.max_total_exposure:.3f} > {live_guard.max_total_exposure_hard_limit:.3f})"
        )
    if risk.max_leverage > live_guard.max_leverage_hard_limit:
        errors.append(
            f"max_leverage too high ({risk.max_leverage:.2f} > {live_guard.max_leverage_hard_limit:.2f})"
        )
    if risk.max_symbol_exposure > risk.max_total_exposure:
        errors.append("max_symbol_exposure cannot exceed max_total_exposure")
    if risk.max_reject_ratio >= 0.98:
        warnings.append("max_reject_ratio is very high; protective auto-halt may be delayed")
    if risk.min_signal_confidence < 0.4:
        warnings.append("min_signal_confidence is low for live mode")

    if live_guard.enforce_notifications and not notifications.enabled:
        errors.append("notifications.enabled must be true when live_guard.enforce_notifications is true")

    if exchange.testnet:
        warnings.append("exchange.testnet=true while mode=live")
    if config.llm.enabled:
        warnings.append("llm.enabled=true; live candidate ranking can vary by provider/API response")

    return {
        "checked": True,
        "mode": config.mode,
        "passed": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
