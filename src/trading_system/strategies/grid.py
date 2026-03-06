from __future__ import annotations

from typing import List

from ..domain import MarketRegime, MarketSnapshot, SignalDirection, StrategySignal
from .base import TradingStrategy


class GridStrategy(TradingStrategy):
    id = "grid"
    name = "Grid"
    supported_regimes = ["range", "trend_up", "trend_down"]

    def generate(self, snapshot: MarketSnapshot, regime: MarketRegime) -> List[StrategySignal]:
        if not self._allowed(regime):
            return []
        if snapshot.volatility > 0.03:
            return []
        kalman = self._kalman_features(snapshot)
        k_trend = abs(float(kalman["trend_score"]))
        k_shock = abs(float(kalman["innovation_z"]))
        if k_trend > 0.55 or k_shock > 3.5:
            return []

        direction = SignalDirection.BUY if snapshot.momentum_7d >= 0 else SignalDirection.SELL
        confidence = min(0.88, 0.56 + (0.03 - snapshot.volatility) * 10 + (1 - snapshot.spread_bps / 120) + (0.55 - k_trend) * 0.06)
        edge = 16 + (0.02 - snapshot.volatility) * 280 + max(0.0, (0.5 - k_trend) * 8) - min(8.0, k_shock * 1.4)
        if edge <= 0:
            return []

        return [
            StrategySignal(
                strategy_id=self.id,
                symbol=snapshot.symbol,
                timestamp=snapshot.timestamp,
                direction=direction,
                confidence=max(0.05, confidence),
                expected_edge_bps=edge,
                slippage_estimate_bps=snapshot.spread_bps,
                position_size_ratio=0.06 * self.weight,
                leverage=1.0,
                stop_loss_pct=0.008,
                take_profit_pct=0.012,
                comment="grid_range_strategy",
                meta={
                    "volatility": snapshot.volatility,
                    "regime": regime.regime.value,
                    "momentum": snapshot.momentum_7d,
                    "kalman_trend_score": kalman["trend_score"],
                    "kalman_innovation_z": kalman["innovation_z"],
                    "kalman_uncertainty": kalman["uncertainty"],
                },
            )
        ]
