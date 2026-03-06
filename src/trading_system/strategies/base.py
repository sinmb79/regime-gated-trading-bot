from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..domain import MarketRegime, MarketSnapshot, StrategySignal


class TradingStrategy(ABC):
    id: str = "base"
    name: str = "base"
    supported_regimes: List[str] = []

    def __init__(self, weight: float = 1.0, cfg: dict | None = None):
        self.weight = weight
        self.cfg = cfg or {}

    @abstractmethod
    def generate(self, snapshot: MarketSnapshot, regime: MarketRegime) -> List[StrategySignal]:
        raise NotImplementedError

    def _allowed(self, regime: MarketRegime) -> bool:
        if not self.supported_regimes:
            return True
        return regime.regime.value in self.supported_regimes

    @staticmethod
    def _feature_float(snapshot: MarketSnapshot, key: str, default: float = 0.0) -> float:
        features = snapshot.features if isinstance(snapshot.features, dict) else {}
        try:
            return float(features.get(key, default))
        except Exception:
            return float(default)

    def _kalman_features(self, snapshot: MarketSnapshot) -> dict[str, float]:
        return {
            "trend_score": self._feature_float(snapshot, "kalman_trend_score", 0.0),
            "velocity_ratio": self._feature_float(snapshot, "kalman_velocity_ratio", 0.0),
            "innovation_z": self._feature_float(snapshot, "kalman_innovation_z", 0.0),
            "uncertainty": self._feature_float(snapshot, "kalman_uncertainty", 0.0),
        }
