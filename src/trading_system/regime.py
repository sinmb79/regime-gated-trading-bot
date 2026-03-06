from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any, List

from .domain import MarketRegime, RegimeType


@dataclass
class RegimeVote:
    symbol: str
    up_votes: int
    down_votes: int
    range_votes: int
    panic_votes: int


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return float(default)


def _metrics_from_market_like(rows: list[Any]) -> tuple[float, float, float, float, float]:
    market_rows = [x for x in rows if hasattr(x, "momentum_7d")]
    momentum = [_f(getattr(x, "momentum_7d", 0.0), 0.0) for x in market_rows]
    volatility = [_f(getattr(x, "volatility", 0.0), 0.0) for x in market_rows]
    spread = [_f(getattr(x, "spread_bps", 0.0), 0.0) for x in market_rows]
    kalman_trend = [_f(getattr(x, "features", {}).get("kalman_trend_score", 0.0), 0.0) for x in market_rows]
    kalman_shock = [abs(_f(getattr(x, "features", {}).get("kalman_innovation_z", 0.0), 0.0)) for x in market_rows]
    if not momentum or not volatility or not spread:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    return mean(momentum), mean(volatility), mean(spread), mean(kalman_trend), mean(kalman_shock)


def _metrics_from_ohlcv_like(rows: list[Any]) -> tuple[float, float, float, float, float]:
    rows = [x for x in rows if hasattr(x, "close")]
    closes: list[float] = []
    returns: list[float] = []
    spreads: list[float] = []
    for x in rows:
        close = _f(getattr(x, "close", 0.0), 0.0)
        high = _f(getattr(x, "high", 0.0), 0.0)
        low = _f(getattr(x, "low", 0.0), 0.0)
        if close > 0:
            closes.append(close)
        if close > 0 and high > 0 and low > 0:
            spreads.append(max(0.0, (high - low) / close) * 10000.0)

    for i in range(max(0, len(closes) - 1)):
        prev = closes[i + 1]
        curr = closes[i]
        if prev > 0:
            returns.append(abs((curr - prev) / prev))

    avg_vol = mean(returns) if returns else 0.0
    avg_spread = mean(spreads) if spreads else 0.0

    if not closes:
        return 0.0, avg_vol, avg_spread, 0.0, 0.0
    lookback = min(len(closes) - 1, 6)
    if lookback <= 0:
        avg_momentum = 0.0
    else:
        ref = closes[lookback]
        avg_momentum = ((closes[0] - ref) / ref) if ref > 0 else 0.0
    return avg_momentum, avg_vol, avg_spread, 0.0, 0.0


def _blend(primary: float, secondary: float, primary_weight: float = 0.65) -> float:
    weight = max(0.0, min(1.0, float(primary_weight)))
    return (primary * weight) + (secondary * (1.0 - weight))


def classify_market_regime(symbol: str, snapshots: List[Any]) -> MarketRegime:
    if not snapshots:
        return MarketRegime(
            symbol=symbol,
            regime=RegimeType.UNKNOWN,
            confidence=0.0,
            score=0.0,
            reason="no_market_data",
        )

    rows = list(snapshots)
    market_rows = [row for row in rows if hasattr(row, "momentum_7d")]
    ohlcv_rows = [row for row in rows if hasattr(row, "close")]

    if market_rows and ohlcv_rows:
        market_momentum, market_vol, market_spread, avg_kalman_trend, avg_kalman_shock = _metrics_from_market_like(market_rows)
        ohlcv_momentum, ohlcv_vol, ohlcv_spread, _, _ = _metrics_from_ohlcv_like(ohlcv_rows)
        avg_momentum = _blend(market_momentum, ohlcv_momentum, primary_weight=0.65)
        avg_vol = _blend(market_vol, ohlcv_vol, primary_weight=0.55)
        avg_spread = _blend(market_spread, ohlcv_spread, primary_weight=0.60)
    elif market_rows:
        avg_momentum, avg_vol, avg_spread, avg_kalman_trend, avg_kalman_shock = _metrics_from_market_like(market_rows)
    else:
        avg_momentum, avg_vol, avg_spread, avg_kalman_trend, avg_kalman_shock = _metrics_from_ohlcv_like(ohlcv_rows)

    # Momentum + Kalman trend fusion with uncertainty penalty.
    trend_score = (avg_momentum * 72.0) + (avg_kalman_trend * 36.0) - (avg_vol * 18.0) - (avg_kalman_shock * 2.0)

    if avg_spread > 80 or avg_vol > 0.055 or avg_kalman_shock > 3.2:
        regime = RegimeType.PANIC
        score = min(1.0, (avg_spread / 100) + (avg_kalman_shock / 6.0))
        confidence = min(1.0, max(0.55, score))
    elif trend_score > 0.8:
        regime = RegimeType.TREND_UP
        confidence = min(1.0, 0.54 + trend_score / 10 + abs(avg_kalman_trend) * 0.08)
        score = trend_score
    elif trend_score < -0.8:
        regime = RegimeType.TREND_DOWN
        confidence = min(1.0, 0.54 + abs(trend_score) / 10 + abs(avg_kalman_trend) * 0.08)
        score = trend_score
    else:
        regime = RegimeType.RANGE
        confidence = max(0.45, 0.62 - min(0.18, abs(avg_kalman_trend) * 0.2) - min(0.12, avg_kalman_shock * 0.03))
        score = 0.0

    return MarketRegime(
        symbol=symbol,
        regime=regime,
        confidence=max(0.0, min(confidence, 1.0)),
        score=score,
        reason=(
            f"momentum={avg_momentum:.4f}, kalman_trend={avg_kalman_trend:.3f}, "
            f"kalman_shock={avg_kalman_shock:.2f}, volatility={avg_vol:.4f}, spread_bps={avg_spread:.2f}"
        ),
    )
