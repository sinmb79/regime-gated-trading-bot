from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .runtime import TradingRuntime


@dataclass(frozen=True)
class RuntimeProfile:
    name: str
    config_path: str
    interval_seconds: int = 5
    enabled: bool = True
    live_confirm_token: str = ""

    @classmethod
    def from_raw(cls, raw: Dict[str, Any], base_dir: Path, index: int) -> "RuntimeProfile":
        if not isinstance(raw, dict):
            raise ValueError(f"invalid profile at index={index}")

        name = str(raw.get("name") or f"profile_{index + 1}").strip()
        if not name:
            name = f"profile_{index + 1}"

        path_raw = str(raw.get("config_path") or "").strip()
        if not path_raw:
            raise ValueError(f"profile[{name}] missing config_path")
        cfg_path = Path(path_raw)
        if not cfg_path.is_absolute():
            cfg_path = (base_dir / cfg_path).resolve()

        return cls(
            name=name,
            config_path=str(cfg_path),
            interval_seconds=max(1, int(raw.get("interval_seconds", 5) or 5)),
            enabled=bool(raw.get("enabled", True)),
            live_confirm_token=str(raw.get("live_confirm_token") or ""),
        )


class MultiRuntimeManager:
    def __init__(self, multi_config_path: str):
        self.multi_config_path = Path(multi_config_path).resolve()
        self.base_dir = self.multi_config_path.parent
        self.profiles = self._load_profiles()
        self.runtimes: Dict[str, TradingRuntime] = {}
        self.profile_by_name: Dict[str, RuntimeProfile] = {}
        self._build_runtimes()

    def _load_profiles(self) -> List[RuntimeProfile]:
        raw = json.loads(self.multi_config_path.read_text(encoding="utf-8-sig"))
        items = raw.get("profiles", [])
        if not isinstance(items, list) or not items:
            raise ValueError("multi config must contain non-empty profiles list")

        profiles: List[RuntimeProfile] = []
        names = set()
        for idx, item in enumerate(items):
            profile = RuntimeProfile.from_raw(item, base_dir=self.base_dir, index=idx)
            if profile.name in names:
                raise ValueError(f"duplicate profile name: {profile.name}")
            names.add(profile.name)
            profiles.append(profile)
        return profiles

    def _build_runtimes(self) -> None:
        for profile in self.profiles:
            if not profile.enabled:
                continue
            runtime = TradingRuntime(profile.config_path)
            self.runtimes[profile.name] = runtime
            self.profile_by_name[profile.name] = profile

    def get_status(self) -> Dict[str, Any]:
        rows: Dict[str, Any] = {}
        for name, runtime in self.runtimes.items():
            profile = self.profile_by_name[name]
            try:
                status = runtime.get_status()
                rows[name] = {
                    "enabled": True,
                    "config_path": profile.config_path,
                    "interval_seconds": profile.interval_seconds,
                    "status": status,
                }
            except Exception as exc:
                rows[name] = {
                    "enabled": True,
                    "config_path": profile.config_path,
                    "interval_seconds": profile.interval_seconds,
                    "error": str(exc),
                }

        disabled = [p for p in self.profiles if not p.enabled]
        for profile in disabled:
            rows[profile.name] = {
                "enabled": False,
                "config_path": profile.config_path,
                "interval_seconds": profile.interval_seconds,
                "status": "disabled",
            }

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "multi_config_path": str(self.multi_config_path),
            "profile_count": len(self.profiles),
            "active_count": len(self.runtimes),
            "profiles": rows,
        }

    def _get_profile(self, name: str) -> RuntimeProfile:
        for profile in self.profiles:
            if profile.name == name:
                return profile
        raise KeyError(f"profile not found: {name}")

    def _get_runtime(self, name: str) -> TradingRuntime:
        runtime = self.runtimes.get(name)
        if runtime is None:
            raise KeyError(f"runtime not available (disabled or missing): {name}")
        return runtime

    def get_profile_status(self, name: str) -> Dict[str, Any]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return {
                "name": profile.name,
                "enabled": False,
                "config_path": profile.config_path,
                "interval_seconds": profile.interval_seconds,
                "status": "disabled",
            }
        runtime = self._get_runtime(name)
        return {
            "name": profile.name,
            "enabled": True,
            "config_path": profile.config_path,
            "interval_seconds": profile.interval_seconds,
            "status": runtime.get_status(),
        }

    def run_once_all(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for name, runtime in self.runtimes.items():
            try:
                out[name] = {"status": "ok", "result": runtime.run_once()}
            except Exception as exc:
                out[name] = {"status": "error", "error": str(exc)}
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "results": out,
        }

    def start_all(self, interval_override: int | None = None, live_confirm_token: str = "") -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for name, runtime in self.runtimes.items():
            profile = self.profile_by_name[name]
            interval = interval_override if interval_override is not None and interval_override > 0 else profile.interval_seconds
            token = live_confirm_token if live_confirm_token else profile.live_confirm_token
            try:
                out[name] = runtime.start(interval_seconds=interval, live_confirm_token=token)
            except Exception as exc:
                out[name] = {"status": "error", "error": str(exc)}
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "results": out,
        }

    def start_profile(self, name: str, interval_seconds: int | None = None, live_confirm_token: str = "") -> Dict[str, Any]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return {"status": "disabled", "profile": name}
        runtime = self._get_runtime(name)
        interval = interval_seconds if interval_seconds is not None and interval_seconds > 0 else profile.interval_seconds
        token = live_confirm_token if live_confirm_token else profile.live_confirm_token
        return runtime.start(interval_seconds=interval, live_confirm_token=token)

    def stop_all(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for name, runtime in self.runtimes.items():
            try:
                out[name] = runtime.stop()
            except Exception as exc:
                out[name] = {"status": "error", "error": str(exc)}
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "results": out,
        }

    def stop_profile(self, name: str) -> Dict[str, Any]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return {"status": "disabled", "profile": name}
        runtime = self._get_runtime(name)
        return runtime.stop()

    def run_once_profile(self, name: str) -> Dict[str, Any]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return {"status": "disabled", "profile": name}
        runtime = self._get_runtime(name)
        return runtime.run_once()

    def clear_profile_risk(self, name: str, confirm_token: str = "") -> Dict[str, Any]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return {"status": "disabled", "profile": name}
        runtime = self._get_runtime(name)
        return runtime.clear_risk_halt(confirm_token=confirm_token)

    def run_profile_live_readiness(self, name: str) -> Dict[str, Any]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return {"status": "disabled", "profile": name}
        runtime = self._get_runtime(name)
        return runtime.run_live_readiness()

    def save_profile_live_readiness_report(self, name: str, output_path: str | None = None) -> Dict[str, Any]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return {"status": "disabled", "profile": name}
        runtime = self._get_runtime(name)
        return runtime.save_live_readiness_report(output_path=output_path)

    def test_profile_llm(self, name: str, sample_symbol: str = "BTCUSDT") -> Dict[str, Any]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return {"status": "disabled", "profile": name}
        runtime = self._get_runtime(name)
        return runtime.test_llm_connection(sample_symbol=sample_symbol)

    def run_profile_exchange_probe(self, name: str, symbols: list[str] | None = None) -> Dict[str, Any]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return {"status": "disabled", "profile": name}
        runtime = self._get_runtime(name)
        return runtime.run_exchange_probe(symbols=symbols)

    def save_profile_exchange_probe_report(
        self,
        name: str,
        output_path: str | None = None,
        symbols: list[str] | None = None,
    ) -> Dict[str, Any]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return {"status": "disabled", "profile": name}
        runtime = self._get_runtime(name)
        return runtime.save_exchange_probe_report(output_path=output_path, symbols=symbols)

    def get_profile_reject_metrics(self, name: str, limit: int = 200) -> Dict[str, Any]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return {"status": "disabled", "profile": name}
        runtime = self._get_runtime(name)
        safe_limit = max(10, min(int(limit or 200), 5000))
        return runtime.get_reject_reason_metrics(limit=safe_limit)

    def patch_profile_alert_config(self, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return {"status": "disabled", "profile": name}
        runtime = self._get_runtime(name)

        raw = payload if isinstance(payload, dict) else {}
        risk_limits_keys = [
            "reject_rate_warn",
            "reject_rate_critical",
            "reject_reason_rate_warn",
            "reject_reason_rate_critical",
            "reject_reason_min_samples",
            "reject_alert_profile",
        ]
        validation_gate_keys = [
            "alert_enabled",
            "alert_min_samples",
            "alert_pass_rate_warn",
            "alert_pass_rate_critical",
            "alert_max_drawdown_warn",
            "alert_max_drawdown_critical",
        ]
        notifications_keys = [
            "enabled",
            "cooldown_seconds",
            "max_per_hour",
            "send_on_levels",
            "include_reject_summary",
        ]

        safe_payload: Dict[str, Any] = {}

        risk_limits: Dict[str, Any] = {}
        for key in risk_limits_keys:
            if key in raw and raw.get(key) is not None:
                risk_limits[key] = raw.get(key)
        if risk_limits:
            safe_payload["risk_limits"] = risk_limits

        validation_gate: Dict[str, Any] = {}
        for key in validation_gate_keys:
            if key in raw and raw.get(key) is not None:
                validation_gate[key] = raw.get(key)
        if validation_gate:
            safe_payload["validation_gate"] = validation_gate

        notifications: Dict[str, Any] = {}
        for key in notifications_keys:
            if key in raw and raw.get(key) is not None:
                notifications[key] = raw.get(key)
        if notifications:
            safe_payload["notifications"] = notifications

        if not safe_payload:
            return {"status": "noop", "profile": name, "message": "no alert config fields provided"}
        return runtime.patch_config(safe_payload)

    def test_profile_validation_alert(self, name: str, level: str = "warn") -> Dict[str, Any]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return {"status": "disabled", "profile": name}
        runtime = self._get_runtime(name)
        selected = str(level or "warn").strip().lower()
        if selected not in {"warn", "critical"}:
            selected = "warn"
        return runtime.trigger_validation_alert_test(level=selected)

    def get_profile_learning_status(self, name: str) -> Dict[str, Any]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return {"status": "disabled", "profile": name}
        runtime = self._get_runtime(name)
        status = runtime.get_status()
        return {
            "profile": name,
            "auto_learning": status.get("auto_learning", {}),
            "validation_gate": status.get("validation_gate", {}),
            "validation_history": status.get("validation_history", {}),
        }

    def get_profile_validation_history(self, name: str, limit: int = 30) -> Dict[str, Any]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return {"status": "disabled", "profile": name}
        runtime = self._get_runtime(name)
        safe_limit = max(1, min(int(limit or 30), 2000))
        return runtime.get_validation_history(limit=safe_limit)

    def patch_profile_auto_learning_config(self, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return {"status": "disabled", "profile": name}
        runtime = self._get_runtime(name)

        raw = payload if isinstance(payload, dict) else {}
        auto_learning_keys = [
            "enabled",
            "paper_only",
            "apply_mode",
            "apply_interval_cycles",
            "window_days",
            "min_trades_per_strategy",
            "min_confidence",
            "max_weight_step_pct",
            "max_strategy_changes_per_apply",
            "max_applies_per_day",
            "allow_pause",
            "max_pending_proposals",
            "proposal_expiry_hours",
        ]
        auto_learning: Dict[str, Any] = {}
        for key in auto_learning_keys:
            if key in raw and raw.get(key) is not None:
                auto_learning[key] = raw.get(key)
        if not auto_learning:
            return {"status": "noop", "profile": name, "message": "no auto_learning fields provided"}
        return runtime.patch_config({"auto_learning": auto_learning})

    def get_profile_strategy_bot_config(self, name: str, strategy_id: str = "") -> Dict[str, Any]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return {"status": "disabled", "profile": name}
        runtime = self._get_runtime(name)

        status = runtime.get_status()
        cfg = status.get("config", {}) if isinstance(status, dict) else {}
        strategies = cfg.get("strategies", {}) if isinstance(cfg, dict) else {}
        if not isinstance(strategies, dict):
            strategies = {}

        target = str(strategy_id or "").strip()
        if target:
            raw = strategies.get(target, {})
            if not isinstance(raw, dict):
                raw = {}
            return {
                "profile": name,
                "strategy_id": target,
                "exists": target in strategies,
                "bot_type": str(raw.get("bot_type", "") or ""),
                "bot_profile": raw.get("bot_profile", {}) if isinstance(raw.get("bot_profile", {}), dict) else {},
                "bot_profile_by_regime": raw.get("bot_profile_by_regime", {}) if isinstance(raw.get("bot_profile_by_regime", {}), dict) else {},
                "raw": raw,
            }

        result: Dict[str, Any] = {}
        for sid, raw_cfg in strategies.items():
            if not isinstance(raw_cfg, dict):
                continue
            result[str(sid)] = {
                "bot_type": str(raw_cfg.get("bot_type", "") or ""),
                "bot_profile": raw_cfg.get("bot_profile", {}) if isinstance(raw_cfg.get("bot_profile", {}), dict) else {},
                "bot_profile_by_regime": raw_cfg.get("bot_profile_by_regime", {}) if isinstance(raw_cfg.get("bot_profile_by_regime", {}), dict) else {},
            }
        return {"profile": name, "strategies": result}

    def patch_profile_strategy_bot_config(self, name: str, strategy_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return {"status": "disabled", "profile": name}
        runtime = self._get_runtime(name)

        sid = str(strategy_id or "").strip()
        if not sid:
            return {"status": "error", "profile": name, "error": "strategy_id is required"}

        raw = payload if isinstance(payload, dict) else {}
        patch: Dict[str, Any] = {}

        if "bot_type" in raw and raw.get("bot_type") is not None:
            patch["bot_type"] = str(raw.get("bot_type") or "").strip()
        if "bot_profile" in raw and isinstance(raw.get("bot_profile"), dict):
            patch["bot_profile"] = raw.get("bot_profile")
        if "bot_profile_by_regime" in raw and isinstance(raw.get("bot_profile_by_regime"), dict):
            patch["bot_profile_by_regime"] = raw.get("bot_profile_by_regime")

        if not patch:
            return {"status": "noop", "profile": name, "strategy_id": sid, "message": "no strategy bot fields provided"}

        return runtime.patch_config({"strategies": {sid: patch}})

    def get_profile_executions(
        self,
        name: str,
        limit: int = 30,
        status: str | None = None,
        reject_reason: str | None = None,
        is_partial: bool | None = None,
    ) -> list[Dict[str, Any]]:
        profile = self._get_profile(name)
        if not profile.enabled:
            return []
        runtime = self._get_runtime(name)
        safe_limit = max(1, min(int(limit or 30), 200))
        status_norm = str(status or "").strip().lower() or None
        reason_norm = str(reject_reason or "").strip() or None
        partial_norm = is_partial if isinstance(is_partial, bool) else None
        return runtime.get_executions(
            limit=safe_limit,
            status=status_norm,
            reject_reason=reason_norm,
            is_partial=partial_norm,
        )

    def run_loop(self, interval_override: int | None = None, live_confirm_token: str = "") -> Dict[str, Any]:
        started = self.start_all(interval_override=interval_override, live_confirm_token=live_confirm_token)
        try:
            while True:
                time.sleep(1.0)
        finally:
            self.stop_all()
        return started

    def close(self) -> None:
        for runtime in self.runtimes.values():
            try:
                runtime.close()
            except Exception:
                pass
