from __future__ import annotations

from typing import List

from ..domain import MarketRegime, MarketSnapshot, SignalDirection, StrategySignal
from .base import TradingStrategy


class BollingerReversionStrategy(TradingStrategy):
    id = "bollinger_reversion"
    name = "Bollinger Mean Reversion"
    supported_regimes = ["range", "trend_up", "trend_down"]

    def generate(self, snapshot: MarketSnapshot, regime: MarketRegime) -> List[StrategySignal]:
        if not self._allowed(regime):
            return []
        kalman = self._kalman_features(snapshot)
        k_trend = abs(float(kalman["trend_score"]))
        k_innov = float(kalman["innovation_z"])

        z_score = float(snapshot.features.get("bb_z", 0.0))
        width = float(snapshot.features.get("bb_width_ratio", 0.0))

        if abs(width) > float(self.cfg.get("max_bb_width_ratio", 0.08)):
            return []

        threshold = float(self.cfg.get("z_entry_threshold", 1.45))
        if abs(z_score) < threshold:
            return []

        if abs(snapshot.momentum_7d) > float(self.cfg.get("momentum_filter", 0.018)):
            return []
        if k_trend > 0.75:
            return []

        direction = SignalDirection.BUY if z_score < 0 else SignalDirection.SELL
        kalman_align = 1.0 if (direction == SignalDirection.BUY and k_innov < 0) or (direction == SignalDirection.SELL and k_innov > 0) else -1.0
        confidence = min(0.88, 0.55 + min(0.25, abs(z_score) / 3.0) + max(0.0, kalman_align) * 0.06 - min(0.06, k_trend * 0.08))
        edge = 12 + abs(z_score) * 10 + (kalman_align * 4.0) - snapshot.volatility * 250 - min(8.0, k_trend * 10)
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
                slippage_estimate_bps=snapshot.spread_bps * 1.05,
                position_size_ratio=0.045 * self.weight,
                leverage=1.5,
                stop_loss_pct=0.007,
                take_profit_pct=0.01,
                comment="bollinger_reversion",
                meta={
                    "bb_z": z_score,
                    "width_ratio": width,
                    "regime": regime.regime.value,
                    "kalman_trend_score": kalman["trend_score"],
                    "kalman_innovation_z": kalman["innovation_z"],
                    "kalman_uncertainty": kalman["uncertainty"],
                },
            )
        ]


class EmaCrossoverStrategy(TradingStrategy):
    id = "ema_crossover"
    name = "EMA Crossover"
    supported_regimes = ["trend_up", "trend_down"]

    def generate(self, snapshot: MarketSnapshot, regime: MarketRegime) -> List[StrategySignal]:
        if not self._allowed(regime):
            return []
        kalman = self._kalman_features(snapshot)
        k_trend = float(kalman["trend_score"])
        k_shock = abs(float(kalman["innovation_z"]))

        ema_fast = float(snapshot.features.get("ema_fast", snapshot.price))
        ema_slow = float(snapshot.features.get("ema_slow", snapshot.price))

        if ema_fast <= 0 or ema_slow <= 0:
            return []

        if self.cfg.get("flat_to_trade", True) is True and abs(snapshot.momentum_7d) < 0.0015:
            return []

        spread = (ema_fast - ema_slow) / max(ema_slow, 1e-9)
        min_gap = float(self.cfg.get("min_gap", 0.001))

        if spread > min_gap:
            direction = SignalDirection.BUY
            if k_trend < -0.2:
                return []
        elif spread < -min_gap:
            direction = SignalDirection.SELL
            if k_trend > 0.2:
                return []
        else:
            return []

        align = max(0.0, k_trend) if direction == SignalDirection.BUY else max(0.0, -k_trend)
        confidence = min(0.95, 0.56 + min(0.3, abs(spread) * 100.0) + align * 0.08 - min(0.08, k_shock * 0.01))
        edge = 18 + abs(spread) * 3000 + align * 12 - snapshot.volatility * 150 - min(12.0, k_shock * 1.5)
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
                slippage_estimate_bps=snapshot.spread_bps * 1.0,
                position_size_ratio=0.05 * self.weight,
                leverage=2.0,
                stop_loss_pct=0.01,
                take_profit_pct=0.018,
                comment="ema_crossover",
                meta={
                    "ema_fast": ema_fast,
                    "ema_slow": ema_slow,
                    "spread": spread,
                    "regime": regime.regime.value,
                    "kalman_trend_score": k_trend,
                    "kalman_innovation_z": kalman["innovation_z"],
                    "kalman_uncertainty": kalman["uncertainty"],
                },
            )
        ]


class VolumeBreakoutStrategy(TradingStrategy):
    id = "volume_breakout"
    name = "Volume Breakout"
    supported_regimes = ["trend_up", "trend_down", "range"]

    def generate(self, snapshot: MarketSnapshot, regime: MarketRegime) -> List[StrategySignal]:
        if not self._allowed(regime):
            return []
        kalman = self._kalman_features(snapshot)
        k_trend = float(kalman["trend_score"])
        k_shock = abs(float(kalman["innovation_z"]))

        ratio = float(snapshot.features.get("volume_ratio", 1.0))
        min_ratio = float(self.cfg.get("volume_ratio_min", 1.8))
        if ratio < min_ratio:
            return []

        if abs(snapshot.momentum_7d) < 0.0015:
            return []

        direction = SignalDirection.BUY if snapshot.momentum_7d > 0 else SignalDirection.SELL
        if direction == SignalDirection.BUY and k_trend < -0.45:
            return []
        if direction == SignalDirection.SELL and k_trend > 0.45:
            return []

        align = max(0.0, k_trend) if direction == SignalDirection.BUY else max(0.0, -k_trend)
        confidence = min(0.85, 0.58 + min(0.2, (ratio - 1.0) / 8) + align * 0.06 - min(0.06, k_shock * 0.01))
        edge = 14 + (ratio - 1.0) * 6 + align * 9 - snapshot.volatility * 220 - min(10.0, k_shock * 1.4)
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
                slippage_estimate_bps=snapshot.spread_bps * 0.95,
                position_size_ratio=0.05 * self.weight,
                leverage=float(self.cfg.get("leverage", 2.0)),
                stop_loss_pct=0.008,
                take_profit_pct=0.016,
                comment="volume_breakout",
                meta={
                    "volume_ratio": ratio,
                    "momentum": snapshot.momentum_7d,
                    "regime": regime.regime.value,
                    "kalman_trend_score": k_trend,
                    "kalman_innovation_z": kalman["innovation_z"],
                    "kalman_uncertainty": kalman["uncertainty"],
                },
            )
        ]
