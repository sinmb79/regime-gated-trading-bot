from __future__ import annotations

import time
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from .domain import RejectReason, RiskDecision, StrategySignal, TradeEvent, OrderStatus
from .exchange import ExchangeAdapter
from .journal import TradeJournal


@dataclass
class ExecutionResult:
    status: str
    message: str
    order_id: Optional[str] = None


class ExecutionEngine:
    def __init__(
        self,
        exchange: ExchangeAdapter,
        journal: TradeJournal,
        maker_fee_bps: float,
        taker_fee_bps: float,
        order_retries: int = 2,
        retry_base_wait_ms: int = 300,
        mode: str = "dry",
        live_staging: dict[str, Any] | None = None,
    ):
        self.exchange = exchange
        self.journal = journal
        self.maker_fee_bps = maker_fee_bps
        self.taker_fee_bps = taker_fee_bps
        self.order_retries = max(0, int(order_retries))
        self.retry_base_wait_ms = max(0, int(retry_base_wait_ms))
        self.mode = str(mode or "dry").strip().lower()
        self.live_staging: Dict[str, Any] = dict(live_staging or {})
        self._position_book: Dict[str, Dict[str, float]] = {}
        self._last_live_staging: Dict[str, Any] = {
            "enabled": False,
            "active": False,
            "stage": 0,
            "max_order_usdt": 0.0,
            "today_trades": 0,
            "today_pnl": 0.0,
            "blocked": False,
            "block_reason": "",
        }
        self._guard_cfg: Dict[str, Any] = {
            "symbol_failure_threshold": 3,
            "symbol_quarantine_seconds": 120,
            "global_failure_threshold": 8,
            "global_quarantine_seconds": 60,
            "auth_quarantine_seconds": 600,
            "backoff_multiplier": 2.0,
            "max_backoff_seconds": 8.0,
            "jitter_ratio": 0.2,
            "recovery_decay_seconds": 300,
        }
        self._symbol_guard: Dict[str, Dict[str, Any]] = {}
        self._global_guard: Dict[str, Any] = {
            "blocked_until": 0.0,
            "reason": "",
            "failure_count": 0,
            "last_error": "",
            "last_error_at": 0.0,
        }

    @staticmethod
    def _status_from_exchange(raw_status: str) -> OrderStatus:
        try:
            return OrderStatus(raw_status)
        except Exception:
            return OrderStatus.REJECTED

    @staticmethod
    def _reject_reason_from_text(raw: str | None) -> str:
        return RejectReason.from_text(raw).value

    @staticmethod
    def _is_retryable_reject(reason: str) -> bool:
        return RejectReason.from_text(reason).is_retryable()

    @staticmethod
    def _extract_order_reject_reason(order) -> str:
        reason = (getattr(order, "reject_reason", "") or "").strip()
        if reason:
            reason = ExecutionEngine._reject_reason_from_text(reason)
        else:
            reason = ExecutionEngine._reject_reason_from_text(getattr(order, "note", None))
        return reason

    def _log_order(self, signal: StrategySignal, event: TradeEvent, signal_id: str | None = None) -> None:
        try:
            self.journal.log_execution(signal, event, signal_id=signal_id)
        except Exception:
            # log failure should not interrupt caller path.
            pass

    @staticmethod
    def _f(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    @staticmethod
    def _i(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return int(default)

    @staticmethod
    def _side_sign(side: Any) -> int:
        raw = str(side or "").strip().upper()
        if raw in {"BUY", "LONG"}:
            return 1
        if raw in {"SELL", "SHORT"}:
            return -1
        return 0

    def _estimate_gross_realized_pnl(
        self,
        symbol: str,
        side: Any,
        filled_usdt: float,
        fill_price: float,
    ) -> float:
        notional = max(float(filled_usdt or 0.0), 0.0)
        price = max(float(fill_price or 0.0), 0.0)
        side_sign = self._side_sign(side)
        if not symbol or notional <= 0 or price <= 0 or side_sign == 0:
            return 0.0

        current = self._position_book.get(symbol, {"notional": 0.0, "entry_price": price})
        current_notional = float(current.get("notional", 0.0) or 0.0)
        entry_price = max(float(current.get("entry_price", price) or price), 1e-9)
        delta_notional = notional * side_sign

        if abs(current_notional) <= 1e-12:
            self._position_book[symbol] = {"notional": delta_notional, "entry_price": price}
            return 0.0

        same_direction = (current_notional > 0 and side_sign > 0) or (current_notional < 0 and side_sign < 0)
        if same_direction:
            old_abs = abs(current_notional)
            add_abs = abs(delta_notional)
            new_abs = old_abs + add_abs
            new_entry = ((entry_price * old_abs) + (price * add_abs)) / max(new_abs, 1e-9)
            self._position_book[symbol] = {
                "notional": current_notional + delta_notional,
                "entry_price": new_entry,
            }
            return 0.0

        close_abs = min(abs(current_notional), abs(delta_notional))
        close_qty = close_abs / max(price, 1e-9)
        if current_notional > 0:
            realized = (price - entry_price) * close_qty
        else:
            realized = (entry_price - price) * close_qty

        current_remaining = abs(current_notional) - close_abs
        incoming_remaining = abs(delta_notional) - close_abs

        if incoming_remaining <= 1e-12:
            if current_remaining <= 1e-12:
                self._position_book.pop(symbol, None)
            else:
                sign = 1.0 if current_notional > 0 else -1.0
                self._position_book[symbol] = {
                    "notional": sign * current_remaining,
                    "entry_price": entry_price,
                }
        else:
            sign = 1.0 if side_sign > 0 else -1.0
            self._position_book[symbol] = {
                "notional": sign * incoming_remaining,
                "entry_price": price,
            }

        return float(realized)

    def _fee_bps_fallback(self, leverage: float) -> float:
        return float(self.maker_fee_bps if leverage <= 1 else self.taker_fee_bps)

    def _order_fee_usdt(self, order: Any, filled_usdt: float, leverage: float) -> float:
        fee_usdt = self._f(getattr(order, "fee_usdt", 0.0), 0.0)
        if fee_usdt > 0:
            return fee_usdt
        if self.mode != "live":
            return 0.0
        fee_rate_bps = self._f(getattr(order, "fee_rate_bps", 0.0), 0.0)
        if fee_rate_bps <= 0:
            fee_rate_bps = self._fee_bps_fallback(leverage)
        if filled_usdt <= 0:
            return 0.0
        return max(0.0, float(filled_usdt) * float(fee_rate_bps) / 10000.0)

    def _live_staging_state(self) -> Dict[str, Any]:
        enabled = bool(self.live_staging.get("enabled", False))
        today_pnl, today_trades, _ = self.journal.today_performance()
        state = {
            "enabled": enabled,
            "active": False,
            "stage": 0,
            "max_order_usdt": 0.0,
            "today_trades": int(today_trades or 0),
            "today_pnl": float(today_pnl or 0.0),
            "blocked": False,
            "block_reason": "",
        }
        if not enabled or self.mode != "live":
            return state

        state["active"] = True
        t1 = max(1, self._i(self.live_staging.get("stage1_trade_count", 10), 10))
        t2 = max(t1 + 1, self._i(self.live_staging.get("stage2_trade_count", 20), 20))
        c1 = max(1.0, self._f(self.live_staging.get("stage1_max_order_usdt", 50.0), 50.0))
        c2 = max(c1, self._f(self.live_staging.get("stage2_max_order_usdt", 150.0), 150.0))
        c3 = max(c2, self._f(self.live_staging.get("stage3_max_order_usdt", 400.0), 400.0))
        require_non_neg = bool(self.live_staging.get("require_non_negative_pnl_for_promotion", True))
        block_loss = abs(self._f(self.live_staging.get("block_on_daily_loss_usdt", 150.0), 150.0))

        trades = int(state["today_trades"])
        pnl = float(state["today_pnl"])
        if trades < t1:
            stage = 1
            cap = c1
        elif trades < t2:
            stage = 2
            cap = c2
        else:
            stage = 3
            cap = c3

        if require_non_neg and pnl < 0:
            stage = 1
            cap = c1

        blocked = block_loss > 0 and pnl <= (-block_loss)
        state["stage"] = stage
        state["max_order_usdt"] = cap
        state["blocked"] = blocked
        if blocked:
            state["block_reason"] = f"daily_pnl={pnl:.2f} <= -{block_loss:.2f}"
        return state

    def get_live_staging_status(self) -> Dict[str, Any]:
        return dict(self._last_live_staging)

    @staticmethod
    def _now_ts() -> float:
        return time.time()

    def _guard_symbol_state(self, symbol: str) -> Dict[str, Any]:
        key = str(symbol or "").upper()
        if key not in self._symbol_guard:
            self._symbol_guard[key] = {
                "failure_count": 0,
                "blocked_until": 0.0,
                "last_error": "",
                "last_error_at": 0.0,
            }
        return self._symbol_guard[key]

    def _decay_guard_failures(self, symbol: str, now_ts: float) -> None:
        decay_seconds = max(1.0, float(self._guard_cfg.get("recovery_decay_seconds", 300.0)))
        state = self._guard_symbol_state(symbol)
        last_error_at = float(state.get("last_error_at", 0.0) or 0.0)
        if last_error_at <= 0:
            return
        elapsed = now_ts - last_error_at
        if elapsed <= decay_seconds:
            return
        prev = int(state.get("failure_count", 0) or 0)
        if prev <= 0:
            return
        reduced = max(0, prev - int(elapsed // decay_seconds))
        state["failure_count"] = reduced

        g_last = float(self._global_guard.get("last_error_at", 0.0) or 0.0)
        g_prev = int(self._global_guard.get("failure_count", 0) or 0)
        if g_last > 0 and g_prev > 0:
            g_elapsed = now_ts - g_last
            if g_elapsed > decay_seconds:
                self._global_guard["failure_count"] = max(0, g_prev - int(g_elapsed // decay_seconds))

    def _is_guard_blocked(self, symbol: str, now_ts: float) -> tuple[bool, str]:
        self._decay_guard_failures(symbol, now_ts)
        state = self._guard_symbol_state(symbol)
        symbol_until = float(state.get("blocked_until", 0.0) or 0.0)
        if now_ts < symbol_until:
            remain = max(0, int(symbol_until - now_ts))
            return True, f"execution_guard:symbol_quarantine:{symbol}:{remain}s"

        global_until = float(self._global_guard.get("blocked_until", 0.0) or 0.0)
        if now_ts < global_until:
            remain = max(0, int(global_until - now_ts))
            reason = str(self._global_guard.get("reason", "") or "global_quarantine")
            return True, f"execution_guard:global_quarantine:{reason}:{remain}s"
        return False, ""

    def _mark_guard_failure(self, symbol: str, reason: str) -> None:
        now_ts = self._now_ts()
        state = self._guard_symbol_state(symbol)
        failure_count = int(state.get("failure_count", 0) or 0) + 1
        state["failure_count"] = failure_count
        state["last_error"] = str(reason or "")
        state["last_error_at"] = now_ts

        threshold = max(1, int(self._guard_cfg.get("symbol_failure_threshold", 3)))
        if failure_count >= threshold:
            quarantine = max(1.0, float(self._guard_cfg.get("symbol_quarantine_seconds", 120.0)))
            state["blocked_until"] = max(float(state.get("blocked_until", 0.0) or 0.0), now_ts + quarantine)

        g_count = int(self._global_guard.get("failure_count", 0) or 0) + 1
        self._global_guard["failure_count"] = g_count
        self._global_guard["last_error"] = str(reason or "")
        self._global_guard["last_error_at"] = now_ts

        reason_enum = RejectReason.from_text(reason)
        if reason_enum == RejectReason.AUTH_ERROR:
            self._global_guard["reason"] = RejectReason.AUTH_ERROR.value
            auth_quarantine = max(10.0, float(self._guard_cfg.get("auth_quarantine_seconds", 600.0)))
            self._global_guard["blocked_until"] = max(float(self._global_guard.get("blocked_until", 0.0) or 0.0), now_ts + auth_quarantine)
            return

        if reason_enum in {RejectReason.RATE_LIMIT, RejectReason.NETWORK_ERROR, RejectReason.TIMEOUT}:
            self._global_guard["reason"] = reason_enum.value
            global_quarantine = max(1.0, float(self._guard_cfg.get("global_quarantine_seconds", 60.0)))
            self._global_guard["blocked_until"] = max(float(self._global_guard.get("blocked_until", 0.0) or 0.0), now_ts + global_quarantine)
            return

        g_threshold = max(1, int(self._guard_cfg.get("global_failure_threshold", 8)))
        if g_count >= g_threshold:
            self._global_guard["reason"] = "global_failure_threshold"
            global_quarantine = max(1.0, float(self._guard_cfg.get("global_quarantine_seconds", 60.0)))
            self._global_guard["blocked_until"] = max(float(self._global_guard.get("blocked_until", 0.0) or 0.0), now_ts + global_quarantine)

    def _mark_guard_success(self, symbol: str) -> None:
        state = self._guard_symbol_state(symbol)
        prev = int(state.get("failure_count", 0) or 0)
        state["failure_count"] = max(0, prev - 1)
        state["last_error"] = ""
        if self._now_ts() >= float(state.get("blocked_until", 0.0) or 0.0):
            state["blocked_until"] = 0.0

        g_prev = int(self._global_guard.get("failure_count", 0) or 0)
        self._global_guard["failure_count"] = max(0, g_prev - 1)
        if self._now_ts() >= float(self._global_guard.get("blocked_until", 0.0) or 0.0):
            self._global_guard["blocked_until"] = 0.0
            self._global_guard["reason"] = ""

    def _retry_wait_seconds(self, attempt: int) -> float:
        if self.retry_base_wait_ms <= 0:
            return 0.0
        base = max(0.0, float(self.retry_base_wait_ms) / 1000.0)
        mult = max(1.0, float(self._guard_cfg.get("backoff_multiplier", 2.0)))
        cap = max(base, float(self._guard_cfg.get("max_backoff_seconds", 8.0)))
        jitter_ratio = max(0.0, min(1.0, float(self._guard_cfg.get("jitter_ratio", 0.2))))
        backoff = min(cap, base * (mult ** max(0, attempt - 1)))
        jitter = backoff * jitter_ratio * random.random()
        return backoff + jitter

    def get_execution_guard_status(self) -> Dict[str, Any]:
        now_ts = self._now_ts()
        symbols: Dict[str, Any] = {}
        for symbol, state in self._symbol_guard.items():
            blocked_until = float(state.get("blocked_until", 0.0) or 0.0)
            symbols[symbol] = {
                "failure_count": int(state.get("failure_count", 0) or 0),
                "blocked": now_ts < blocked_until,
                "blocked_until_ts": blocked_until,
                "blocked_remaining_seconds": max(0, int(blocked_until - now_ts)),
                "last_error": str(state.get("last_error", "") or ""),
            }

        global_until = float(self._global_guard.get("blocked_until", 0.0) or 0.0)
        return {
            "config": dict(self._guard_cfg),
            "global": {
                "blocked": now_ts < global_until,
                "blocked_until_ts": global_until,
                "blocked_remaining_seconds": max(0, int(global_until - now_ts)),
                "failure_count": int(self._global_guard.get("failure_count", 0) or 0),
                "reason": str(self._global_guard.get("reason", "") or ""),
                "last_error": str(self._global_guard.get("last_error", "") or ""),
            },
            "symbols": symbols,
        }

    def execute(self, signal: StrategySignal, risk: RiskDecision, account_equity: float, signal_id: str | None = None) -> TradeEvent:
        if not risk.allowed:
            event = TradeEvent(
                signal=signal,
                status=OrderStatus.REJECTED,
                requested_size_usdt=0.0,
                size_usdt=0.0,
                leverage=signal.leverage,
                realized_pnl=0.0,
                reject_reason=RejectReason.RISK_REJECTED.value,
                attempt_count=1,
                is_partial=False,
            )
            self._log_order(signal, event, signal_id=signal_id)
            return event

        size_ratio = risk.adjusted_position_ratio if risk.adjusted_position_ratio is not None else signal.position_size_ratio
        leverage = risk.adjusted_leverage if risk.adjusted_leverage is not None else signal.leverage
        requested_size = account_equity * size_ratio
        live_staging = self._live_staging_state()
        self._last_live_staging = live_staging
        if bool(live_staging.get("blocked", False)):
            event = TradeEvent(
                signal=signal,
                status=OrderStatus.REJECTED,
                requested_size_usdt=max(0.0, float(requested_size)),
                size_usdt=0.0,
                leverage=leverage,
                realized_pnl=0.0,
                reject_reason=RejectReason.LIVE_STAGING_GUARD.value,
                attempt_count=1,
                is_partial=False,
            )
            self._log_order(signal, event, signal_id=signal_id)
            return event

        if bool(live_staging.get("active", False)):
            cap = max(0.0, self._f(live_staging.get("max_order_usdt", 0.0), 0.0))
            if cap > 0:
                requested_size = min(float(requested_size), cap)
        if requested_size <= 0:
            event = TradeEvent(
                signal=signal,
                status=OrderStatus.REJECTED,
                requested_size_usdt=0.0,
                size_usdt=0.0,
                leverage=leverage,
                realized_pnl=0.0,
                reject_reason=RejectReason.INVALID_POSITION_SIZE.value,
                attempt_count=1,
                is_partial=False,
            )
            self._log_order(signal, event, signal_id=signal_id)
            return event

        now_ts = self._now_ts()
        blocked, block_reason = self._is_guard_blocked(signal.symbol, now_ts)
        if blocked:
            event = TradeEvent(
                signal=signal,
                status=OrderStatus.REJECTED,
                requested_size_usdt=max(0.0, float(requested_size)),
                size_usdt=0.0,
                leverage=leverage,
                realized_pnl=0.0,
                reject_reason=RejectReason.EXECUTION_GUARD.value,
                attempt_count=1,
                is_partial=False,
            )
            self._mark_guard_failure(signal.symbol, block_reason or RejectReason.EXECUTION_GUARD.value)
            self._log_order(signal, event, signal_id=signal_id)
            return event

        remaining_size = requested_size
        max_attempts = self.order_retries + 1
        attempt = 0

        total_filled = 0.0
        total_fee_usdt = 0.0
        total_realized_gross = 0.0
        total_realized_net = 0.0
        final_order_id = None
        final_note = ""
        final_status: Optional[OrderStatus] = None
        final_reject_reason: str = ""
        final_expected_cost = 0.0
        final_actual_cost = 0.0

        while attempt < max_attempts and remaining_size > 0:
            attempt += 1
            order = self.exchange.create_order(
                symbol=signal.symbol,
                side=signal.direction,
                size_usdt=remaining_size,
                leverage=leverage,
                stop_loss_pct=signal.stop_loss_pct,
                take_profit_pct=signal.take_profit_pct,
                comment=signal.comment,
            )

            final_order_id = order.order_id or final_order_id
            status = self._status_from_exchange(order.status)
            final_note = order.note

            order_filled = float(order.size_usdt or 0.0)
            order_actual_price = float(order.price) if order.price is not None else 0.0
            order_expected_price = float(getattr(order, "expected_price", 0.0) or 0.0)
            order_estimated_gross = self._estimate_gross_realized_pnl(
                symbol=signal.symbol,
                side=signal.direction.value,
                filled_usdt=order_filled,
                fill_price=order_actual_price if order_actual_price > 0 else order_expected_price,
            )
            order_reported_gross = self._f(getattr(order, "gross_realized_pnl", 0.0), 0.0)
            if abs(order_reported_gross) <= 1e-12:
                order_reported_gross = self._f(getattr(order, "realized_pnl", 0.0), 0.0)
            order_fee_usdt = self._order_fee_usdt(order, filled_usdt=order_filled, leverage=leverage)
            if abs(order_reported_gross) > 1e-12:
                order_gross = order_reported_gross
                order_net = order_reported_gross
            else:
                order_gross = order_estimated_gross
                order_net = order_estimated_gross - order_fee_usdt

            total_filled += order_filled
            total_fee_usdt += order_fee_usdt
            total_realized_gross += order_gross
            total_realized_net += order_net
            remaining_size = max(0.0, requested_size - total_filled)
            if order_filled > 0:
                if order_expected_price > 0:
                    final_expected_cost += order_expected_price * order_filled
                final_actual_cost += order_actual_price * order_filled

            if status == OrderStatus.FILLED:
                final_status = OrderStatus.FILLED
                remaining_size = max(0.0, requested_size - total_filled)
                if remaining_size <= 1e-12:
                    self._mark_guard_success(signal.symbol)
                    break

                # Exchange reported full for one attempt but total fill can be short due to rounding.
                if self.order_retries == 0:
                    break
                wait_seconds = self._retry_wait_seconds(attempt)
                if wait_seconds > 0:
                    time.sleep(wait_seconds)
                continue

            if status == OrderStatus.PARTIALLY_FILLED:
                remaining_size = max(0.0, requested_size - total_filled)
                self._mark_guard_success(signal.symbol)

                if remaining_size > 1e-12 and attempt < max_attempts:
                    wait_seconds = self._retry_wait_seconds(attempt)
                    if wait_seconds > 0:
                        time.sleep(wait_seconds)
                    continue

                final_status = OrderStatus.PARTIALLY_FILLED if total_filled > 0 else OrderStatus.REJECTED
                break

            # status rejected
            final_reject_reason = self._extract_order_reject_reason(order)
            self._mark_guard_failure(signal.symbol, final_reject_reason or RejectReason.EXCHANGE_REJECT.value)
            retryable = self._is_retryable_reject(final_reject_reason)
            if not getattr(order, "retryable", True):
                retryable = False

            if retryable and remaining_size > 0 and attempt < max_attempts:
                wait_seconds = self._retry_wait_seconds(attempt)
                if wait_seconds > 0:
                    time.sleep(wait_seconds)
                continue

            if not final_reject_reason:
                final_reject_reason = RejectReason.EXCHANGE_REJECT.value
            final_status = OrderStatus.REJECTED
            break

        if total_filled <= 0.0:
            final_status = OrderStatus.REJECTED
            final_reject_reason = final_reject_reason or RejectReason.EXCHANGE_REJECT.value
            final_expected_fill = None
            final_actual_fill = None
            final_slippage = None
            is_partial = False
        else:
            if total_filled >= requested_size - 1e-12:
                final_status = OrderStatus.FILLED
                final_reject_reason = final_reject_reason or ""
                is_partial = False
            else:
                final_status = OrderStatus.PARTIALLY_FILLED
                final_reject_reason = final_reject_reason or RejectReason.PARTIAL_FILL.value
                is_partial = True

            final_expected_fill = (final_expected_cost / total_filled) if final_expected_cost > 0 else None
            final_actual_fill = (final_actual_cost / total_filled) if total_filled > 0 else None
            if final_expected_fill is not None and final_expected_fill > 0 and final_actual_fill is not None:
                final_slippage = (final_actual_fill - final_expected_fill) / final_expected_fill * 10000.0
            else:
                final_slippage = None

        final_fee_bps = self._fee_bps_fallback(leverage)
        if total_filled > 0 and total_fee_usdt > 0:
            final_fee_bps = (total_fee_usdt / total_filled) * 10000.0

        event = TradeEvent(
            signal=signal,
            status=final_status,
            requested_size_usdt=requested_size,
            size_usdt=total_filled,
            leverage=leverage,
            order_id=final_order_id,
            filled_price=final_actual_fill,
            expected_fill_price=final_expected_fill,
            actual_fill_price=final_actual_fill,
            fee_bps=final_fee_bps,
            fee_usdt=total_fee_usdt,
            gross_realized_pnl=total_realized_gross,
            realized_pnl=total_realized_net,
            slippage_bps=final_slippage,
            reject_reason=final_reject_reason,
            attempt_count=attempt,
            is_partial=is_partial,
        )
        self._log_order(signal, event, signal_id=signal_id)
        return event








