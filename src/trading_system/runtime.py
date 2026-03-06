from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any, Dict, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from .config import AppConfig
from .data import MockMarketDataCollector
from .exchange import build_exchange
from .journal import TradeJournal
from .llm import LLMAdvisor
from .learning import LearningEngine
from .pipeline import TradingOrchestrator
from .preflight import evaluate_live_preflight
from .validation_gate import evaluate_validation_gate
from .validation_history import build_validation_history_payload, load_validation_history


_HIDDEN_VALUE = "[HIDDEN]"
_RISK_HALT_CONFIRM_TOKEN = "UNHALT"


class TradingRuntime:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self._lock = Lock()
        self._thread: Optional[Thread] = None
        self._stop_event = Event()
        self._is_running = False
        self._last_summary: Optional[Dict[str, Any]] = None
        self._cycle_count = 0
        self._last_error: Optional[str] = None
        self._risk_halt_reason: Optional[str] = None
        self._risk_clear_failures: int = 0
        self._risk_clear_locked_until: float = 0.0
        self._started_at: Optional[str] = None
        self._interval_seconds = 5
        self._reject_alert_last_sent_at = 0.0
        self._reject_alert_last_signature = ""
        self._reject_alert_send_times: deque[float] = deque(maxlen=200)
        self._validation_alert_last_sent_at = 0.0
        self._validation_alert_last_signature = ""
        self._validation_alert_send_times: deque[float] = deque(maxlen=200)
        self._auto_learning_last_result: Dict[str, Any] = {"status": "idle", "applied_count": 0, "applied": []}
        self._auto_learning_last_applied_cycle: int = 0
        self._auto_learning_last_applied_at: Optional[str] = None
        self._auto_learning_apply_times: deque[float] = deque(maxlen=200)

        self.config = AppConfig.from_file(str(self.config_path))
        self.exchange = build_exchange(self.config.exchange)
        self.journal = TradeJournal(self.config.journal.path)
        self._collector = MockMarketDataCollector(symbols=self.config.pipeline.universe)
        self._learning = LearningEngine(self.journal)

    @property
    def is_running(self) -> bool:
        return self._is_running

    def _risk_limits_state(self) -> Dict[str, Any]:
        return asdict(self.config.risk_limits)

    @staticmethod
    def _masked_token_hint(raw: str) -> str:
        token = str(raw or "").strip()
        if len(token) <= 2:
            return "*" * len(token)
        return token[:2] + "*" * (len(token) - 2)

    def _risk_clear_lock_remaining_ms(self) -> int:
        remain = (self._risk_clear_locked_until - time.time()) * 1000.0
        return max(0, int(remain))

    def _set_risk_clear_lock(self) -> None:
        lock_sec = max(0, int(self.config.risk_guard.clear_lock_duration_seconds))
        if lock_sec <= 0:
            self._risk_clear_locked_until = 0.0
            return
        self._risk_clear_locked_until = time.time() + lock_sec

    def _risk_clear_lock_status(self) -> Dict[str, Any]:
        remaining_ms = self._risk_clear_lock_remaining_ms()
        return {
            "is_locked": remaining_ms > 0,
            "locked_until": self._risk_clear_locked_until,
            "locked_remaining_ms": remaining_ms,
            "failed_attempts": self._risk_clear_failures,
        }

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    @classmethod
    def _bounded_weight(cls, current_weight: float, suggested_weight: float, max_step_pct: float) -> float:
        current = max(0.01, float(current_weight))
        target = cls._clamp(float(suggested_weight), 0.01, 3.0)
        step_pct = max(0.0, float(max_step_pct))
        if step_pct <= 0:
            return round(target, 3)
        max_step = max(0.01, current * step_pct)
        lower = max(0.01, current - max_step)
        upper = current + max_step
        return round(cls._clamp(target, lower, upper), 3)

    def _auto_learning_status(self, config: AppConfig) -> Dict[str, Any]:
        cfg = config.auto_learning
        gate = self._validation_gate(config)
        now = time.time()
        while self._auto_learning_apply_times and now - self._auto_learning_apply_times[0] > 86400:
            self._auto_learning_apply_times.popleft()

        interval = max(1, int(cfg.apply_interval_cycles or 1))
        if self._auto_learning_last_applied_cycle > 0:
            cycles_since_last = max(0, self._cycle_count - self._auto_learning_last_applied_cycle)
        else:
            cycles_since_last = max(0, self._cycle_count)
        remaining_cycles = max(0, interval - cycles_since_last)
        max_daily = max(0, int(cfg.max_applies_per_day or 0))

        return {
            "enabled": bool(cfg.enabled),
            "paper_only": bool(cfg.paper_only),
            "window_days": int(cfg.window_days),
            "min_trades_per_strategy": int(cfg.min_trades_per_strategy),
            "min_confidence": float(cfg.min_confidence),
            "max_weight_step_pct": float(cfg.max_weight_step_pct),
            "max_strategy_changes_per_apply": int(cfg.max_strategy_changes_per_apply),
            "max_applies_per_day": max_daily,
            "allow_pause": bool(cfg.allow_pause),
            "apply_interval_cycles": interval,
            "remaining_cycles_to_next_apply": remaining_cycles,
            "last_applied_cycle": self._auto_learning_last_applied_cycle,
            "last_applied_at": self._auto_learning_last_applied_at,
            "applied_today": len(self._auto_learning_apply_times),
            "daily_quota_remaining": max(-1, max_daily - len(self._auto_learning_apply_times)) if max_daily > 0 else -1,
            "last_result": self._auto_learning_last_result,
            "validation_gate": gate,
        }

    def _auto_learning_try_apply(self, config: AppConfig) -> Dict[str, Any]:
        cfg = config.auto_learning
        result: Dict[str, Any] = {
            "enabled": bool(cfg.enabled),
            "status": "disabled",
            "cycle": self._cycle_count,
            "applied_count": 0,
            "applied": [],
            "skipped": [],
        }
        if not cfg.enabled:
            return result

        mode = str(config.mode).strip().lower()
        if cfg.paper_only and mode not in {"dry", "paper"}:
            result["status"] = "blocked_mode"
            result["reason"] = "auto learning is restricted to dry/paper mode"
            return result

        gate = self._validation_gate(config)
        if config.validation_gate.enforce_for_auto_learning and not gate.get("passed", False):
            result["status"] = "blocked_validation_gate"
            result["reason"] = "validation gate failed"
            result["validation_gate"] = gate
            return result

        if self._risk_halt_reason:
            result["status"] = "blocked_risk_halt"
            result["reason"] = "risk halt is active"
            return result

        interval = max(1, int(cfg.apply_interval_cycles or 1))
        if self._auto_learning_last_applied_cycle > 0:
            cycles_since_last = max(0, self._cycle_count - self._auto_learning_last_applied_cycle)
        else:
            cycles_since_last = max(0, self._cycle_count)
        if cycles_since_last < interval:
            result["status"] = "waiting_cycle_interval"
            result["remaining_cycles"] = interval - cycles_since_last
            return result

        now = time.time()
        while self._auto_learning_apply_times and now - self._auto_learning_apply_times[0] > 86400:
            self._auto_learning_apply_times.popleft()
        max_daily = max(0, int(cfg.max_applies_per_day or 0))
        if max_daily > 0 and len(self._auto_learning_apply_times) >= max_daily:
            result["status"] = "rate_limited"
            result["reason"] = "daily auto-learning apply quota reached"
            return result

        tunings = self._learning.suggest_tuning(
            current_strategy_weights=config.strategy_weights(),
            window_days=max(0, int(cfg.window_days)),
            min_trades=max(1, int(cfg.min_trades_per_strategy)),
        )

        min_confidence = self._clamp(float(cfg.min_confidence), 0.0, 1.0)
        actionable = sorted(
            [
                t for t in tunings
                if str(t.action) in {"increase", "decrease", "pause"}
                and float(t.confidence or 0.0) >= min_confidence
            ],
            key=lambda x: float(getattr(x, "confidence", 0.0)),
            reverse=True,
        )
        if not actionable:
            result["status"] = "no_actionable"
            result["reason"] = "no tuning candidate passed confidence/action filters"
            return result

        strategy_cfg = {
            key: (dict(value) if isinstance(value, dict) else {})
            for key, value in config.strategies.items()
        }
        max_changes = max(1, int(cfg.max_strategy_changes_per_apply or 1))
        allow_pause = bool(cfg.allow_pause)
        max_step_pct = max(0.0, float(cfg.max_weight_step_pct or 0.0))
        applied: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []

        for item in actionable:
            strategy = str(getattr(item, "strategy", "") or "").strip()
            action = str(getattr(item, "action", "") or "hold")
            confidence = float(getattr(item, "confidence", 0.0) or 0.0)
            reason = str(getattr(item, "reason", "") or "").strip()
            if not strategy:
                continue
            if len(applied) >= max_changes:
                skipped.append(
                    {"strategy": strategy, "action": action, "reason": "max_strategy_changes_per_apply reached"}
                )
                continue

            current = dict(strategy_cfg.get(strategy, {}))
            current_enabled = bool(current.get("enabled", True))
            current_weight = float(current.get("weight", 1.0) or 1.0)

            if action == "pause":
                if not allow_pause:
                    skipped.append(
                        {"strategy": strategy, "action": action, "reason": "pause action disabled by config"}
                    )
                    continue
                if not current_enabled:
                    skipped.append(
                        {"strategy": strategy, "action": action, "reason": "already paused"}
                    )
                    continue
                current["enabled"] = False
                strategy_cfg[strategy] = current
                applied.append(
                    {
                        "strategy": strategy,
                        "action": action,
                        "weight_before": round(current_weight, 3),
                        "weight_after": round(current_weight, 3),
                        "enabled_after": False,
                        "confidence": confidence,
                        "reason": reason,
                    }
                )
                continue

            suggested_weight = float(getattr(item, "suggested_weight", current_weight) or current_weight)
            bounded_weight = self._bounded_weight(current_weight, suggested_weight, max_step_pct=max_step_pct)
            if abs(bounded_weight - current_weight) < 0.0005 and current_enabled:
                skipped.append(
                    {"strategy": strategy, "action": action, "reason": "bounded target equals current weight"}
                )
                continue

            current["enabled"] = True
            current["weight"] = bounded_weight
            strategy_cfg[strategy] = current
            applied.append(
                {
                    "strategy": strategy,
                    "action": action,
                    "weight_before": round(current_weight, 3),
                    "weight_after": bounded_weight,
                    "enabled_after": True,
                    "confidence": confidence,
                    "reason": reason,
                }
            )

        result["skipped"] = skipped[:20]
        if not applied:
            result["status"] = "no_change"
            result["reason"] = "all actionable tuning results were filtered or unchanged"
            return result

        merged = self._merge(asdict(config), {"strategies": strategy_cfg})
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

        self.config = AppConfig.from_file(str(self.config_path))
        applied_ts = datetime.utcnow().isoformat()
        self._auto_learning_last_applied_cycle = self._cycle_count
        self._auto_learning_last_applied_at = applied_ts
        self._auto_learning_apply_times.append(now)

        for item in applied:
            try:
                self.journal.record_auto_learning_event(
                    source="auto",
                    mode=str(config.mode),
                    cycle=int(self._cycle_count),
                    strategy=str(item.get("strategy", "")),
                    action=str(item.get("action", "hold")),
                    weight_before=float(item.get("weight_before", 0.0)),
                    weight_after=float(item.get("weight_after", 0.0)),
                    enabled_after=bool(item.get("enabled_after", True)),
                    confidence=float(item.get("confidence", 0.0)),
                    reason=str(item.get("reason", "")),
                    meta={
                        "window_days": int(cfg.window_days),
                        "min_trades_per_strategy": int(cfg.min_trades_per_strategy),
                        "min_confidence": float(cfg.min_confidence),
                        "max_weight_step_pct": float(cfg.max_weight_step_pct),
                        "max_strategy_changes_per_apply": int(cfg.max_strategy_changes_per_apply),
                        "apply_interval_cycles": int(cfg.apply_interval_cycles),
                    },
                )
            except Exception:
                pass
            try:
                self.journal.record_feedback(
                    strategy=str(item.get("strategy", "")),
                    metric_name="auto_learning_apply",
                    metric_value=float(item.get("weight_after", 0.0)),
                    suggestion=str(item.get("reason", "")),
                )
            except Exception:
                pass

        result["status"] = "applied"
        result["applied_count"] = len(applied)
        result["applied"] = applied
        result["applied_at"] = applied_ts
        return result

    def _resolve_reject_thresholds(self) -> Dict[str, Any]:
        limits = self._risk_limits_state()
        profile = str(limits.get("reject_alert_profile", "auto")).strip().lower() or "auto"
        mode = str(self.config.mode or "").strip().lower()
        if profile == "auto":
            if mode in {"safe", "paper", "dry"}:
                profile = "balanced"
            elif mode in {"aggressive", "live"}:
                profile = "aggressive"
            else:
                profile = "balanced"

        # Backward-compatible aliases used in UI/editor presets.
        profile = {
            "tight": "safe",
            "normal": "balanced",
            "loose": "aggressive",
        }.get(profile, profile)

        factor_map = {
            "safe": 0.75,
            "balanced": 1.0,
            "aggressive": 1.25,
        }
        if profile not in factor_map:
            profile = "balanced"
        factor = factor_map.get(profile, 1.0)

        def _clamp(value: float, lo: float, hi: float) -> float:
            return max(lo, min(hi, value))

        reject_rate_warn = _clamp(float(limits.get("reject_rate_warn", 0.35)) * factor, 0.01, 0.95)
        reject_rate_critical = _clamp(float(limits.get("reject_rate_critical", 0.60)) * factor, reject_rate_warn + 0.02, 0.99)
        reason_rate_warn = _clamp(float(limits.get("reject_reason_rate_warn", 0.30)) * factor, 0.01, 0.95)
        reason_rate_critical = _clamp(float(limits.get("reject_reason_rate_critical", 0.50)) * factor, reason_rate_warn + 0.02, 0.99)

        return {
            "profile": profile,
            "warn": reject_rate_warn,
            "critical": reject_rate_critical,
            "reason_warn": reason_rate_warn,
            "reason_critical": reason_rate_critical,
            "min_samples": int(limits.get("reject_reason_min_samples", 20)),
            "factor": factor,
        }

    def _build_reject_alert_text(self, metrics: Dict[str, Any], alerts: list[Dict[str, Any]]) -> str:
        total = int(metrics.get("total_executions", 0) or 0)
        rejected = int(metrics.get("rejected_executions", 0) or 0)
        reject_rate = float(metrics.get("reject_rate", 0.0) or 0.0)
        top_reasons = metrics.get("reasons", [])[:3]
        reason_text = ", ".join([
            f"{item.get('reason')} {(float(item.get('ratio', 0.0) or 0.0) * 100):.1f}% ({int(item.get('count', 0))}건)"
            for item in top_reasons
        ]) or "-"

        alert_labels = [item.get("message") for item in alerts if item.get("message")]
        lines = [
            f"[{datetime.utcnow().isoformat()}] 거부 사유 경보",
            f"모드: {self.config.mode}",
            f"샘플: {total}건, 거부: {rejected}건 ({reject_rate * 100:.1f}%)",
            f"주요 사유: {reason_text}",
        ]
        if alert_labels:
            lines.append("요약: " + " / ".join(alert_labels[:3]))
        return "\n".join(lines)

    def _build_reject_alert_payload(self, metrics: Dict[str, Any], alerts: list[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "event": "reject_reason_alert",
            "ts": datetime.utcnow().isoformat(),
            "mode": self.config.mode,
            "alerts": alerts,
            "summary": {
                "total_executions": metrics.get("total_executions", 0),
                "rejected_executions": metrics.get("rejected_executions", 0),
                "reject_rate": metrics.get("reject_rate", 0.0),
            },
            "thresholds": metrics.get("thresholds", {}),
            "reasons": metrics.get("reasons", []),
        }

    def _post_json(self, url: str, payload: Dict[str, Any]) -> bool:
        try:
            request = Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=8) as response:
                status = getattr(response, "status", None)
                if status is None:
                    status = getattr(response, "getcode", lambda: None)()
                return status is not None and 200 <= int(status) < 300
        except URLError:
            return False

    def _post_telegram(self, text: str) -> bool:
        token = (self.config.notifications.telegram_bot_token or "").strip()
        chat_id = (self.config.notifications.telegram_chat_id or "").strip()
        if not token or not chat_id:
            return False
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            request = Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=8) as response:
                status = getattr(response, "status", None)
                if status is None:
                    status = getattr(response, "getcode", lambda: None)()
                return status is not None and 200 <= int(status) < 300
        except URLError:
            return False

    def _should_send_reject_alert(self, now: float, signature: str) -> bool:
        cfg = self.config.notifications
        if not cfg.enabled:
            return False

        cooldown_seconds = max(0, int(cfg.cooldown_seconds or 0))
        if self._reject_alert_last_signature == signature and now < (self._reject_alert_last_sent_at + cooldown_seconds):
            return False

        if now < (self._reject_alert_last_sent_at + cooldown_seconds):
            return False

        if cfg.max_per_hour > 0:
            while self._reject_alert_send_times and now - self._reject_alert_send_times[0] > 3600:
                self._reject_alert_send_times.popleft()
            if len(self._reject_alert_send_times) >= int(cfg.max_per_hour):
                return False

        return True

    def _send_reject_alert_notifications(self, metrics: Dict[str, Any], alerts: list[Dict[str, Any]]) -> None:
        cfg = self.config.notifications
        if not cfg.enabled:
            return

        if not alerts:
            return

        send_levels = {str(level).strip().lower() for level in (cfg.send_on_levels or [])}
        filtered = [item for item in alerts if str(item.get("level", "")).strip().lower() in send_levels]
        if not filtered:
            return

        signature = str(
            json.dumps(filtered, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
        now = time.time()
        if not self._should_send_reject_alert(now, signature):
            return

        message = self._build_reject_alert_text(metrics, filtered)
        payload = self._build_reject_alert_payload(metrics, filtered)
        if not cfg.include_reject_summary:
            payload.pop("reasons", None)
        sent = False

        if cfg.webhook_url:
            sent = self._post_json(cfg.webhook_url, payload) or sent
        if cfg.slack_webhook_url:
            sent = self._post_json(cfg.slack_webhook_url, {"text": message}) or sent
        if cfg.telegram_bot_token and cfg.telegram_chat_id:
            sent = self._post_telegram(message) or sent

        if sent:
            self._reject_alert_last_sent_at = now
            self._reject_alert_last_signature = signature
            self._reject_alert_send_times.append(now)

    def _validation_alert_thresholds(self, config: AppConfig) -> Dict[str, Any]:
        gate = config.validation_gate
        pass_warn = self._clamp(float(gate.alert_pass_rate_warn), 0.0, 1.0)
        pass_critical = self._clamp(float(gate.alert_pass_rate_critical), 0.0, pass_warn)
        dd_warn = max(0.0, float(gate.alert_max_drawdown_warn))
        dd_critical = max(dd_warn, float(gate.alert_max_drawdown_critical))
        return {
            "enabled": bool(gate.alert_enabled),
            "min_samples": max(1, int(gate.alert_min_samples or 1)),
            "pass_rate_warn": pass_warn,
            "pass_rate_critical": pass_critical,
            "max_drawdown_warn": dd_warn,
            "max_drawdown_critical": dd_critical,
        }

    def _build_validation_history_alerts(
        self,
        history: Dict[str, Any],
        config: AppConfig,
    ) -> tuple[Dict[str, Any], list[Dict[str, Any]]]:
        thresholds = self._validation_alert_thresholds(config)
        alerts: list[Dict[str, Any]] = []
        if not thresholds["enabled"]:
            return thresholds, alerts

        total = int(history.get("total_runs", 0) or 0)
        pass_rate = float(history.get("pass_rate", 0.0) or 0.0)
        latest = history.get("latest", {}) if isinstance(history, dict) else {}
        latest_overall = bool(latest.get("overall_passed", False)) if isinstance(latest, dict) else False
        latest_dd = float((latest.get("max_drawdown_pct", 0.0) if isinstance(latest, dict) else 0.0) or 0.0)

        if total < int(thresholds["min_samples"]):
            alerts.append(
                {
                    "level": "info",
                    "code": "validation_samples_low",
                    "message": f"검증 이력 샘플이 부족합니다 ({total}/{thresholds['min_samples']}).",
                }
            )
            return thresholds, alerts

        if pass_rate <= float(thresholds["pass_rate_critical"]):
            alerts.append(
                {
                    "level": "critical",
                    "code": "validation_pass_rate_low",
                    "message": f"검증 통과율이 {(pass_rate * 100):.1f}%로 임계치 {(thresholds['pass_rate_critical'] * 100):.1f}% 이하입니다.",
                }
            )
        elif pass_rate <= float(thresholds["pass_rate_warn"]):
            alerts.append(
                {
                    "level": "warn",
                    "code": "validation_pass_rate_low",
                    "message": f"검증 통과율이 {(pass_rate * 100):.1f}%로 경고 임계치 {(thresholds['pass_rate_warn'] * 100):.1f}% 이하입니다.",
                }
            )

        if latest_dd >= float(thresholds["max_drawdown_critical"]):
            alerts.append(
                {
                    "level": "critical",
                    "code": "validation_drawdown_high",
                    "message": f"최근 검증 MDD가 {(latest_dd * 100):.1f}%로 임계치 {(thresholds['max_drawdown_critical'] * 100):.1f}% 이상입니다.",
                }
            )
        elif latest_dd >= float(thresholds["max_drawdown_warn"]):
            alerts.append(
                {
                    "level": "warn",
                    "code": "validation_drawdown_high",
                    "message": f"최근 검증 MDD가 {(latest_dd * 100):.1f}%로 경고 임계치 {(thresholds['max_drawdown_warn'] * 100):.1f}% 이상입니다.",
                }
            )

        if not latest_overall:
            alerts.append(
                {
                    "level": "warn",
                    "code": "validation_latest_failed",
                    "message": "최근 검증 결과가 FAIL입니다.",
                }
            )

        return thresholds, alerts

    def _build_validation_alert_text(self, history: Dict[str, Any], alerts: list[Dict[str, Any]]) -> str:
        total = int(history.get("total_runs", 0) or 0)
        pass_rate = float(history.get("pass_rate", 0.0) or 0.0)
        latest = history.get("latest", {}) if isinstance(history, dict) else {}
        latest_ts = str(latest.get("timestamp", "-")) if isinstance(latest, dict) else "-"
        latest_dd = float((latest.get("max_drawdown_pct", 0.0) if isinstance(latest, dict) else 0.0) or 0.0)
        summary = " / ".join([str(item.get("message", "")) for item in alerts[:3] if item.get("message")]) or "-"
        return "\n".join(
            [
                f"[{datetime.utcnow().isoformat()}] 검증 이력 경보",
                f"검증횟수: {total}, 통과율: {pass_rate * 100:.1f}%",
                f"최근 검증: {latest_ts}, MDD: {latest_dd * 100:.1f}%",
                f"요약: {summary}",
            ]
        )

    def _build_validation_alert_payload(self, history: Dict[str, Any], alerts: list[Dict[str, Any]], thresholds: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "event": "validation_history_alert",
            "ts": datetime.utcnow().isoformat(),
            "mode": self.config.mode,
            "alerts": alerts,
            "thresholds": thresholds,
            "history_summary": {
                "total_runs": history.get("total_runs", 0),
                "pass_rate": history.get("pass_rate", 0.0),
                "latest": history.get("latest", {}),
            },
        }

    def _should_send_validation_alert(self, now: float, signature: str) -> bool:
        cfg = self.config.notifications
        if not cfg.enabled:
            return False

        cooldown_seconds = max(0, int(cfg.cooldown_seconds or 0))
        if self._validation_alert_last_signature == signature and now < (self._validation_alert_last_sent_at + cooldown_seconds):
            return False

        if now < (self._validation_alert_last_sent_at + cooldown_seconds):
            return False

        if cfg.max_per_hour > 0:
            while self._validation_alert_send_times and now - self._validation_alert_send_times[0] > 3600:
                self._validation_alert_send_times.popleft()
            if len(self._validation_alert_send_times) >= int(cfg.max_per_hour):
                return False

        return True

    def _send_validation_alert_notifications(
        self,
        history: Dict[str, Any],
        thresholds: Dict[str, Any],
        alerts: list[Dict[str, Any]],
        force: bool = False,
    ) -> bool:
        cfg = self.config.notifications
        if not cfg.enabled:
            return False
        if not alerts:
            return False

        if force:
            filtered = list(alerts)
        else:
            send_levels = {str(level).strip().lower() for level in (cfg.send_on_levels or [])}
            filtered = [item for item in alerts if str(item.get("level", "")).strip().lower() in send_levels]
        if not filtered:
            return False

        signature = str(json.dumps(filtered, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        now = time.time()
        if not force and not self._should_send_validation_alert(now, signature):
            return False

        message = self._build_validation_alert_text(history, filtered)
        payload = self._build_validation_alert_payload(history, filtered, thresholds)
        sent = False
        if cfg.webhook_url:
            sent = self._post_json(cfg.webhook_url, payload) or sent
        if cfg.slack_webhook_url:
            sent = self._post_json(cfg.slack_webhook_url, {"text": message}) or sent
        if cfg.telegram_bot_token and cfg.telegram_chat_id:
            sent = self._post_telegram(message) or sent

        if sent:
            self._validation_alert_last_sent_at = now
            self._validation_alert_last_signature = signature
            self._validation_alert_send_times.append(now)
        return sent

    def _check_auto_halt(self, summary: Dict[str, Any]) -> Optional[str]:
        limits = self.config.risk_limits
        account = summary.get("account_state", {}) or {}
        today_pnl = float(account.get("today_pnl", 0.0) or 0.0)
        consecutive_losses = int(account.get("consecutive_loss_count", 0) or 0)
        equity = float(
            account.get("equity_usdt", 0.0)
            or summary.get("balance", {}).get("equity_usdt", 0.0)
            or 0.0
        )

        executed = int(summary.get("executed", 0) or 0)
        rejected = int(summary.get("rejected", 0) or 0)
        total = executed + rejected

        if limits.daily_max_loss_pct > 0 and equity > 0 and today_pnl < 0:
            loss_ratio = abs(today_pnl) / equity
            if loss_ratio >= limits.daily_max_loss_pct:
                return f"Daily loss exceeded ({loss_ratio:.2%} >= {limits.daily_max_loss_pct:.2%})"

        if limits.max_consecutive_losses > 0 and consecutive_losses >= limits.max_consecutive_losses:
            return f"Consecutive loss exceeded ({consecutive_losses} >= {limits.max_consecutive_losses})"

        if total > 0 and limits.max_reject_ratio > 0:
            reject_ratio = rejected / total
            if reject_ratio >= limits.max_reject_ratio:
                return f"Reject rate too high ({reject_ratio:.1%} >= {limits.max_reject_ratio:.1%})"

        return None

    def _mark_auto_halt_if_needed(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        reason = self._check_auto_halt(summary)
        result = dict(summary)
        result["auto_halt"] = {
            "enabled": reason is not None,
            "stopped": False,
            "reason": reason,
            "status": "ok",
        }

        if reason is None:
            return result

        self._risk_halt_reason = reason
        self._last_error = reason
        if self._is_running:
            self._stop_event.set()
            self._is_running = False
            result["auto_halt"]["stopped"] = True
            result["auto_halt"]["status"] = "auto_stopped"
        else:
            result["auto_halt"]["status"] = "risk_violation"

        return result

    def _load_config(self) -> AppConfig:
        self.config = AppConfig.from_file(str(self.config_path))
        return self.config

    def _live_preflight(self, config: AppConfig) -> Dict[str, Any]:
        return evaluate_live_preflight(config)

    def _validation_gate(self, config: AppConfig) -> Dict[str, Any]:
        return evaluate_validation_gate(config, base_dir=Path.cwd())

    def _resolve_validation_history_path(self, config: AppConfig) -> Path:
        path = Path(config.validation_gate.history_path)
        if path.is_absolute():
            return path
        return (Path.cwd() / path).resolve()

    def _validation_history_payload(self, config: AppConfig, limit: int) -> Dict[str, Any]:
        max_rows = max(1, min(200, int(limit)))
        history_path = self._resolve_validation_history_path(config)
        rows = load_validation_history(history_path, limit=max_rows)
        return build_validation_history_payload(
            rows=rows,
            limit=max_rows,
            history_path=str(history_path),
        )

    def _build_orchestrator(self, config: AppConfig) -> TradingOrchestrator:
        return TradingOrchestrator(
            config=config,
            data_collector=self._collector,
            exchange=self.exchange,
            journal=self.journal,
            llm=LLMAdvisor(
                enabled=config.llm.enabled,
                provider=config.llm.provider,
                api_key=config.llm.api_key,
                api_key_env=config.llm.api_key_env,
                api_base_url=config.llm.api_base_url,
                model=config.llm.model,
                temperature=config.llm.temperature,
                timeout_seconds=config.llm.timeout_seconds,
                max_retries=config.llm.max_retries,
                retry_delay_ms=config.llm.retry_delay_ms,
                max_tokens=config.llm.max_tokens,
                score_scale=config.llm.score_scale,
                score_candidates_limit=config.llm.score_candidates_limit,
                request_mode=config.llm.request_mode,
            ),
        )

    def _run_once_internal(self, interval_seconds: Optional[int] = None) -> Dict[str, Any]:
        if interval_seconds is not None:
            self._interval_seconds = max(1, int(interval_seconds))

        config = self._load_config()
        orchestrator = self._build_orchestrator(config)
        summary = orchestrator.run_once()
        summary = self._mark_auto_halt_if_needed(summary)
        self._cycle_count += 1
        self._last_summary = summary

        if summary.get("auto_halt", {}).get("reason"):
            self._last_error = summary["auto_halt"]["reason"]
        else:
            self._last_error = None

        try:
            reject_reason_metrics = self.get_reject_reason_metrics(limit=200)
            self._send_reject_alert_notifications(
                reject_reason_metrics,
                reject_reason_metrics.get('alerts', []),
            )
        except Exception:
            pass

        validation_alert = {
            "thresholds": {},
            "alerts": [],
            "last_alert_ts": self._validation_alert_last_sent_at,
        }
        try:
            history = self._validation_history_payload(
                config=config,
                limit=max(1, int(config.validation_gate.history_limit_default or 30)),
            )
            thresholds, alerts = self._build_validation_history_alerts(history, config)
            self._send_validation_alert_notifications(history, thresholds, alerts)
            validation_alert = {
                "thresholds": thresholds,
                "alerts": alerts,
                "last_alert_ts": self._validation_alert_last_sent_at,
            }
        except Exception:
            pass

        try:
            auto_learning = self._auto_learning_try_apply(config)
        except Exception as exc:
            auto_learning = {
                "enabled": bool(config.auto_learning.enabled),
                "status": "error",
                "reason": str(exc),
                "applied_count": 0,
                "applied": [],
            }
        summary["auto_learning"] = auto_learning
        summary["validation_alert"] = validation_alert
        self._auto_learning_last_result = auto_learning

        return summary

    def run_once(self) -> Dict[str, Any]:
        with self._lock:
            try:
                return self._run_once_internal()
            except Exception as exc:
                self._last_error = str(exc)
                raise

    def start(self, interval_seconds: Optional[int] = None, live_confirm_token: Optional[str] = None) -> Dict[str, Any]:
        if self._is_running:
            return {"status": "already_running", "interval_seconds": self._interval_seconds}

        if interval_seconds is not None:
            self._interval_seconds = max(1, int(interval_seconds))

        config = self._load_config()
        preflight = self._live_preflight(config)
        validation_gate = self._validation_gate(config)
        if str(config.mode).lower() == "live" and not preflight.get("passed", False):
            self._last_error = "live preflight failed"
            return {
                "status": "reject_preflight",
                "interval_seconds": self._interval_seconds,
                "preflight": preflight,
            }
        if (
            str(config.mode).lower() == "live"
            and config.validation_gate.enforce_for_live
            and not validation_gate.get("passed", False)
        ):
            self._last_error = "validation gate failed"
            return {
                "status": "reject_validation_gate",
                "interval_seconds": self._interval_seconds,
                "reason": "validation gate failed",
                "validation_gate": validation_gate,
                "preflight": preflight,
            }

        if (
            str(config.mode).lower() == "live"
            and config.live_guard.enabled
            and config.live_guard.require_ack
            and live_confirm_token != config.live_guard.confirm_token
        ):
            self._last_error = "live start token mismatch"
            return {
                "status": "reject_live_ack",
                "interval_seconds": self._interval_seconds,
                "reason": "live confirm token mismatch",
                "preflight": preflight,
            }

        self._is_running = True
        self._stop_event.clear()
        self._started_at = datetime.utcnow().isoformat()
        self._last_error = None
        self._risk_halt_reason = None

        def _loop() -> None:
            while not self._stop_event.is_set():
                try:
                    with self._lock:
                        self._run_once_internal()
                except Exception as exc:
                    self._last_error = str(exc)
                time.sleep(self._interval_seconds)

        self._thread = Thread(target=_loop, name="trading-loop", daemon=True)
        self._thread.start()
        return {
            "status": "started",
            "interval_seconds": self._interval_seconds,
            "preflight": preflight,
            "validation_gate": validation_gate,
        }

    def stop(self) -> Dict[str, Any]:
        if not self._is_running:
            return {"status": "already_stopped"}

        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1)
        self._is_running = False
        return {"status": "stopped"}

    def clear_risk_halt(self, confirm_token: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            previous_reason = self._risk_halt_reason
            lock_state = self._risk_clear_lock_status()
            if previous_reason is None:
                self._risk_clear_failures = 0
                self._risk_clear_locked_until = 0.0
                return {
                    "status": "already_cleared",
                    "previous_reason": previous_reason,
                    "halted": False,
                    "clear_protection": lock_state,
                }

            if lock_state["is_locked"]:
                reject_event_id: Optional[int] = None
                reject_audit_error: Optional[str] = None
                try:
                    reject_event_id = self.journal.record_risk_event(
                        action="risk_halt_clear_reject",
                        previous_reason=previous_reason,
                        current_reason=previous_reason,
                        note="clear_attempt_while_locked",
                    )
                except Exception as exc:
                    reject_audit_error = str(exc)

                return {
                    "status": "reject",
                    "locked": True,
                    "previous_reason": previous_reason,
                    "halted": True,
                    "event_id": reject_event_id,
                    "audit_error": reject_audit_error,
                    "reason": "risk clear is temporarily locked by policy",
                    "clear_protection": lock_state,
                }

            expected_token = _RISK_HALT_CONFIRM_TOKEN
            try:
                expected_token = self.config.risk_guard.confirm_token
            except Exception:
                pass

            if confirm_token != expected_token:
                self._risk_clear_failures += 1
                event_id: Optional[int] = None
                event_error: Optional[str] = None
                try:
                    event_id = self.journal.record_risk_event(
                        action="risk_halt_clear_reject",
                        previous_reason=previous_reason,
                        current_reason=previous_reason,
                        note="confirm_token_mismatch",
                    )
                except Exception as exc:
                    event_error = str(exc)

                max_fail_limit = max(1, int(self.config.risk_guard.clear_fail_limit or 3))
                if self._risk_clear_failures >= max_fail_limit:
                    self._set_risk_clear_lock()
                    self._risk_clear_failures = 0
                    return {
                        "status": "reject",
                        "previous_reason": previous_reason,
                        "halted": True,
                        "event_id": event_id,
                        "audit_error": event_error,
                        "reason": "confirm token mismatch",
                        "clear_protection": self._risk_clear_lock_status(),
                    }

                return {
                    "status": "reject",
                    "previous_reason": previous_reason,
                    "halted": True,
                    "event_id": event_id,
                    "audit_error": event_error,
                    "reason": f"confirm token mismatch ({self._risk_clear_failures}/{max_fail_limit})",
                    "clear_protection": self._risk_clear_lock_status(),
                }

            self._risk_halt_reason = None
            self._risk_clear_failures = 0
            self._risk_clear_locked_until = 0.0
            event_id: Optional[int] = None
            audit_error: Optional[str] = None

            if self._last_error == previous_reason:
                self._last_error = None

            try:
                event_id = self.journal.record_risk_event(
                    action="risk_halt_clear",
                    previous_reason=previous_reason,
                    current_reason=None,
                    note="manual_clear_requested",
                )
            except Exception as exc:
                audit_error = str(exc)

            if isinstance(self._last_summary, dict):
                auto_halt = self._last_summary.get("auto_halt")
                if isinstance(auto_halt, dict):
                    auto_halt["acknowledged"] = True
                    if auto_halt.get("stopped") and previous_reason:
                        auto_halt["status"] = "acknowledged"

            return {
                "status": "cleared",
                "previous_reason": previous_reason,
                "halted": False,
                "event_id": event_id,
                "audit_error": audit_error,
                "clear_protection": self._risk_clear_lock_status(),
            }

    def _public_exchange(self, exchange_cfg: Dict[str, Any]) -> Dict[str, Any]:
        public = dict(exchange_cfg)

        for key in ["api_key", "api_secret", "api_passphrase"]:
            if public.get(key):
                public[key] = _HIDDEN_VALUE

        return public

    def _public_config(self, config: AppConfig) -> Dict[str, Any]:
        data = asdict(config)
        data["exchange"] = self._public_exchange(data["exchange"])
        if isinstance(data.get("notifications"), dict):
            if data["notifications"].get("telegram_bot_token"):
                data["notifications"]["telegram_bot_token"] = _HIDDEN_VALUE
            if data["notifications"].get("telegram_chat_id"):
                data["notifications"]["telegram_chat_id"] = _HIDDEN_VALUE
        if isinstance(data.get("llm"), dict):
            if data["llm"].get("api_key"):
                data["llm"]["api_key"] = _HIDDEN_VALUE
        if isinstance(data.get("live_guard"), dict):
            if data["live_guard"].get("confirm_token"):
                data["live_guard"]["confirm_token"] = _HIDDEN_VALUE
        return data

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            try:
                config = self._load_config()
            except Exception:
                config = self.config

            resolved_reject_thresholds = self._resolve_reject_thresholds()
            balance = self.exchange.get_balance()
            positions = self.exchange.get_open_positions()
            preflight = self._live_preflight(config)
            validation_gate = self._validation_gate(config)
            validation_history = self._validation_history_payload(
                config=config,
                limit=max(1, int(config.validation_gate.history_limit_default or 30)),
            )
            validation_alert_thresholds, validation_alerts = self._build_validation_history_alerts(
                validation_history,
                config,
            )
            return {
                "running": self._is_running,
                "mode": config.mode,
                "interval_seconds": self._interval_seconds,
                "cycle_count": self._cycle_count,
                "started_at": self._started_at,
                "last_error": self._last_error,
                "last_cycle": self._last_summary,
                "balance": balance,
                "positions": positions,
                "exchange": self.exchange.name,
                "allow_live": config.exchange.allow_live,
                "testnet": config.exchange.testnet,
                "journal_path": config.journal.path,
                "live_guard": {
                    "enabled": config.live_guard.enabled,
                    "require_ack": config.live_guard.require_ack,
                    "confirm_token_hint": self._masked_token_hint(config.live_guard.confirm_token),
                },
                "live_staging": (self._last_summary or {}).get("live_staging", {}),
                "execution_guard": (self._last_summary or {}).get("execution_guard", {}),
                "live_preflight": preflight,
                "validation_gate": validation_gate,
                "validation_history": validation_history,
                "validation_alert": {
                    "enabled": bool(config.validation_gate.alert_enabled),
                    "thresholds": validation_alert_thresholds,
                    "alerts": validation_alerts,
                    "last_alert_ts": self._validation_alert_last_sent_at,
                },
                "risk_guard": {
                    "armed": True,
                    "halted": self._risk_halt_reason is not None,
                    "reason": self._risk_halt_reason,
                    "limits": self._risk_limits_state(),
                    "account_state": (self._last_summary or {}).get("account_state", {}),
                    "auto_halt": (self._last_summary or {}).get("auto_halt"),
                    "clear_protection": {
                        "max_failed_attempts": self.config.risk_guard.clear_fail_limit,
                        "lock_duration_seconds": self.config.risk_guard.clear_lock_duration_seconds,
                        "confirm_token_hint": self._masked_token_hint(self.config.risk_guard.confirm_token),
                        "failed_attempts": self._risk_clear_failures,
                        "locked": self._risk_clear_lock_remaining_ms() > 0,
                        "locked_remaining_ms": self._risk_clear_lock_remaining_ms(),
                    },
                },
                "reject_alert": {
                    "enabled": self.config.notifications.enabled,
                    "profile": resolved_reject_thresholds.get("profile", "auto"),
                    "thresholds": resolved_reject_thresholds,
                    "last_alert_ts": self._reject_alert_last_sent_at,
                },
                "auto_learning": self._auto_learning_status(config),
                "config": self._public_config(config),
            }
    def get_risk_events(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.journal.recent_risk_events(limit=limit)

    def get_executions(
        self,
        limit: int = 30,
        status: str | None = None,
        reject_reason: str | None = None,
        is_partial: bool | None = None,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(200, int(limit)))
        return self.journal.execution_summary(
            limit=limit,
            status=status,
            reject_reason=reject_reason,
            is_partial=is_partial,
        )

    def get_reject_reason_metrics(self, limit: int = 200) -> Dict[str, Any]:
        limit = max(1, min(500, int(limit)))
        stats = self.journal.reject_reason_statistics(limit=limit)

        resolved = self._resolve_reject_thresholds()
        thresholds = {
            "profile": resolved.get("profile", "balanced"),
            "warn": float(resolved.get("warn", 0.35)),
            "critical": float(resolved.get("critical", 0.60)),
            "reason_warn": float(resolved.get("reason_warn", 0.30)),
            "reason_critical": float(resolved.get("reason_critical", 0.50)),
            "min_samples": int(resolved.get("min_samples", 20)),
        }

        total_rejected = int(stats.get("rejected_executions", 0) or 0)
        total_executions = int(stats.get("total_executions", 0) or 0)
        reject_rate = float(stats.get("rejected_rate", 0.0) or 0.0)
        reasons: list[Dict[str, Any]] = []
        alerts: list[Dict[str, Any]] = []

        if total_executions >= thresholds["min_samples"]:
            if reject_rate >= thresholds["critical"]:
                alerts.append({
                    "level": "critical",
                    "code": "reject_rate_high",
                    "message": f"최근 실행 {total_executions}건 기준 거부율이 {(reject_rate * 100):.1f}%로 임계치 {thresholds['critical'] * 100:.0f}% 이상입니다.",
                })
            elif reject_rate >= thresholds["warn"]:
                alerts.append({
                    "level": "warn",
                    "code": "reject_rate_high",
                    "message": f"최근 실행 {total_executions}건 기준 거부율이 {(reject_rate * 100):.1f}%로 경고 임계치 {thresholds['warn'] * 100:.0f}% 이상입니다.",
                })
        else:
            alerts.append({
                "level": "info",
                "code": "insufficient_samples",
                "message": f"거부사유 분석은 최소 {thresholds['min_samples']}건 샘플이 필요합니다. 현재 {total_executions}건입니다.",
            })

        for item in stats.get("reasons", []):
            ratio = float(item.get("ratio", 0.0) or 0.0)
            status_level = "ok"
            if total_rejected >= max(1, thresholds["min_samples"]) and ratio >= thresholds["reason_critical"]:
                status_level = "critical"
                alerts.append({
                    "level": "critical",
                    "code": "reject_reason_hotspot",
                    "message": f"거부사유 '{item.get('reason')}'가 {ratio * 100:.1f}%로 집중 발생 ({item.get('count')}건)합니다.",
                })
            elif total_rejected >= max(1, thresholds["min_samples"]) and ratio >= thresholds["reason_warn"]:
                status_level = "warn"
                alerts.append({
                    "level": "warn",
                    "code": "reject_reason_hotspot",
                    "message": f"거부사유 '{item.get('reason')}'가 {ratio * 100:.1f}%로 높습니다 ({item.get('count')}건).",
                })

            reasons.append(
                {
                    "reason": item.get("reason"),
                    "count": int(item.get("count", 0)),
                    "ratio": ratio,
                    "status": status_level,
                }
            )

        reasons.sort(key=lambda x: (x["count"], x["reason"]), reverse=True)
        return {
            "limit": int(limit),
            "total_executions": total_executions,
            "rejected_executions": total_rejected,
            "reject_rate": reject_rate,
            "thresholds": thresholds,
            "reasons": reasons,
            "alerts": alerts,
        }
    def get_config(self) -> Dict[str, Any]:
        return self._public_config(self._load_config())

    def get_learning(self, window_days: int = 14) -> Dict[str, Any]:
        with self._lock:
            config = self._load_config()
            summary = [vars(m) for m in self._learning.summarize(window_days=window_days)]
            tunings = [
                vars(t) for t in self._learning.suggest_tuning(
                    current_strategy_weights=config.strategy_weights(),
                    window_days=window_days,
                )
            ]
            return {
                "window_days": window_days,
                "summary": summary,
                "tuning": tunings,
                "auto_learning": self._auto_learning_status(config),
            }

    def _merge(self, a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(a)
        for key, value in b.items():
            if isinstance(value, dict) and isinstance(out.get(key), dict):
                out[key] = self._merge(out[key], value)
            else:
                out[key] = value
        return out

    def patch_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        current = asdict(self._load_config())
        exchange = payload.get("exchange", {}) if isinstance(payload, dict) else {}
        if isinstance(exchange, dict):
            for key in ["api_key", "api_secret", "api_passphrase"]:
                if exchange.get(key) == _HIDDEN_VALUE:
                    exchange.pop(key)
            if exchange:
                payload = dict(payload)
                payload["exchange"] = exchange

        notifications = payload.get("notifications", {}) if isinstance(payload, dict) else {}
        if isinstance(notifications, dict):
            if notifications.get("telegram_bot_token") == _HIDDEN_VALUE:
                notifications.pop("telegram_bot_token")
            if notifications.get("telegram_chat_id") == _HIDDEN_VALUE:
                notifications.pop("telegram_chat_id")
            if notifications:
                payload = dict(payload)
                payload["notifications"] = notifications
        llm = payload.get("llm", {}) if isinstance(payload, dict) else {}
        if isinstance(llm, dict):
            if llm.get("api_key") == _HIDDEN_VALUE:
                llm.pop("api_key")
            if llm:
                payload = dict(payload)
                payload["llm"] = llm
        live_guard = payload.get("live_guard", {}) if isinstance(payload, dict) else {}
        if isinstance(live_guard, dict):
            if live_guard.get("confirm_token") == _HIDDEN_VALUE:
                live_guard.pop("confirm_token")
            if live_guard:
                payload = dict(payload)
                payload["live_guard"] = live_guard
        merged = self._merge(current, payload)
        merged["mode"] = merged.get("mode", self.config.mode)

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

        self.config = AppConfig.from_file(str(self.config_path))
        self.exchange = build_exchange(self.config.exchange)
        return self._public_config(self.config)

    def apply_learning(
        self,
        window_days: int = 14,
        strategy_filter: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            config = self._load_config()
            if strategy_filter is not None and not isinstance(strategy_filter, list):
                strategy_filter = None

            tunings = self._learning.suggest_tuning(
                current_strategy_weights=config.strategy_weights(),
                window_days=window_days,
            )

            strategy_cfg = dict(config.strategies)
            applied: list[dict[str, Any]] = []

            for item in tunings:
                if strategy_filter and item.strategy not in strategy_filter:
                    continue
                if item.action == "hold":
                    continue

                current = dict(strategy_cfg.get(item.strategy, {})) if isinstance(strategy_cfg.get(item.strategy), dict) else {}
                before_weight = float(current.get("weight", 1.0) or 1.0)
                before_enabled = bool(current.get("enabled", True))
                if item.action == "pause":
                    current["enabled"] = False
                elif item.action in {"increase", "decrease"}:
                    current["enabled"] = True
                    current["weight"] = item.suggested_weight

                strategy_cfg[item.strategy] = current
                applied.append(
                    {
                        "strategy": item.strategy,
                        "action": item.action,
                        "weight_before": before_weight,
                        "weight_after": float(current.get("weight", before_weight) or before_weight),
                        "enabled_before": before_enabled,
                        "enabled_after": bool(current.get("enabled", True)),
                        "confidence": float(getattr(item, "confidence", 0.0) or 0.0),
                        "reason": str(getattr(item, "reason", "") or ""),
                    }
                )

            if not applied:
                result = {"status": "manual_no_change", "applied_count": 0, "applied": []}
                self._auto_learning_last_result = result
                return result

            merged = self._merge(asdict(config), {"strategies": strategy_cfg})
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(merged, f, ensure_ascii=False, indent=2)

            self.config = AppConfig.from_file(str(self.config_path))
            for item in applied:
                try:
                    self.journal.record_auto_learning_event(
                        source="manual",
                        mode=str(config.mode),
                        cycle=int(self._cycle_count),
                        strategy=str(item.get("strategy", "")),
                        action=str(item.get("action", "hold")),
                        weight_before=float(item.get("weight_before", 0.0)),
                        weight_after=float(item.get("weight_after", 0.0)),
                        enabled_after=bool(item.get("enabled_after", True)),
                        confidence=float(item.get("confidence", 0.0)),
                        reason=str(item.get("reason", "")),
                        meta={"window_days": int(window_days)},
                    )
                except Exception:
                    pass
            result = {
                "status": "manual_applied",
                "applied_count": len(applied),
                "applied": applied,
            }
            self._auto_learning_last_result = result
            self._auto_learning_last_applied_cycle = self._cycle_count
            self._auto_learning_last_applied_at = datetime.utcnow().isoformat()
            return result

    def close(self) -> None:
        with self._lock:
            if self._is_running:
                self.stop()
            self.journal.close()

    def get_auto_learning_events(self, limit: int = 100, source: str | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(1000, int(limit)))
        src = source.strip() if isinstance(source, str) else None
        if src == "":
            src = None
        return self.journal.recent_auto_learning_events(limit=limit, source=src)

    def get_validation_history(self, limit: int = 30) -> dict[str, Any]:
        with self._lock:
            config = self._load_config()
            return self._validation_history_payload(config=config, limit=limit)

    def run_live_readiness(self) -> dict[str, Any]:
        with self._lock:
            config = self._load_config()
            preflight = self._live_preflight(config)
            validation_gate = self._validation_gate(config)
            checks: list[dict[str, Any]] = []

            def _add(code: str, required: bool, passed: bool, detail: str, level: str = "info") -> None:
                checks.append(
                    {
                        "code": code,
                        "required": bool(required),
                        "passed": bool(passed),
                        "detail": str(detail),
                        "level": str(level),
                    }
                )

            mode = str(config.mode).strip().lower()
            _add(
                code="mode_live",
                required=False,
                passed=(mode == "live"),
                detail=f"현재 mode={mode}. 실거래 점검은 mode=live 권장",
                level="warn" if mode != "live" else "info",
            )

            preflight_passed = bool(preflight.get("passed", False))
            _add(
                code="live_preflight",
                required=True,
                passed=preflight_passed,
                detail=" / ".join(preflight.get("errors", [])) if not preflight_passed else "ok",
                level="critical" if not preflight_passed else "info",
            )

            gate_required = bool(config.validation_gate.enforce_for_live)
            gate_passed = bool(validation_gate.get("passed", False))
            _add(
                code="validation_gate",
                required=gate_required,
                passed=(gate_passed or not gate_required),
                detail=(
                    " / ".join(validation_gate.get("errors", []))
                    if gate_required and not gate_passed
                    else "ok"
                ),
                level="critical" if gate_required and not gate_passed else "info",
            )

            notify_enabled = bool(config.notifications.enabled)
            has_channel = bool(
                (config.notifications.webhook_url or "").strip()
                or (config.notifications.slack_webhook_url or "").strip()
                or (
                    (config.notifications.telegram_bot_token or "").strip()
                    and (config.notifications.telegram_chat_id or "").strip()
                )
            )
            notify_required = bool(config.live_guard.enforce_notifications)
            notify_passed = (notify_enabled and has_channel) or (not notify_required)
            _add(
                code="notifications",
                required=notify_required,
                passed=notify_passed,
                detail=(
                    "알림 필수인데 채널 설정이 부족합니다."
                    if notify_required and not notify_passed
                    else "ok"
                ),
                level="critical" if notify_required and not notify_passed else "info",
            )

            staging_cfg = config.live_staging
            staging_enabled = bool(staging_cfg.enabled)
            stage_caps_valid = (
                float(staging_cfg.stage1_max_order_usdt) > 0
                and float(staging_cfg.stage2_max_order_usdt) >= float(staging_cfg.stage1_max_order_usdt)
                and float(staging_cfg.stage3_max_order_usdt) >= float(staging_cfg.stage2_max_order_usdt)
            )
            _add(
                code="live_staging_config",
                required=False,
                passed=(stage_caps_valid or not staging_enabled),
                detail=(
                    "live_staging 비활성"
                    if not staging_enabled
                    else (
                        "ok"
                        if stage_caps_valid
                        else "stage cap 설정이 잘못되었습니다(stage1<=stage2<=stage3 필요)"
                    )
                ),
                level="warn" if staging_enabled and not stage_caps_valid else "info",
            )

            exchange_name = str(config.exchange.type)
            exchange_balance: dict[str, Any] = {}
            exchange_error = ""
            exchange_connect_ok = False
            try:
                temp_exchange = build_exchange(config.exchange)
                exchange_name = temp_exchange.name
                bal = temp_exchange.get_balance()
                exchange_balance = {
                    "USDT": bal.get("USDT"),
                    "equity_usdt": bal.get("equity_usdt"),
                    "position_count": bal.get("position_count"),
                }
                exchange_connect_ok = True
            except Exception as exc:
                exchange_error = str(exc)

            _add(
                code="exchange_connectivity",
                required=True,
                passed=exchange_connect_ok,
                detail=exchange_error if not exchange_connect_ok else f"ok ({exchange_name})",
                level="critical" if not exchange_connect_ok else "info",
            )

            symbol = ""
            price_ok = False
            price_error = ""
            if exchange_connect_ok:
                try:
                    symbol = (config.pipeline.universe[0] if config.pipeline.universe else "").strip() or "BTC/USDT"
                    probe_exchange = build_exchange(config.exchange)
                    probe_price = float(probe_exchange.get_last_price(symbol))
                    price_ok = probe_price > 0
                    if not price_ok:
                        price_error = f"invalid price={probe_price}"
                except Exception as exc:
                    price_error = str(exc)
            _add(
                code="exchange_price_probe",
                required=True,
                passed=price_ok,
                detail=(f"{symbol} price ok" if price_ok else f"{symbol} probe failed: {price_error}"),
                level="critical" if not price_ok else "info",
            )

            required_failed = [item for item in checks if item["required"] and not item["passed"]]
            overall_passed = len(required_failed) == 0
            return {
                "overall_passed": overall_passed,
                "mode": config.mode,
                "exchange": exchange_name,
                "exchange_balance_preview": exchange_balance,
                "checks": checks,
                "blocking_failures": required_failed,
                "preflight": preflight,
                "validation_gate": validation_gate,
                "timestamp": datetime.utcnow().isoformat(),
            }

    def save_live_readiness_report(self, output_path: str | None = None) -> dict[str, Any]:
        report = self.run_live_readiness()
        raw = str(output_path or "").strip()
        if raw:
            out = Path(raw)
            if not out.is_absolute():
                out = (self.config_path.parent / out).resolve()
        else:
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            out_dir = (self.config_path.parent / "data" / "validation" / "live_readiness").resolve()
            out = out_dir / f"live_readiness_{ts}.json"

        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "status": "saved",
            "report_path": str(out),
            "report": report,
        }

    def run_exchange_probe(self, symbols: list[str] | None = None) -> dict[str, Any]:
        with self._lock:
            config = self._load_config()

        checks: list[dict[str, Any]] = []
        warnings: list[str] = []
        symbol_rows: list[dict[str, Any]] = []
        exchange_info: dict[str, Any] = {
            "type": str(config.exchange.type),
            "mode": str(config.mode),
            "allow_live": bool(config.exchange.allow_live),
            "testnet": bool(config.exchange.testnet),
        }

        def _add(code: str, required: bool, passed: bool, detail: str, level: str = "info") -> None:
            checks.append(
                {
                    "code": code,
                    "required": bool(required),
                    "passed": bool(passed),
                    "detail": str(detail),
                    "level": str(level),
                }
            )

        def _f(v: Any, default: float = 0.0) -> float:
            try:
                return float(v)
            except Exception:
                return float(default)

        target_symbols = [str(x).strip().upper() for x in (symbols or config.pipeline.universe or []) if str(x).strip()]
        if not target_symbols:
            target_symbols = ["BTCUSDT", "ETHUSDT"]
        target_symbols = target_symbols[:30]

        temp_exchange = None
        try:
            temp_exchange = build_exchange(config.exchange)
            exchange_info["name"] = getattr(temp_exchange, "name", str(config.exchange.type))
            _add("build_exchange", True, True, f"name={exchange_info['name']}", "info")
        except Exception as exc:
            _add("build_exchange", True, False, str(exc), "critical")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_passed": False,
                "checks": checks,
                "warnings": warnings,
                "symbols": symbol_rows,
                "exchange": exchange_info,
            }

        try:
            bal = temp_exchange.get_balance()
            exchange_info["balance"] = {
                "USDT": bal.get("USDT"),
                "equity_usdt": bal.get("equity_usdt"),
                "position_count": bal.get("position_count"),
            }
            _add("fetch_balance", True, True, "balance fetch ok", "info")
        except Exception as exc:
            _add("fetch_balance", True, False, str(exc), "critical")

        raw = getattr(temp_exchange, "_exchange", None)
        is_ccxt = raw is not None
        _add(
            "ccxt_adapter",
            True,
            is_ccxt,
            "ccxt adapter connected" if is_ccxt else "paper/mock adapter: exchange param probe limited",
            "info" if is_ccxt else "warn",
        )

        if is_ccxt:
            markets_loaded = False
            try:
                if hasattr(raw, "load_markets"):
                    raw.load_markets()
                markets_loaded = True
                _add("load_markets", True, True, "markets loaded", "info")
            except Exception as exc:
                _add("load_markets", True, False, str(exc), "critical")

            has = getattr(raw, "has", {}) or {}
            create_order_ok = bool(has.get("createOrder"))
            fetch_positions_ok = bool(has.get("fetchPositions")) or bool(has.get("fetchPosition"))
            set_leverage_ok = bool(has.get("setLeverage"))
            set_position_mode_ok = bool(has.get("setPositionMode"))
            _add("cap_create_order", True, create_order_ok, f"has.createOrder={create_order_ok}", "info" if create_order_ok else "warn")
            _add("cap_fetch_positions", False, fetch_positions_ok, f"has.fetchPositions={fetch_positions_ok}", "info" if fetch_positions_ok else "warn")
            _add("cap_set_leverage", False, set_leverage_ok, f"has.setLeverage={set_leverage_ok}", "info" if set_leverage_ok else "warn")
            _add("cap_set_position_mode", False, set_position_mode_ok, f"has.setPositionMode={set_position_mode_ok}", "info" if set_position_mode_ok else "warn")

            if markets_loaded:
                markets = getattr(raw, "markets", {}) or {}
                for symbol in target_symbols:
                    row: dict[str, Any] = {
                        "symbol": symbol,
                        "exists": False,
                        "active": False,
                        "linear": None,
                        "inverse": None,
                        "quote": "",
                        "contract": None,
                        "contract_size": None,
                        "amount_precision": None,
                        "price_precision": None,
                        "min_amount": None,
                        "min_notional": None,
                        "sample_amount_precision_ok": None,
                    }
                    market = markets.get(symbol)
                    if not isinstance(market, dict):
                        row["error"] = "market not found"
                        warnings.append(f"{symbol}: market not found")
                        symbol_rows.append(row)
                        continue

                    precision = market.get("precision", {}) or {}
                    limits = market.get("limits", {}) or {}
                    amount_limit = (limits.get("amount", {}) or {})
                    cost_limit = (limits.get("cost", {}) or {})
                    row["exists"] = True
                    row["active"] = bool(market.get("active", True))
                    row["linear"] = market.get("linear")
                    row["inverse"] = market.get("inverse")
                    row["quote"] = str(market.get("quote") or "")
                    row["contract"] = market.get("contract")
                    row["contract_size"] = market.get("contractSize")
                    row["amount_precision"] = precision.get("amount")
                    row["price_precision"] = precision.get("price")
                    row["min_amount"] = amount_limit.get("min")
                    row["min_notional"] = cost_limit.get("min")

                    try:
                        if hasattr(raw, "amount_to_precision"):
                            sample = max(_f(row["min_amount"], 0.001), 0.001)
                            raw.amount_to_precision(symbol, sample)
                            row["sample_amount_precision_ok"] = True
                        else:
                            row["sample_amount_precision_ok"] = False
                    except Exception:
                        row["sample_amount_precision_ok"] = False
                        warnings.append(f"{symbol}: amount_to_precision failed")

                    if not row["active"]:
                        warnings.append(f"{symbol}: inactive market")
                    if str(row["quote"] or "").upper() != "USDT":
                        warnings.append(f"{symbol}: quote={row['quote']} (USDT 권장)")
                    if row["amount_precision"] is None:
                        warnings.append(f"{symbol}: amount precision missing")
                    if _f(row["min_notional"], 0.0) <= 0:
                        warnings.append(f"{symbol}: min_notional missing")

                    symbol_rows.append(row)

        required_checks = [item for item in checks if bool(item.get("required"))]
        overall_passed = all(bool(item.get("passed")) for item in required_checks) if required_checks else True
        critical_count = sum(1 for item in checks if str(item.get("level", "")).lower() == "critical" and not bool(item.get("passed")))

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_passed": bool(overall_passed),
            "critical_failures": int(critical_count),
            "checks": checks,
            "warnings": warnings[:80],
            "symbols": symbol_rows,
            "exchange": exchange_info,
        }

    def save_exchange_probe_report(self, output_path: str | None = None, symbols: list[str] | None = None) -> dict[str, Any]:
        report = self.run_exchange_probe(symbols=symbols)
        raw = str(output_path or "").strip()
        if raw:
            out = Path(raw)
            if not out.is_absolute():
                out = (self.config_path.parent / out).resolve()
        else:
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            out_dir = (self.config_path.parent / "data" / "validation" / "exchange_probe").resolve()
            out = out_dir / f"exchange_probe_{ts}.json"

        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "status": "saved",
            "report_path": str(out),
            "report": report,
        }

    def test_llm_connection(self, sample_symbol: str = "BTCUSDT") -> dict[str, Any]:
        with self._lock:
            config = self._load_config()
        llm_cfg = config.llm

        api_key_source = "none"
        if str(llm_cfg.api_key or "").strip():
            api_key_source = "config"
        elif str(llm_cfg.api_key_env or "").strip():
            api_key_source = f"env:{llm_cfg.api_key_env}"

        advisor = LLMAdvisor(
            enabled=bool(llm_cfg.enabled),
            provider=llm_cfg.provider,
            api_key=llm_cfg.api_key,
            api_key_env=llm_cfg.api_key_env,
            api_base_url=llm_cfg.api_base_url,
            model=llm_cfg.model,
            temperature=llm_cfg.temperature,
            timeout_seconds=llm_cfg.timeout_seconds,
            max_retries=llm_cfg.max_retries,
            retry_delay_ms=llm_cfg.retry_delay_ms,
            max_tokens=llm_cfg.max_tokens,
            score_scale=llm_cfg.score_scale,
            score_candidates_limit=llm_cfg.score_candidates_limit,
            request_mode=llm_cfg.request_mode,
        )

        if not llm_cfg.enabled:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "enabled": False,
                "provider": llm_cfg.provider,
                "request_mode": llm_cfg.request_mode,
                "model": llm_cfg.model,
                "api_base_url": llm_cfg.api_base_url,
                "api_key_source": api_key_source,
                "status": "disabled",
                "passed": False,
                "message": "llm.enabled=false (설정에서 활성화 필요)",
                "metadata": advisor.get_last_metadata(),
                "sample_scores": {},
            }

        symbol = str(sample_symbol or "BTCUSDT").strip().upper() or "BTCUSDT"
        candidates = [
            {
                "id": f"{symbol}_long",
                "symbol": symbol,
                "direction": "BUY",
                "confidence": 0.71,
                "expected_edge_bps": 14.0,
                "base_score": 62.0,
                "regime_confidence": 0.68,
            },
            {
                "id": f"{symbol}_short",
                "symbol": symbol,
                "direction": "SELL",
                "confidence": 0.56,
                "expected_edge_bps": 7.0,
                "base_score": 48.0,
                "regime_confidence": 0.54,
            },
        ]
        context = {
            "mode": str(config.mode),
            "timestamp": datetime.utcnow().isoformat(),
            "purpose": "connection_test",
        }

        scores = advisor.score_candidates(candidates, context=context)
        meta = advisor.get_last_metadata()
        status = str(meta.get("status", "unknown"))
        passed = bool(scores) and status in {"ok", "mock"}

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "enabled": bool(llm_cfg.enabled),
            "provider": llm_cfg.provider,
            "request_mode": llm_cfg.request_mode,
            "model": llm_cfg.model,
            "api_base_url": llm_cfg.api_base_url,
            "api_key_source": api_key_source,
            "status": status,
            "passed": passed,
            "scored_count": len(scores),
            "metadata": meta,
            "sample_scores": scores,
        }

    def trigger_validation_alert_test(self, level: str = "warn") -> dict[str, Any]:
        with self._lock:
            config = self._load_config()
            lv = str(level or "warn").strip().lower()
            if lv not in {"info", "warn", "critical"}:
                lv = "warn"

            history = self._validation_history_payload(
                config=config,
                limit=max(1, int(config.validation_gate.history_limit_default or 30)),
            )
            thresholds = self._validation_alert_thresholds(config)
            if not bool(config.notifications.enabled):
                return {
                    "status": "skipped",
                    "reason": "notifications disabled",
                    "level": lv,
                    "history_total_runs": int(history.get("total_runs", 0) or 0),
                }

            sent = self._send_validation_alert_notifications(
                history=history,
                thresholds=thresholds,
                alerts=[
                    {
                        "level": lv,
                        "code": "validation_alert_test",
                        "message": f"검증 알람 테스트({lv}) - 채널 연결 점검",
                    }
                ],
                force=True,
            )
            return {
                "status": "sent" if sent else "failed",
                "level": lv,
                "force": True,
                "history_total_runs": int(history.get("total_runs", 0) or 0),
                "thresholds": thresholds,
            }













