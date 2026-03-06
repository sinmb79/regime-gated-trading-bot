from __future__ import annotations

from typing import List

from ..domain import MarketRegime, MarketSnapshot, SignalDirection, StrategySignal
from .base import TradingStrategy


class DefensiveStrategy(TradingStrategy):
    id = "defensive"
    name = "Defensive Low Frequency"
    supported_regimes = ["trend_up", "trend_down", "range"]

    def generate(self, snapshot: MarketSnapshot, regime: MarketRegime) -> List[StrategySignal]:
        # only use when market is not panicked and volatility moderate
        if not self._allowed(regime) or snapshot.volatility > 0.025:
            return []
        kalman = self._kalman_features(snapshot)
        k_trend = float(kalman["trend_score"])
        k_shock = abs(float(kalman["innovation_z"]))
        k_uncertainty = float(kalman["uncertainty"])
        if k_shock > 4.5:
            return []

        # low confidence long/short depending on very weak momentum.
        if abs(snapshot.momentum_7d) < 0.003:
            return []

        direction = SignalDirection.BUY if snapshot.momentum_7d > 0 else SignalDirection.SELL
        align = max(0.0, k_trend) if direction == SignalDirection.BUY else max(0.0, -k_trend)
        edge = 10 + abs(snapshot.momentum_7d) * 950 + align * 6 - min(6.0, k_shock * 1.2)
        confidence = min(
            0.78,
            0.5
            + abs(snapshot.momentum_7d) * 180
            + (1.0 - regime.confidence) * 0.1
            + align * 0.06
            - min(0.06, k_uncertainty * 0.6),
        )
        if edge <= 0:
            return []

        return [
            StrategySignal(
                strategy_id=self.id,
                symbol=snapshot.symbol,
                timestamp=snapshot.timestamp,
                direction=direction,
                confidence=confidence,
                expected_edge_bps=edge,
                slippage_estimate_bps=snapshot.spread_bps * 0.8,
                position_size_ratio=0.045 * self.weight,
                leverage=1.5,
                stop_loss_pct=0.006,
                take_profit_pct=0.012,
                comment="defensive_reversion",
                meta={
                    "volatility": snapshot.volatility,
                    "spread_bps": snapshot.spread_bps,
                    "momentum": snapshot.momentum_7d,
                    "regime": regime.regime.value,
                    "kalman_trend_score": k_trend,
                    "kalman_innovation_z": kalman["innovation_z"],
                    "kalman_uncertainty": k_uncertainty,
                },
            )
        ]
