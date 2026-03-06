from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class PipelineConfig:
    universe: List[str] = field(default_factory=list)
    scan_limit: int = 20
    candidate_count: int = 2
    symbols_to_scan: int = 20
    max_cycles: int = 1


@dataclass(frozen=True)
class RiskLimitConfig:
    daily_max_loss_pct: float = 0.04
    max_total_exposure: float = 0.45
    max_symbol_exposure: float = 0.18
    max_open_positions: int = 3
    max_daily_trades: int = 20
    max_leverage: float = 5.0
    min_signal_confidence: float = 0.58
    max_slippage_bps: float = 35.0
    min_expectancy_pct: float = 0.05
    cooldown_minutes: int = 10
    max_consecutive_losses: int = 3
    max_reject_ratio: float = 0.85
    reject_rate_warn: float = 0.35
    reject_rate_critical: float = 0.60
    reject_reason_rate_warn: float = 0.30
    reject_reason_rate_critical: float = 0.50
    reject_reason_min_samples: int = 20
    reject_alert_profile: str = "auto"


@dataclass(frozen=True)
class RiskGuardConfig:
    clear_fail_limit: int = 3
    clear_lock_duration_seconds: int = 30
    confirm_token: str = "UNHALT"


@dataclass(frozen=True)
class LiveGuardConfig:
    enabled: bool = True
    require_ack: bool = True
    confirm_token: str = "LIVE_OK"
    enforce_notifications: bool = True
    max_daily_loss_hard_limit_pct: float = 0.10
    max_total_exposure_hard_limit: float = 0.90
    max_leverage_hard_limit: float = 10.0


@dataclass(frozen=True)
class ExecutionConfig:
    default_position_fraction: float = 0.06
    maker_fee_bps: float = 2.0
    taker_fee_bps: float = 4.0
    default_leverage: float = 2.0
    order_retries: int = 2
    retry_base_wait_ms: int = 300
    partial_fill_min_ratio: float = 0.55


@dataclass(frozen=True)
class ExchangeConfig:
    type: str = "paper"
    initial_cash_usdt: float = 10000.0
    base_currency: str = "USDT"
    api_key: str = ""
    api_secret: str = ""
    api_passphrase: str = ""
    api_key_env: str = ""
    api_secret_env: str = ""
    api_passphrase_env: str = ""
    testnet: bool = True
    allow_live: bool = False
    partial_fill_probability: float = 0.0
    partial_fill_min_ratio: float = 0.55
    partial_fill_max_ratio: float = 0.95



@dataclass(frozen=True)
class LLMConfig:
    enabled: bool = False
    provider: str = "mock"
    api_key: str = ""
    api_key_env: str = "OPENAI_API_KEY"
    api_base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    temperature: float = 0.2
    timeout_seconds: int = 12
    max_retries: int = 1
    retry_delay_ms: int = 250
    max_tokens: int = 256
    score_scale: float = 10.0
    score_candidates_limit: int = 30
    request_mode: str = "openai"


@dataclass(frozen=True)
class JournalConfig:
    path: str = "data/trading_journal.sqlite"


@dataclass(frozen=True)
class NotificationConfig:
    enabled: bool = False
    send_on_levels: list[str] = field(default_factory=lambda: ["critical", "warn"])
    cooldown_seconds: int = 900
    max_per_hour: int = 0
    webhook_url: str = ""
    slack_webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    include_reject_summary: bool = True


@dataclass(frozen=True)
class ValidationGateConfig:
    enforce_for_live: bool = True
    enforce_for_auto_learning: bool = True
    report_path: str = "data/validation/latest_validation_report.json"
    history_path: str = "data/validation/validation_history.jsonl"
    allow_bypass: bool = False
    bypass: bool = False
    history_limit_default: int = 30
    require_overall_passed: bool = True
    max_report_age_days: int = 14
    alert_enabled: bool = True
    alert_min_samples: int = 5
    alert_pass_rate_warn: float = 0.60
    alert_pass_rate_critical: float = 0.40
    alert_max_drawdown_warn: float = 0.25
    alert_max_drawdown_critical: float = 0.35


