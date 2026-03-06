from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from .config import ExchangeConfig
from .domain import RejectReason


@dataclass
class Order:
    order_id: str
    symbol: str
    side: str
    size_usdt: float
    leverage: float
    status: str
    price: float
    created_at: datetime
    updated_at: datetime
    requested_size_usdt: float = 0.0
    expected_price: float = 0.0
    realized_pnl: float = 0.0
    note: str = ""
    slippage_bps: float = 0.0
    retryable: bool = True
    reject_reason: str = ""
    fee_usdt: float = 0.0
    fee_rate_bps: float = 0.0
    gross_realized_pnl: float = 0.0


class ExchangeAdapter(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def get_balance(self) -> Dict[str, float]:
        ...

    @abstractmethod
    def get_last_price(self, symbol: str) -> float:
        ...

    @abstractmethod
    def create_order(
        self,
        symbol: str,
        side: str,
        size_usdt: float,
        leverage: float,
        stop_loss_pct: float,
        take_profit_pct: float,
        comment: str,
    ) -> Order:
        ...

    @abstractmethod
    def get_open_positions(self) -> Dict[str, float]:
        """Return net notional exposure per symbol."""

    def set_price(self, symbol: str, price: float) -> None:
        """Optional override for mock/live adapters."""

    def settle_all(self) -> None:
        """Optional override for paper adapters to settle open positions."""


class PaperExchange(ExchangeAdapter):
    def __init__(
        self,
        initial_cash_usdt: float = 10000.0,
        partial_fill_probability: float = 0.0,
        partial_fill_min_ratio: float = 0.55,
        partial_fill_max_ratio: float = 0.95,
    ):
        self._cash = float(initial_cash_usdt)
        self._positions: Dict[str, float] = {}
        self._entry_prices: Dict[str, float] = {}
        self._position_leverage: Dict[str, float] = {}
        self._price_cache: Dict[str, float] = {}
        self._orders: List[Order] = []
        self._seq = 0
        self._rng_state = 17
        self.partial_fill_probability = max(0.0, min(1.0, float(partial_fill_probability)))
        self.partial_fill_min_ratio = max(0.01, min(0.99, float(partial_fill_min_ratio)))
        self.partial_fill_max_ratio = max(self.partial_fill_min_ratio, min(0.9999, float(partial_fill_max_ratio)))

    @property
    def name(self) -> str:
        return "paper"

    def get_balance(self) -> Dict[str, float]:
        notional_exposure = sum(abs(v) for v in self._positions.values())
        locked_margin = self._locked_margin()
        return {
            "USDT": self._cash,
            "equity_usdt": max(0.0, self._cash + locked_margin + self._unrealized_pnl()),
            "notional_exposure": notional_exposure,
            "position_count": len(self._positions),
            "locked_margin_usdt": locked_margin,
        }

    def _unrealized_pnl(self) -> float:
        total = 0.0
        for symbol, notional in self._positions.items():
            if notional == 0:
                continue
            if symbol not in self._price_cache:
                continue
            price = self._price_cache[symbol]
            entry = self._entry_prices.get(symbol, price)
            direction = 1 if notional > 0 else -1
            base_qty = abs(notional) / entry if entry > 0 else 0.0
            total += direction * (price - entry) * base_qty
        return total

    def set_price(self, symbol: str, price: float) -> None:
        self._price_cache[symbol] = price

    def get_last_price(self, symbol: str) -> float:
        if symbol not in self._price_cache:
            raise KeyError(f"No price for {symbol}")
        return self._price_cache[symbol]

    def _release_margin(self, notional: float, leverage: float) -> float:
        if notional <= 0:
            return 0.0
        return notional / max(leverage, 1.0)

    def _locked_margin(self) -> float:
        total = 0.0
        for symbol, notional in self._positions.items():
            lev = max(self._position_leverage.get(symbol, 1.0), 1.0)
            total += abs(notional) / lev
        return total

    def _random_float(self, a: float = 0.0, b: float = 1.0) -> float:
        self._rng_state = (1103515245 * self._rng_state + 12345) & 0x7fffffff
        return a + (self._rng_state / 0x7fffffff) * (b - a)

    def _simulate_partial_fill_ratio(self) -> float:
        if self.partial_fill_probability <= 0:
            return 1.0
        if self._random_float() > self.partial_fill_probability:
            return 1.0
        return self._random_float(self.partial_fill_min_ratio, self.partial_fill_max_ratio)

    def _build_order(
        self,
        order_id: str,
        symbol: str,
        side: str,
        size_usdt: float,
        leverage: float,
        status: str,
        price: float,
        note: str,
        realized_pnl: float = 0.0,
        requested_size_usdt: float = 0.0,
        expected_price: float = 0.0,
        slippage_bps: float = 0.0,
        retryable: bool = True,
        reject_reason: str = "",
        fee_usdt: float = 0.0,
        fee_rate_bps: float = 0.0,
        gross_realized_pnl: float = 0.0,
    ) -> Order:
        now = datetime.utcnow()
        return Order(
            order_id=order_id,
            symbol=symbol,
            side=str(side),
            size_usdt=float(size_usdt),
            leverage=float(leverage),
            status=status,
            price=float(price),
            created_at=now,
            updated_at=now,
            requested_size_usdt=float(requested_size_usdt),
            expected_price=float(expected_price),
            realized_pnl=float(realized_pnl),
            note=note,
            slippage_bps=float(slippage_bps),
            retryable=bool(retryable),
            reject_reason=str(reject_reason),
            fee_usdt=float(fee_usdt),
            fee_rate_bps=float(fee_rate_bps),
            gross_realized_pnl=float(gross_realized_pnl),
        )

    def create_order(
        self,
        symbol: str,
        side: str,
        size_usdt: float,
        leverage: float,
        stop_loss_pct: float,
        take_profit_pct: float,
        comment: str,
    ) -> Order:
        self._seq += 1
        requested_size = max(0.0, float(size_usdt))
        now = datetime.utcnow()
        expected_price = self.get_last_price(symbol)

        if requested_size <= 0:
            order = self._build_order(
                f"PAPER-{self._seq:06d}",
                symbol,
                side,
                0.0,
                leverage,
                "rejected",
                expected_price,
                "invalid_size",
                0.0,
                requested_size_usdt=requested_size,
                expected_price=expected_price,
                retryable=False,
                reject_reason=RejectReason.INVALID_SIZE.value,
            )
            self._orders.append(order)
            return order

        if side not in {"BUY", "SELL"}:
            order = self._build_order(
                f"PAPER-{self._seq:06d}",
                symbol,
                side,
                0.0,
                leverage,
                "rejected",
                expected_price,
                "unsupported_side",
                0.0,
                requested_size_usdt=requested_size,
                expected_price=expected_price,
                retryable=False,
                reject_reason=RejectReason.UNSUPPORTED_SIDE.value,
            )
            self._orders.append(order)
            return order

        fill_ratio = self._simulate_partial_fill_ratio()
        fill_size = requested_size * fill_ratio
        if fill_size <= 0:
            order = self._build_order(
                f"PAPER-{self._seq:06d}",
                symbol,
                side,
                0.0,
                leverage,
                "rejected",
                expected_price,
                f"partial_fill_zero (request={requested_size:.2f})",
                0.0,
                requested_size_usdt=requested_size,
                expected_price=expected_price,
                retryable=True,
                reject_reason=RejectReason.PARTIAL_FILL_ZERO.value,
            )
            self._orders.append(order)
            return order

        is_partial = fill_ratio < 0.9999
        size_usdt = fill_size

        price = expected_price
        side_sign = 1 if side == "BUY" else -1
        delta_notional = size_usdt * side_sign
        current_notional = self._positions.get(symbol, 0.0)
        current_leverage = self._position_leverage.get(symbol, max(leverage, 1.0))

        # 반대 방향 정리
        realized = 0.0
        if current_notional * side_sign < 0:
            close_abs_notional = min(abs(current_notional), abs(delta_notional))
            if abs(current_notional) > 0 and price > 0:
                entry = self._entry_prices.get(symbol, price)
                close_base = close_abs_notional / max(entry, 1e-9)
                if current_notional > 0:
                    realized += (price - entry) * close_base
                else:
                    realized += (entry - price) * close_base

                self._cash += self._release_margin(close_abs_notional, current_leverage)
                self._cash += realized

            remaining = abs(delta_notional) - close_abs_notional
            if remaining <= 1e-12:
                if abs(current_notional) == close_abs_notional:
                    self._positions.pop(symbol, None)
                    self._entry_prices.pop(symbol, None)
                    self._position_leverage.pop(symbol, None)
                else:
                    remain_notional = abs(current_notional) - close_abs_notional
                    sign = 1.0 if current_notional > 0 else -1.0
                    self._positions[symbol] = sign * remain_notional

                status = "partially_filled" if is_partial else "filled"
                note = comment
                if is_partial:
                    note = f"partial_fill_ratio={fill_ratio:.4f} request={requested_size:.2f} " + note
                order = self._build_order(
                    f"PAPER-{self._seq:06d}",
                    symbol,
                    side,
                    size_usdt,
                    leverage,
                    status,
                    price,
                    note,
                    realized,
                    requested_size_usdt=requested_size,
                    expected_price=expected_price,
                )
                self._orders.append(order)
                return order

            if abs(current_notional) <= close_abs_notional + 1e-12:
                self._positions.pop(symbol, None)
                self._entry_prices.pop(symbol, None)
                self._position_leverage.pop(symbol, None)

            delta_notional = remaining * side_sign

        if current_notional == 0:
            required_margin = self._release_margin(abs(size_usdt), max(leverage, 1.0))
            if required_margin > self._cash:
                order = self._build_order(
                    f"PAPER-{self._seq:06d}",
                    symbol,
                    side,
                    size_usdt if is_partial else 0.0,
                    leverage,
                    "rejected",
                    price,
                    "insufficient_cash_for_margin",
                    0.0,
                    requested_size_usdt=requested_size,
                    expected_price=expected_price,
                    retryable=False,
                    reject_reason=RejectReason.INSUFFICIENT_CASH.value,
                )
                self._orders.append(order)
                return order

            self._cash -= required_margin
            self._positions[symbol] = delta_notional
            self._entry_prices[symbol] = price
            self._position_leverage[symbol] = max(leverage, 1.0)
            status = "partially_filled" if is_partial else "filled"
            note = comment
            if is_partial:
                note = f"partial_fill_ratio={fill_ratio:.4f} request={requested_size:.2f} " + note
            order = self._build_order(
                f"PAPER-{self._seq:06d}",
                symbol,
                side,
                size_usdt,
                leverage,
                status,
                price,
                note,
                realized,
                requested_size_usdt=requested_size,
                expected_price=expected_price,
            )
            self._orders.append(order)
            return order

        same_direction = (current_notional > 0 and side_sign > 0) or (current_notional < 0 and side_sign < 0)
        required_margin = self._release_margin(abs(size_usdt), max(leverage, 1.0))

        if same_direction:
            if required_margin > self._cash:
                order = self._build_order(
                    f"PAPER-{self._seq:06d}",
                    symbol,
                    side,
                    size_usdt,
                    leverage,
                    "rejected",
                    price,
                    "insufficient_cash_for_additional_margin",
                    0.0,
                    requested_size_usdt=requested_size,
                    expected_price=expected_price,
                    retryable=False,
                    reject_reason=RejectReason.INSUFFICIENT_CASH.value,
                )
                self._orders.append(order)
                return order

            new_notional = current_notional + delta_notional
            old_abs = abs(current_notional)
            add_abs = abs(delta_notional)
            old_entry = self._entry_prices.get(symbol, price)
            if old_abs + add_abs > 0:
                new_entry = (old_entry * old_abs + price * add_abs) / (old_abs + add_abs)
            else:
                new_entry = price
            self._positions[symbol] = new_notional
            self._entry_prices[symbol] = new_entry
            self._position_leverage[symbol] = (self._position_leverage.get(symbol, max(leverage, 1.0)) + max(leverage, 1.0)) / 2
            self._cash -= required_margin
            status = "partially_filled" if is_partial else "filled"
            note = comment
            if is_partial:
                note = f"partial_fill_ratio={fill_ratio:.4f} request={requested_size:.2f} " + note
            order = self._build_order(
                f"PAPER-{self._seq:06d}",
                symbol,
                side,
                size_usdt,
                leverage,
                status,
                price,
                note,
                realized,
                requested_size_usdt=requested_size,
                expected_price=expected_price,
            )
            self._orders.append(order)
            return order

        # opposite direction already handled; reverse/re-open below.
        if required_margin > self._cash:
            order = self._build_order(
                f"PAPER-{self._seq:06d}",
                symbol,
                side,
                0.0,
                leverage,
                "rejected",
                price,
                "insufficient_cash_for_margin",
                0.0,
                requested_size_usdt=requested_size,
                expected_price=expected_price,
                retryable=False,
                reject_reason=RejectReason.INSUFFICIENT_CASH.value,
            )
            self._orders.append(order)
            return order

        self._cash -= required_margin
        remaining_notional = abs(delta_notional)
        self._positions[symbol] = side_sign * remaining_notional
        self._entry_prices[symbol] = price
        self._position_leverage[symbol] = max(leverage, 1.0)
        status = "partially_filled" if is_partial else "filled"
        note = comment
        if is_partial:
            note = f"partial_fill_ratio={fill_ratio:.4f} request={requested_size:.2f} " + note
        order = self._build_order(
            f"PAPER-{self._seq:06d}",
            symbol,
            side,
            size_usdt,
            leverage,
            status,
            price,
            note,
            realized,
            requested_size_usdt=requested_size,
            expected_price=expected_price,
        )
        self._orders.append(order)
        return order

    def get_open_positions(self) -> Dict[str, float]:
        return dict(self._positions)

    def settle_all(self) -> None:
        for symbol, notional in list(self._positions.items()):
            if abs(notional) <= 1e-12:
                continue
            price = self._price_cache.get(symbol, self._entry_prices.get(symbol, 0.0))
            entry = self._entry_prices.get(symbol, price)
            if price <= 0 or entry <= 0:
                continue

            leverage = max(self._position_leverage.get(symbol, 1.0), 1.0)
            qty = abs(notional) / max(entry, 1e-9)
            if notional > 0:
                realized = (price - entry) * qty
            else:
                realized = (entry - price) * qty

            self._cash += self._release_margin(abs(notional), leverage)
            self._cash += realized
            self._positions.pop(symbol, None)
            self._entry_prices.pop(symbol, None)
            self._position_leverage.pop(symbol, None)


class CCXTExchangeAdapter(ExchangeAdapter):
    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: str = "",
        api_secret: str = "",
        password: str | None = None,
        testnet: bool = True,
    ):
        try:
            import ccxt
        except Exception as exc:
            raise RuntimeError("ccxt 패키지가 필요합니다. pip install ccxt") from exc

        options: Dict[str, object] = {
            "enableRateLimit": True,
            "options": {
                "defaultType": "future",
                "defaultSubType": "linear",
            },
        }

        params = {
            "apiKey": api_key,
            "secret": api_secret,
        }
        if password:
            params["password"] = password

        self.client = getattr(ccxt, exchange_id)({**options, **params})
        if hasattr(self.client, "set_sandbox_mode"):
            try:
                self.client.set_sandbox_mode(testnet)
            except Exception:
                pass
        self._last_price_cache: Dict[str, float] = {}

    @property
    def name(self) -> str:
        return self.client.id

    def get_balance(self) -> Dict[str, float]:
        balances = {}
        for params in [{"type": "future"}, {"defaultType": "future"}, {}]:
            try:
                balances = self.client.fetch_balance(params)
                if balances:
                    break
            except Exception:
                continue
        total = balances.get("total", {})
        usdt = total.get("USDT", 0.0)
        positions = []
        if hasattr(self.client, "fetch_positions"):
            for params in [{"type": "future"}, {}]:
                try:
                    positions = self.client.fetch_positions(None, params)
                    break
                except Exception:
                    continue
        notional_exposure = 0.0
        for row in positions:
            notional_exposure += abs(float(row.get("notional", 0.0)))

        return {
            "USDT": usdt,
            "equity_usdt": float(total.get("USDT", 0.0)),
            "notional_exposure": notional_exposure,
            "position_count": len(positions),
        }

    def get_last_price(self, symbol: str) -> float:
        price = self.client.fetch_ticker(symbol)["last"]
        self._last_price_cache[symbol] = float(price)
        return float(price)

    def _fetch_positions_safe(self, symbol: str | None = None) -> list[dict]:
        if not hasattr(self.client, "fetch_positions"):
            return []
        symbols = [symbol] if symbol else None
        for params in [{"type": "future"}, {}]:
            try:
                return self.client.fetch_positions(symbols, params)
            except TypeError:
                try:
                    if symbols:
                        return self.client.fetch_positions(symbols)
                    return self.client.fetch_positions()
                except Exception:
                    continue
            except Exception:
                continue
        return []

    def _signed_notional(self, row: dict) -> float:
        notional = self._to_float(row.get("notional"))
        if abs(notional) > 0:
            return notional

        contracts = self._to_float(row.get("contracts"))
        price = self._to_float(row.get("markPrice") or row.get("entryPrice") or row.get("avgPrice"))
        side_raw = str(row.get("side") or row.get("positionSide") or "").strip().lower()
        sign = 0.0
        if "long" in side_raw or "buy" in side_raw:
            sign = 1.0
        elif "short" in side_raw or "sell" in side_raw:
            sign = -1.0
        elif contracts > 0:
            sign = 1.0
        elif contracts < 0:
            sign = -1.0
        if sign == 0.0:
            return 0.0
        return sign * abs(contracts) * max(price, 0.0)

    def _symbol_net_notional(self, symbol: str) -> float:
        total = 0.0
        for row in self._fetch_positions_safe(symbol):
            row_symbol = str(row.get("symbol") or "")
            if row_symbol and row_symbol != symbol:
                continue
            total += self._signed_notional(row)
        return total

    def _amount_to_precision_safe(self, symbol: str, amount: float) -> float:
        raw = max(float(amount or 0.0), 0.0)
        if raw <= 0:
            return 0.0
        try:
            precise = self.client.amount_to_precision(symbol, raw)
            return self._to_float(precise)
        except Exception:
            return raw

    def _create_market_order_with_fallback(self, symbol: str, side: str, amount: float, reduce_only: bool) -> dict:
        params_candidates: list[dict] = []
        base = {}
        if str(self.client.id).lower() == "bybit":
            base["positionIdx"] = 0

        if reduce_only:
            params_candidates.append({**base, "reduceOnly": True})
            params_candidates.append({**base, "reduce_only": True})
        params_candidates.append(base)

        last_exc: Exception | None = None
        for params in params_candidates:
            try:
                return self.client.create_order(
                    symbol=symbol,
                    type="market",
                    side=side.lower(),
                    amount=amount,
                    params=params,
                )
            except Exception as exc:
                last_exc = exc
                continue
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("order create failed without exception detail")

    @staticmethod
    def _extract_reject_reason(raw: Dict[str, object]) -> str:
        candidates = []
        for key in ["msg", "message", "error", "code"]:
            value = raw.get(key)
            if value:
                candidates.append(str(value))
        info = raw.get("info")
        if isinstance(info, dict):
            for key in ["msg", "message", "error", "code"]:
                value = info.get(key)
                if value:
                    candidates.append(str(value))
        return " ".join(candidates).strip()

    @staticmethod
    def _to_float(value: object) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _split_symbol_assets(symbol: str) -> tuple[str, str]:
        raw = str(symbol or "").upper()
        if "/" in raw:
            left, right = raw.split("/", 1)
            quote = right.split(":", 1)[0]
            return left.strip(), quote.strip()
        for quote in ["USDT", "USDC", "USD", "BUSD"]:
            if raw.endswith(quote) and len(raw) > len(quote):
                return raw[: -len(quote)], quote
        return raw, ""

    @staticmethod
    def _normalize_currency(value: object) -> str:
        return str(value or "").strip().upper()

    def _fee_cost_to_usdt(self, cost: float, currency: str, symbol: str, avg_price: float) -> float:
        fee_cost = max(self._to_float(cost), 0.0)
        if fee_cost <= 0:
            return 0.0
        cur = self._normalize_currency(currency)
        base, quote = self._split_symbol_assets(symbol)
        if cur in {"", "USDT", "USD", quote}:
            return fee_cost
        if cur == base and avg_price > 0:
            return fee_cost * avg_price
        return fee_cost

    def _extract_fee_usdt(self, order: Dict[str, object], symbol: str, avg_price: float) -> float:
        total = 0.0
        fee = order.get("fee")
        if isinstance(fee, dict):
            total += self._fee_cost_to_usdt(
                cost=fee.get("cost"),
                currency=str(fee.get("currency") or ""),
                symbol=symbol,
                avg_price=avg_price,
            )
        fees = order.get("fees")
        if isinstance(fees, list):
            for item in fees:
                if not isinstance(item, dict):
                    continue
                total += self._fee_cost_to_usdt(
                    cost=item.get("cost"),
                    currency=str(item.get("currency") or ""),
                    symbol=symbol,
                    avg_price=avg_price,
                )

        info = order.get("info")
        if isinstance(info, dict):
            if total <= 0:
                for key in ["cumExecFee", "execFee", "fee", "commission"]:
                    value = self._to_float(info.get(key))
                    if value > 0:
                        fee_currency = str(info.get("feeCurrency") or info.get("commissionAsset") or "")
                        total = self._fee_cost_to_usdt(value, fee_currency, symbol, avg_price)
                        break
            if total <= 0:
                nested = info.get("result")
                if isinstance(nested, dict):
                    for key in ["cumExecFee", "execFee", "fee", "commission"]:
                        value = self._to_float(nested.get(key))
                        if value > 0:
                            fee_currency = str(nested.get("feeCurrency") or nested.get("commissionAsset") or "")
                            total = self._fee_cost_to_usdt(value, fee_currency, symbol, avg_price)
                            break
        return max(total, 0.0)

    def _extract_realized_pnl(self, order: Dict[str, object]) -> float:
        for key in ["realizedPnl", "realized_pnl", "closedPnl", "closed_pnl", "pnl", "profit"]:
            value = self._to_float(order.get(key))
            if abs(value) > 0:
                return value
        info = order.get("info")
        if isinstance(info, dict):
            for key in ["realizedPnl", "realized_pnl", "closedPnl", "closed_pnl", "pnl", "profit"]:
                value = self._to_float(info.get(key))
                if abs(value) > 0:
                    return value
            nested = info.get("result")
            if isinstance(nested, dict):
                for key in ["realizedPnl", "realized_pnl", "closedPnl", "closed_pnl", "pnl", "profit"]:
                    value = self._to_float(nested.get(key))
                    if abs(value) > 0:
                        return value
        return 0.0

    def create_order(
        self,
        symbol: str,
        side: str,
        size_usdt: float,
        leverage: float,
        stop_loss_pct: float,
        take_profit_pct: float,
        comment: str,
    ) -> Order:
        now = datetime.utcnow()
        expected_price = 0.0
        try:
            if "set_position_mode" in dir(self.client):
                try:
                    self.client.set_position_mode(False, symbol)
                except Exception:
                    pass
            if "set_leverage" in dir(self.client):
                try:
                    self.client.set_leverage(int(max(1, round(leverage))), symbol)
                except TypeError:
                    try:
                        self.client.set_leverage(int(max(1, round(leverage))))
                    except Exception:
                        pass
                except Exception:
                    pass

            expected_price = self.get_last_price(symbol)
            raw_amount = max(size_usdt / max(expected_price, 1e-9), 0.0)
            amount = self._amount_to_precision_safe(symbol, raw_amount)
            if amount <= 0:
                return Order(
                    order_id="",
                    symbol=symbol,
                    side=str(side),
                    size_usdt=0.0,
                    requested_size_usdt=float(size_usdt),
                    leverage=float(leverage),
                    status="rejected",
                    price=float(expected_price),
                    expected_price=float(expected_price),
                    created_at=now,
                    updated_at=now,
                    note="live_order_error: amount_to_precision <= 0",
                    slippage_bps=0.0,
                    retryable=False,
                    reject_reason=RejectReason.INVALID_ORDER_VALUE.value,
                )

            net_notional = self._symbol_net_notional(symbol)
            reduce_only = False
            side_norm = str(side or "").strip().upper()
            if net_notional > 0 and side_norm == "SELL":
                reduce_only = True
            elif net_notional < 0 and side_norm == "BUY":
                reduce_only = True

            order = self._create_market_order_with_fallback(
                symbol=symbol,
                side=side,
                amount=amount,
                reduce_only=reduce_only,
            )

            raw_status = str(order.get("status", "rejected")).lower()
            filled_base = self._to_float(order.get("filled"))
            average_price = self._to_float(order.get("average") or expected_price)

            if raw_status in {"closed", "filled"}:
                status = "filled"
            elif raw_status in {"partially_filled", "open"}:
                status = "partially_filled" if filled_base > 0 else "rejected"
            elif raw_status in {"canceled", "cancelled", "expired", "rejected", "failed", "error"}:
                status = "rejected"
            else:
                status = "new"

            if filled_base > 0 and average_price > 0:
                filled_usdt = filled_base * average_price
            else:
                filled_usdt = self._to_float(order.get("cost"))
            if filled_usdt <= 0 and status in {"filled", "partially_filled"}:
                filled_usdt = float(size_usdt)

            slippage_bps = 0.0
            if expected_price > 0 and average_price > 0:
                slippage_bps = ((average_price - expected_price) / expected_price) * 10000.0

            fee_usdt = self._extract_fee_usdt(order, symbol=symbol, avg_price=average_price)
            fee_rate_bps = (fee_usdt / filled_usdt * 10000.0) if filled_usdt > 0 and fee_usdt > 0 else 0.0
            gross_realized_pnl = self._extract_realized_pnl(order)

            retryable = status != "rejected"
            reject_reason = RejectReason.EXCHANGE_REJECT.value
            if status == "rejected":
                raw_reason = self._extract_reject_reason(order)
                lower = raw_reason.lower()
                if "insufficient" in lower:
                    retryable = False
                    reject_reason = RejectReason.INSUFFICIENT_CASH.value
                elif "invalid" in lower:
                    retryable = False
                    reject_reason = RejectReason.INVALID_ORDER.value
                elif "auth" in lower or "api" in lower:
                    retryable = False
                    reject_reason = RejectReason.AUTH_ERROR.value
                elif "timeout" in lower or "network" in lower:
                    reject_reason = RejectReason.NETWORK_ERROR.value
                else:
                    reject_reason = raw_reason or RejectReason.EXCHANGE_REJECT.value

            return Order(
                order_id=str(order.get("id", "")),
                symbol=symbol,
                side=str(side),
                size_usdt=float(filled_usdt),
                requested_size_usdt=float(size_usdt),
                leverage=float(leverage),
                status=status,
                price=float(order.get("average", expected_price)),
                expected_price=float(expected_price),
                created_at=now,
                updated_at=now,
                realized_pnl=float(gross_realized_pnl),
                note=comment,
                slippage_bps=slippage_bps,
                retryable=retryable,
                reject_reason=reject_reason,
                fee_usdt=fee_usdt,
                fee_rate_bps=fee_rate_bps,
                gross_realized_pnl=float(gross_realized_pnl),
            )
        except Exception as exc:
            reason = RejectReason.from_text(str(exc)).value
            return Order(
                order_id="",
                symbol=symbol,
                side=str(side),
                size_usdt=0.0,
                requested_size_usdt=float(size_usdt),
                leverage=float(leverage),
                status="rejected",
                price=self._last_price_cache.get(symbol, 0.0),
                expected_price=self._last_price_cache.get(symbol, 0.0),
                created_at=now,
                updated_at=now,
                note=f"live_order_error: {exc}",
                slippage_bps=0.0,
                retryable=RejectReason.from_text(str(exc)).is_retryable(),
                reject_reason=reason,
            )

    def get_open_positions(self) -> Dict[str, float]:
        positions = self._fetch_positions_safe()
        out: Dict[str, float] = {}
        for row in positions:
            symbol = row.get("symbol")
            if not symbol:
                continue
            notional = self._signed_notional(row)
            if abs(notional) <= 0:
                continue
            out[symbol] = float(out.get(symbol, 0.0)) + float(notional)
        return out



