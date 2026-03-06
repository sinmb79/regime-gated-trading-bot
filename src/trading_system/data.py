from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from random import Random
from statistics import mean, pstdev
from typing import Deque, Dict, List, Optional

from .domain import MarketSnapshot
from .kalman import KalmanTrendTracker


@dataclass
class OhlcvPoint:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class DataCollector(ABC):
    @abstractmethod
    def collect_snapshot(self, symbol: str) -> MarketSnapshot:
        ...

    @abstractmethod
    def collect_batch(self, symbols: List[str]) -> Dict[str, MarketSnapshot]:
        ...

    @abstractmethod
    def get_history(self, symbol: str) -> List[OhlcvPoint]:
        ...


class MockMarketDataCollector(DataCollector):
    def __init__(self, seed: int = 42, symbols: Optional[List[str]] = None):
        self._rng_seed = seed
        self._rng_state = seed
        self._rng = Random(seed)
        self._clock = datetime.utcnow().replace(second=0, microsecond=0)
        self._trend_state: Dict[str, float] = {}
        self._kalman: Dict[str, KalmanTrendTracker] = {}
        self._histories: Dict[str, Deque[OhlcvPoint]] = defaultdict(lambda: deque(maxlen=300))
        base_prices = {
            "BTC/USDT": 62000,
            "ETH/USDT": 3200,
            "SOL/USDT": 140,
            "XRP/USDT": 0.6,
            "DOGE/USDT": 0.1,
        }
        for symbol in (symbols or base_prices.keys()):
            price = base_prices.get(symbol, 100)
            self._kalman[symbol] = KalmanTrendTracker(
                process_var=1e-2,
                measurement_var=max((float(price) * 0.0025) ** 2, 1e-6),
            )
            now = self._clock
            for i in range(120):
                now = now - timedelta(minutes=1)
                price = self._next_price(symbol, price, i)
                self._kalman[symbol].update(price)
                self._histories[symbol].append(
                    OhlcvPoint(
                        timestamp=now,
                        open=price * 0.998,
                        high=price * 1.004,
                        low=price * 0.996,
                        close=price,
                        volume=1000 + i * 2,
                    )
                )

    def _next_price(self, symbol: str, last: float, i: int) -> float:
        vol = 0.0015
        if "BTC" in symbol:
            vol = 0.002
        if "ETH" in symbol:
            vol = 0.0022
        if "SOL" in symbol:
            vol = 0.004
        if "DOGE" in symbol or "XRP" in symbol:
            vol = 0.006

        trend = float(self._trend_state.get(symbol, 0.0))
        trend = (trend * 0.86) + self._rng.gauss(0.0, vol * 0.22)
        trend_cap = vol * 2.8
        trend = max(-trend_cap, min(trend_cap, trend))
        self._trend_state[symbol] = trend

        noise = self._rng.gauss(0.0, vol * 0.45)
        cyclical = (i % 7 - 3) * 0.00008
        shock = trend + noise + cyclical
        return max(0.01, last * (1 + shock))

    def _random_float(self, a: float = 0.0, b: float = 1.0) -> float:
        # deterministic-like pseudo random for reproducibility in examples.
        self._rng_state = (1103515245 * self._rng_state + 12345) & 0x7fffffff
        return a + (self._rng_state / 0x7fffffff) * (b - a)

    def _next_timestamp(self) -> datetime:
        self._clock = self._clock + timedelta(minutes=1)
        return self._clock

    def _kalman_tracker(self, symbol: str, fallback_price: float) -> KalmanTrendTracker:
        tracker = self._kalman.get(symbol)
        if tracker is not None:
            return tracker
        tracker = KalmanTrendTracker(
            process_var=1e-2,
            measurement_var=max((float(fallback_price) * 0.0025) ** 2, 1e-6),
        )
        tracker.update(float(fallback_price))
        self._kalman[symbol] = tracker
        return tracker

    @staticmethod
    def _ema(values: List[float], period: int) -> float:
        if not values or period <= 0:
            return 0.0
        alpha = 2.0 / (period + 1)
        out = float(values[0])
        for value in values[1:]:
            out = alpha * float(value) + (1 - alpha) * out
        return out

    def _collect_snapshot_at(self, symbol: str, ts: datetime) -> MarketSnapshot:
        hist = self._histories[symbol]
        last = hist[0].close if hist else 100.0
        new_close = self._next_price(symbol, last, len(hist))
        point = OhlcvPoint(
            timestamp=ts,
            open=last,
            high=new_close * (1 + self._random_float(0.0003, 0.0015)),
            low=new_close * (1 - self._random_float(0.0003, 0.0015)),
            close=new_close,
            volume=1000 + self._random_float(0, 2000),
        )
        hist.appendleft(point)

        closes = [p.close for p in list(hist)[:12]]
        vols = [abs((closes[i] - closes[i + 1]) / closes[i + 1]) for i in range(len(closes) - 1)] if len(closes) > 1 else [0.0]
        momentum = 0.0
        if len(closes) >= 7 and closes[6] > 0:
            momentum = (closes[0] - closes[6]) / closes[6]

        spread_bps = self._random_float(5, 80)
        trend = float(self._trend_state.get(symbol, 0.0))
        funding = max(-0.03, min(0.03, (-trend * 6.0) + self._random_float(-0.003, 0.003)))

        closes20 = [p.close for p in list(hist)[:20]]
        vols20 = [p.volume for p in list(hist)[:20]]
        rel_vol = mean(vols) if vols else 0.001

        bb_mid = mean(closes20) if closes20 else point.close
        bb_std = pstdev(closes20) if len(closes20) >= 2 else 0.0
        bb_z = 0.0
        if bb_std > 1e-12 and point.close > 0:
            bb_z = (point.close - bb_mid) / bb_std
        bb_width_ratio = (bb_std / bb_mid) if bb_mid > 0 else 0.0

        ema_fast = self._ema(closes[:8], 3)
        ema_slow = self._ema(closes20, 12)
        vma = mean(vols20) if vols20 else 1.0
        volume_ratio = point.volume / vma if vma > 0 else 1.0

        obs_std = max(new_close * max(rel_vol, 0.0008), new_close * 0.0008)
        tracker = self._kalman_tracker(symbol, fallback_price=new_close)
        kal = tracker.update(new_close, measurement_var=obs_std * obs_std)

        return MarketSnapshot(
            symbol=symbol,
            timestamp=point.timestamp,
            price=new_close,
            volume=point.volume,
            momentum_7d=momentum,
            volatility=mean(vols),
            spread_bps=spread_bps,
            funding_rate=funding,
            features={
                "atr": mean(vols) * 10000,
                "rsi_like": self._random_float(20, 80),
                "bb_mid": bb_mid,
                "bb_std": bb_std,
                "bb_z": bb_z,
                "bb_width_ratio": bb_width_ratio,
                "ema_fast": ema_fast,
                "ema_slow": ema_slow,
                "volume_ratio": volume_ratio,
                "kalman_price": kal["price"],
                "kalman_velocity": kal["velocity"],
                "kalman_velocity_ratio": kal["velocity_ratio"],
                "kalman_trend_score": kal["trend_score"],
                "kalman_innovation": kal["innovation"],
                "kalman_innovation_z": kal["innovation_z"],
                "kalman_uncertainty": kal["uncertainty"],
            },
        )

    def collect_snapshot(self, symbol: str) -> MarketSnapshot:
        return self._collect_snapshot_at(symbol, ts=self._next_timestamp())

    def collect_batch(self, symbols: List[str]) -> Dict[str, MarketSnapshot]:
        ts = self._next_timestamp()
        return {s: self._collect_snapshot_at(s, ts=ts) for s in symbols}

    def get_history(self, symbol: str) -> List[OhlcvPoint]:
        return list(self._histories[symbol])
