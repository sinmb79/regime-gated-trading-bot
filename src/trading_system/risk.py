from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List

from .domain import MarketRegime, RegimeType, RiskDecision, StrategySignal


@dataclass
class AccountState:
    cash_usdt: float
    equity_usdt: float
    open_positions: Dict[str, float]
    last_trade_by_symbol: Dict[str, datetime] = field(default_factory=dict)
    today_pnl: float = 0.0
    today_trades: int = 0
    consecutive_loss_count: int = 0
    last_trade_at: datetime | None = None


class RiskEngine:
    def __init__(
        self,
        daily_max_loss_pct: float,
        max_total_exposure: float,
        max_symbol_exposure: float,
        max_open_positions: int,
        max_daily_trades: int,
        max_leverage: float,
        min_signal_confidence: float,
        max_slippage_bps: float,
        min_expectancy_pct: float,
        cooldown_minutes: int,
        max_consecutive_losses: int = 3,
        max_reject_ratio: float = 0.85,
    ):
        self.daily_max_loss_pct = daily_max_loss_pct
        self.max_total_exposure = max_total_exposure
        self.max_symbol_exposure = max_symbol_exposure
        self.max_open_positions = max_open_positions
        self.max_daily_trades = max_daily_trades
        self.max_leverage = max_leverage
        self.min_signal_confidence = min_signal_confidence
        self.max_slippage_bps = max_slippage_bps
        self.min_expectancy_pct = min_expectancy_pct
        self.cooldown_minutes = cooldown_minutes
        self.max_consecutive_losses = max_consecutive_losses
        self.max_reject_ratio = max_reject_ratio

    def evaluate(
        self,
        signal: StrategySignal,
        regime: MarketRegime,
        account: AccountState,
    ) -> RiskDecision:
        reasons: List[str] = []

        if account.today_pnl <= -abs(account.equity_usdt * self.daily_max_loss_pct):
            reasons.append("daily_loss_limit_reached")

        if account.consecutive_loss_count >= self.max_consecutive_losses:
            reasons.append("consecutive_loss_limit")

        if signal.confidence < self.min_signal_confidence:
            reasons.append("low_signal_confidence")

        if signal.slippage_estimate_bps > self.max_slippage_bps:
            reasons.append("slippage_too_high")

        if signal.leverage > self.max_leverage:
            reasons.append("leverage_over_limit")

        if signal.direction == "HOLD":
            reasons.append("no_direction")

        if regime.regime == RegimeType.PANIC:
            reasons.append("panic_regime_block")

        if account.today_trades >= self.max_daily_trades:
            reasons.append("daily_trade_count_limit")

        cooldown_anchor = account.last_trade_by_symbol.get(signal.symbol) or account.last_trade_at
        if cooldown_anchor and self.cooldown_minutes > 0:
            now_ts = signal.timestamp if isinstance(signal.timestamp, datetime) else datetime.utcnow()
            if now_ts - cooldown_anchor < timedelta(minutes=self.cooldown_minutes):
                reasons.append("cooldown_time")

        total_exposure = sum(abs(x) for x in account.open_positions.values())
        equity_base = max(account.equity_usdt, 1.0)
        if total_exposure / equity_base > self.max_total_exposure:
            reasons.append("total_exposure_limit")

        symbol_exposure = abs(account.open_positions.get(signal.symbol, 0.0))
        if symbol_exposure / equity_base > self.max_symbol_exposure:
            reasons.append("symbol_exposure_limit")

        if len(account.open_positions) >= self.max_open_positions and signal.symbol not in account.open_positions:
            reasons.append("position_count_limit")

        if signal.expected_edge_bps < self.min_expectancy_pct * 100:
            reasons.append("expectancy_too_low")

        kalman_shock = abs(float(signal.meta.get("kalman_innovation_z", 0.0) or 0.0))
        if kalman_shock > 4.5:
            reasons.append("kalman_shock_block")

        if signal.meta.get("volatility", 0.0) > 0.12:
            reasons.append("high_volatility_cut")

        allowed = not reasons
        adjusted_ratio = signal.position_size_ratio

        if account.consecutive_loss_count >= 2:
            adjusted_ratio *= 0.7
        if signal.meta.get("volatility", 0.0) > 0.07 and signal.meta.get("volatility", 0.0) <= 0.12:
            adjusted_ratio *= 0.9
        if account.today_pnl < 0 and account.consecutive_loss_count >= 1:
            adjusted_ratio *= 0.9
        if kalman_shock > 3.0:
            adjusted_ratio *= 0.85

        return RiskDecision(
            allowed=allowed,
            reasons=reasons,
            adjusted_position_ratio=max(0.0, adjusted_ratio),
            adjusted_leverage=min(signal.leverage, self.max_leverage),
        )
