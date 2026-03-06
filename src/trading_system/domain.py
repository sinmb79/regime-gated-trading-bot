from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class SignalDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class RegimeType(str, Enum):
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    RANGE = "range"
    PANIC = "panic"
    UNKNOWN = "unknown"


class OrderStatus(str, Enum):
    NEW = "new"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class RejectReason(str, Enum):
    RISK_REJECTED = "risk_rejected"
    INVALID_POSITION_SIZE = "invalid_position_size"
    INSUFFICIENT_CASH = "insufficient_cash"
    INVALID_SIZE = "invalid_size"
    INVALID_ORDER = "invalid_order"
    INVALID_ORDER_VALUE = "invalid_order_value"
    UNSUPPORTED_SIDE = "unsupported_side"
    PARTIAL_FILL_ZERO = "partial_fill_zero"
    PARTIAL_FILL = "partial_fill"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    AUTH_ERROR = "auth_error"
    RATE_LIMIT = "rate_limit"
    LIVE_STAGING_GUARD = "live_staging_guard"
    EXECUTION_GUARD = "execution_guard"
    EXCHANGE_REJECT = "exchange_reject"
    UNKNOWN_REJECT = "unknown_reject"

    @classmethod
    def from_text(cls, raw: str | None) -> "RejectReason":
        normalized = (raw or "").strip().lower()
        if not normalized:
            return cls.UNKNOWN_REJECT

        if "insufficient_cash" in normalized or "insufficient_balance" in normalized:
            return cls.INSUFFICIENT_CASH
        if "insufficient_margin" in normalized:
            return cls.INSUFFICIENT_CASH
        if "invalid_order_value" in normalized:
            return cls.INVALID_ORDER_VALUE
        if "invalid_size" in normalized:
            return cls.INVALID_SIZE
        if "invalid_order" in normalized or "invalid order" in normalized:
            return cls.INVALID_ORDER
        if "unsupported_side" in normalized or "invalid_side" in normalized:
            return cls.UNSUPPORTED_SIDE
        if "partial_fill_zero" in normalized:
            return cls.PARTIAL_FILL_ZERO
        if "partial_fill" in normalized:
            return cls.PARTIAL_FILL
        if "timeout" in normalized or "timed out" in normalized:
            return cls.TIMEOUT
        if "network" in normalized:
            return cls.NETWORK_ERROR
        if "auth" in normalized or "api_key" in normalized or "api secret" in normalized:
            return cls.AUTH_ERROR
        if "rate limit" in normalized:
            return cls.RATE_LIMIT
        if "live_staging" in normalized:
            return cls.LIVE_STAGING_GUARD
        if "execution_guard" in normalized or "guard_block" in normalized or "quarantine" in normalized:
            return cls.EXECUTION_GUARD
        return cls.EXCHANGE_REJECT

    def is_retryable(self) -> bool:
        return self not in {
            RejectReason.INSUFFICIENT_CASH,
            RejectReason.INVALID_SIZE,
            RejectReason.INVALID_ORDER,
            RejectReason.INVALID_ORDER_VALUE,
            RejectReason.UNSUPPORTED_SIDE,
            RejectReason.AUTH_ERROR,
        }


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    timestamp: datetime
    price: float
    volume: float
    momentum_7d: float
    volatility: float
    spread_bps: float
    funding_rate: float
    features: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketRegime:
    symbol: str
    regime: RegimeType
    confidence: float
    score: float
    reason: str


@dataclass(frozen=True)
class StrategySignal:
    strategy_id: str
    symbol: str
    timestamp: datetime
    direction: SignalDirection
    confidence: float
    expected_edge_bps: float
    slippage_estimate_bps: float
    position_size_ratio: float
    leverage: float
    stop_loss_pct: float
    take_profit_pct: float
    comment: str
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reasons: List[str]
    adjusted_position_ratio: Optional[float] = None
    adjusted_leverage: Optional[float] = None


@dataclass(frozen=True)
class TradeEvent:
    signal: StrategySignal
    status: OrderStatus
    requested_size_usdt: Optional[float] = None
    size_usdt: Optional[float] = None
    leverage: Optional[float] = None
    order_id: Optional[str] = None
    filled_price: Optional[float] = None
    expected_fill_price: Optional[float] = None
    actual_fill_price: Optional[float] = None
    fee_bps: Optional[float] = None
    fee_usdt: Optional[float] = None
    gross_realized_pnl: Optional[float] = None
    realized_pnl: Optional[float] = None
    slippage_bps: Optional[float] = None
    reject_reason: Optional[str] = None
    attempt_count: int = 1
    is_partial: bool = False


@dataclass(frozen=True)
class StrategyCandidate:
    signal: StrategySignal
    score: float