@dataclass(frozen=True)
class LiveStagingConfig:
    enabled: bool = True
    stage1_max_order_usdt: float = 50.0
    stage1_trade_count: int = 10
    stage2_max_order_usdt: float = 150.0
    stage2_trade_count: int = 20
    stage3_max_order_usdt: float = 400.0
    block_on_daily_loss_usdt: float = 150.0
    require_non_negative_pnl_for_promotion: bool = True


@dataclass(frozen=True)
class AutoLearningConfig:
    enabled: bool = False
    paper_only: bool = True
    apply_mode: str = "manual_approval"
    apply_interval_cycles: int = 20
    window_days: int = 14
    min_trades_per_strategy: int = 8
    min_confidence: float = 0.62
    max_weight_step_pct: float = 0.20
    max_strategy_changes_per_apply: int = 3
    max_applies_per_day: int = 8
    allow_pause: bool = False
    max_pending_proposals: int = 100
    proposal_expiry_hours: int = 72


@dataclass(frozen=True)
class AppConfig:
    mode: str
    pipeline: PipelineConfig
    risk_limits: RiskLimitConfig
    risk_guard: RiskGuardConfig
    live_guard: LiveGuardConfig
    live_staging: LiveStagingConfig
    execution: ExecutionConfig
    exchange: ExchangeConfig
    strategies: Dict[str, Dict[str, Any]]
    llm: LLMConfig
    journal: JournalConfig
    notifications: NotificationConfig
    validation_gate: ValidationGateConfig
    auto_learning: AutoLearningConfig

    @staticmethod
    def _dict_to_dataclass(cls_type, raw: Dict[str, Any]):
        return cls_type(**raw)

    @staticmethod
    def _with_defaults(cls_type, raw: Dict[str, Any]):
        default = asdict(cls_type())
        merged = default | raw
        return cls_type(**merged)

    @classmethod
    def from_file(cls, path: str | Path) -> "AppConfig":
        raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))

        return cls(
            mode=raw.get("mode", "dry"),
            pipeline=cls._with_defaults(PipelineConfig, raw.get("pipeline", {})),
            risk_limits=cls._with_defaults(RiskLimitConfig, raw.get("risk_limits", {})),
            risk_guard=cls._with_defaults(RiskGuardConfig, raw.get("risk_guard", {})),
            live_guard=cls._with_defaults(LiveGuardConfig, raw.get("live_guard", {})),
            live_staging=cls._with_defaults(LiveStagingConfig, raw.get("live_staging", {})),
            execution=cls._with_defaults(ExecutionConfig, raw.get("execution", {})),
            exchange=cls._with_defaults(ExchangeConfig, raw.get("exchange", {})),
            strategies=raw.get("strategies", {}),
            llm=cls._with_defaults(LLMConfig, raw.get("llm", {})),
            journal=cls._with_defaults(JournalConfig, raw.get("journal", {})),
            notifications=cls._with_defaults(NotificationConfig, raw.get("notifications", {})),
            validation_gate=cls._with_defaults(ValidationGateConfig, raw.get("validation_gate", {})),
            auto_learning=cls._with_defaults(AutoLearningConfig, raw.get("auto_learning", {})),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def with_mode(self, mode: str) -> "AppConfig":
        return AppConfig(
            mode=mode,
            pipeline=self.pipeline,
            risk_limits=self.risk_limits,
            risk_guard=self.risk_guard,
            live_guard=self.live_guard,
            live_staging=self.live_staging,
            execution=self.execution,
            exchange=self.exchange,
            strategies=self.strategies,
            llm=self.llm,
            journal=self.journal,
            notifications=self.notifications,
            validation_gate=self.validation_gate,
            auto_learning=self.auto_learning,
        )

    def strategy_weights(self) -> Dict[str, float]:
        weights: Dict[str, float] = {}
        for key, cfg in self.strategies.items():
            if not isinstance(cfg, dict):
                continue
            weight = cfg.get("weight")
            if isinstance(weight, (int, float)):
                weights[key] = float(weight)
            else:
                weights[key] = 1.0
        return weights







