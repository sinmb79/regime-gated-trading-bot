from __future__ import annotations

from typing import List

from ..domain import MarketRegime, MarketSnapshot, SignalDirection, StrategySignal
from .base import TradingStrategy


class FundingArbStrategy(TradingStrategy):
    id = "funding_arb"
    name = "Funding Arb"
    supported_regimes = ["trend_up", "trend_down", "range"]

    def generate(self, snapshot: MarketSnapshot, regime: MarketRegime) -> List[StrategySignal]:
        if not self._allowed(regime):
            return []
        kalman = self._kalman_features(snapshot)
        k_trend = float(kalman["trend_score"])
        k_shock = abs(float(kalman["innovation_z"]))

        # Simplified sample logic:
        # positive funding may encourage SHORT to collect premium,
        # negative funding may encourage LONG.
        if abs(snapshot.funding_rate) < 0.003:
            return []

        direction = SignalDirection.SELL if snapshot.funding_rate > 0 else SignalDirection.BUY
        if direction == SignalDirection.SELL and k_trend > 0.60:
            return []
        if direction == SignalDirection.BUY and k_trend < -0.60:
            return []

        align = max(0.0, -k_trend) if direction == SignalDirection.SELL else max(0.0, k_trend)
        edge = abs(snapshot.funding_rate) * 3000 + align * 10 - min(12.0, k_shock * 1.8)
        confidence = min(0.76, 0.45 + abs(snapshot.funding_rate) * 50 + align * 0.08 - min(0.06, k_shock * 0.01))
        if snapshot.volatility > 0.05:
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
                slippage_estimate_bps=snapshot.spread_bps * 1.1,
                position_size_ratio=0.04 * self.weight,
                leverage=2.0,
                stop_loss_pct=0.004,
                take_profit_pct=0.008,
                comment="funding_arb_small_leverage",
                meta={
                    "funding_rate": snapshot.funding_rate,
                    "volatility": snapshot.volatility,
                    "kalman_trend_score": k_trend,
                    "kalman_innovation_z": kalman["innovation_z"],
                    "kalman_uncertainty": kalman["uncertainty"],
                },
            )
        ]