def _looks_like_env_ref(raw: str) -> bool:
    if not isinstance(raw, str):
        return False
    s = raw.strip()
    return (s.startswith("${") and s.endswith("}")) or (s.startswith("$") and len(s) > 1)


def _resolve_secret(raw: str, env_fallback: str | None = None) -> str:
    source = (raw or "").strip()
    if env_fallback:
        env_value = os.getenv(env_fallback)
        if env_value:
            return env_value

    if _looks_like_env_ref(source):
        if source.startswith("${") and source.endswith("}"):
            key = source[2:-1].strip()
        else:
            key = source[1:].strip()
        return os.getenv(key, source)

    return source


def build_exchange(exchange_cfg: ExchangeConfig) -> ExchangeAdapter:
    if exchange_cfg.type.lower() in {"paper", "mock"}:
        return PaperExchange(initial_cash_usdt=exchange_cfg.initial_cash_usdt, partial_fill_probability=exchange_cfg.partial_fill_probability, partial_fill_min_ratio=exchange_cfg.partial_fill_min_ratio, partial_fill_max_ratio=exchange_cfg.partial_fill_max_ratio)

    api_key = _resolve_secret(exchange_cfg.api_key, exchange_cfg.api_key_env)
    api_secret = _resolve_secret(exchange_cfg.api_secret, exchange_cfg.api_secret_env)
    password = _resolve_secret(exchange_cfg.api_passphrase, exchange_cfg.api_passphrase_env)

    if not api_key or not api_secret:
        raise RuntimeError(
            "실거래 연동에서는 API_KEY/API_SECRET(또는 환경 변수 참조)가 필요합니다."
        )

    exchange_id = str(exchange_cfg.type or "").strip()
    normalized = exchange_id.lower()
    if normalized in {"binance-futures", "binance_usdm", "binanceusdm"}:
        exchange_id = "binanceusdm"
    elif normalized in {"bybit-usdt", "bybit_usdt", "bybitusdt"}:
        exchange_id = "bybit"

    return CCXTExchangeAdapter(
        exchange_id=exchange_id,
        api_key=api_key,
        api_secret=api_secret,
        password=password,
        testnet=exchange_cfg.testnet,
    )


