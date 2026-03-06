from __future__ import annotations

from typing import List

from ..domain import MarketRegime, MarketSnapshot, SignalDirection, StrategySignal
from .base import TradingStrategy


class TrendStrategy(TradingStrategy):
    id = "trend"
    name = "Trend Momentum"
    supported_regimes = ["trend_up", "trend_down"]

    def generate(self, snapshot: MarketSnapshot, regime: MarketRegime) -> List[StrategySignal]:
        if not self._allowed(regime):
            return []
        kalman = self._kalman_features(snapshot)
        k_trend = float(kalman["trend_score"])
        k_shock = abs(float(kalman["innovation_z"]))

        if regime.regime.value == "trend_up" and snapshot.momentum_7d > 0:
            if k_trend < -0.35:
                return []
            direction = SignalDirection.BUY
            edge = 26 + snapshot.momentum_7d * 1200 + max(0.0, k_trend) * 12 - min(10.0, k_shock * 2.2)
            confidence = min(0.95, max(0.3, regime.confidence + 0.18 + max(0.0, k_trend) * 0.08 - min(0.08, k_shock * 0.01)))
        elif regime.regime.value == "trend_down" and snapshot.momentum_7d < 0:
            if k_trend > 0.35:
                return []
            direction = SignalDirection.SELL
            edge = 22 + abs(snapshot.momentum_7d) * 1200 + max(0.0, -k_trend) * 12 - min(10.0, k_shock * 2.2)
            confidence = min(0.95, max(0.3, regime.confidence + 0.14 + max(0.0, -k_trend) * 0.08 - min(0.08, k_shock * 0.01)))
        else:
            return []
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
                slippage_estimate_bps=snapshot.spread_bps,
                position_size_ratio=0.08 * self.weight,
                leverage=2.0,
                stop_loss_pct=0.01,
                take_profit_pct=0.02,
                comment="trend_following",
                meta={
                    "momentum": snapshot.momentum_7d,
                    "regime": regime.regime.value,
                    "kalman_trend_score": k_trend,
                    "kalman_innovation_z": kalman["innovation_z"],
                    "kalman_uncertainty": kalman["uncertainty"],
                },
            )
        ]
