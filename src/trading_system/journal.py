from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .domain import OrderStatus, StrategySignal, TradeEvent


class TradeJournal:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self._lock = threading.Lock()
        self._ensure_schema()

    @staticmethod
    def _success_statuses() -> tuple[str, ...]:
        return (OrderStatus.FILLED.value, OrderStatus.PARTIALLY_FILLED.value)

    @staticmethod
    def _json_default(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def _ensure_executions_columns(self, cur) -> None:
        cur.execute("PRAGMA table_info(executions)")
        existing = {row[1] for row in cur.fetchall()}
        required = {
            "requested_size_usdt": "REAL NOT NULL DEFAULT 0.0",
            "expected_fill_price": "REAL",
            "actual_fill_price": "REAL",
            "slippage_bps": "REAL",
            "fee_bps": "REAL",
            "fee_usdt": "REAL NOT NULL DEFAULT 0.0",
            "gross_realized_pnl": "REAL NOT NULL DEFAULT 0.0",
            "attempt_count": "INTEGER NOT NULL DEFAULT 1",
            "is_partial": "INTEGER NOT NULL DEFAULT 0",
            "reject_reason": "TEXT",
        }
        for col, ddl in required.items():
            if col not in existing:
                cur.execute(f"ALTER TABLE executions ADD COLUMN {col} {ddl}")

    def _ensure_schema(self) -> None:
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS signals(
                    id TEXT PRIMARY KEY,
                    ts TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    expected_edge_bps REAL NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS executions(
                    id TEXT PRIMARY KEY,
                    signal_id TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    order_status TEXT NOT NULL,
                    requested_size_usdt REAL NOT NULL,
                    size_usdt REAL NOT NULL,
                    leverage REAL NOT NULL,
                    expected_fill_price REAL,
                    actual_fill_price REAL,
                    slippage_bps REAL,
                    fee_bps REAL,
                    fee_usdt REAL NOT NULL DEFAULT 0.0,
                    gross_realized_pnl REAL NOT NULL DEFAULT 0.0,
                    attempt_count INTEGER NOT NULL,
                    is_partial INTEGER NOT NULL,
                    filled_price REAL,
                    realized_pnl REAL,
                    reject_reason TEXT,
                    note TEXT,
                    FOREIGN KEY(signal_id) REFERENCES signals(id)
            )
                """
            )
            self._ensure_executions_columns(cur)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    suggestion TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS risk_events(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    action TEXT NOT NULL,
                    previous_reason TEXT,
                    current_reason TEXT,
                    note TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS auto_learning_events(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    source TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    cycle INTEGER NOT NULL,
                    strategy TEXT NOT NULL,
                    action TEXT NOT NULL,
                    weight_before REAL,
                    weight_after REAL,
                    enabled_after INTEGER,
                    confidence REAL,
                    reason TEXT,
                    meta TEXT
                )
                """
            )
            self.conn.commit()

    def _make_signal_id(self, signal: StrategySignal) -> str:
        raw = f"{signal.timestamp.isoformat()}|{signal.strategy_id}|{signal.symbol}|{signal.direction}|{signal.expected_edge_bps}|{signal.comment}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def _signal_payload(self, signal: StrategySignal) -> str:
        payload = asdict(signal)
        payload["direction"] = signal.direction.value
        payload["meta"] = signal.meta
        return json.dumps(payload, ensure_ascii=False, default=self._json_default)

    def log_signal(self, signal: StrategySignal) -> str:
        signal_id = self._make_signal_id(signal)
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO signals VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    signal_id,
                    signal.timestamp.isoformat(),
                    signal.strategy_id,
                    signal.symbol,
                    signal.direction.value,
                    signal.confidence,
                    signal.expected_edge_bps,
                    self._signal_payload(signal),
                ),
            )
            self.conn.commit()
        return signal_id

    def log_execution(self, signal: StrategySignal, event: TradeEvent, signal_id: Optional[str] = None) -> None:
        with self._lock:
            cur = self.conn.cursor()
            sid = signal_id or self._make_signal_id(signal)
            ts = signal.timestamp.isoformat() if isinstance(signal.timestamp, datetime) else datetime.utcnow().isoformat()
            status_value = event.status.value if isinstance(event.status, OrderStatus) else str(event.status)
            requested_size = event.requested_size_usdt if event.requested_size_usdt is not None else event.size_usdt or 0.0
            requested_size = float(requested_size if requested_size is not None else 0.0)
            cur.execute(
                "INSERT OR REPLACE INTO executions(id, signal_id, ts, symbol, side, order_status, requested_size_usdt, size_usdt, leverage, expected_fill_price, actual_fill_price, slippage_bps, fee_bps, fee_usdt, gross_realized_pnl, attempt_count, is_partial, filled_price, realized_pnl, reject_reason, note) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event.order_id or f"{sid}-none",
                    sid,
                    ts,
                    signal.symbol,
                    str(signal.direction.value),
                    status_value,
                    requested_size,
                    float(event.size_usdt or 0.0),
                    float(event.leverage or 0.0),
                    event.expected_fill_price,
                    event.actual_fill_price,
                    event.slippage_bps,
                    event.fee_bps,
                    float(event.fee_usdt or 0.0),
                    float(event.gross_realized_pnl or 0.0),
                    int(event.attempt_count or 1),
                    1 if bool(event.is_partial) else 0,
                    event.filled_price if event.filled_price is not None else 0.0,
                    event.realized_pnl if event.realized_pnl is not None else 0.0,
                    event.reject_reason or "",
                    signal.comment,
                ),
            )
            self.conn.commit()

    def record_feedback(self, strategy: str, metric_name: str, metric_value: float, suggestion: Optional[str] = None):
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO feedback(ts, strategy, metric_name, metric_value, suggestion) VALUES(?, ?, ?, ?, ?)",
                (datetime.utcnow().isoformat(), strategy, metric_name, metric_value, suggestion),
            )
            self.conn.commit()


    def record_risk_event(
        self,
        action: str,
        previous_reason: Optional[str] = None,
        current_reason: Optional[str] = None,
        note: Optional[str] = None,
    ) -> int:
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                INSERT INTO risk_events(ts, action, previous_reason, current_reason, note)
                VALUES(?, ?, ?, ?, ?)
                """,
                (
                    datetime.utcnow().isoformat(),
                    action,
                    previous_reason,
                    current_reason,
                    note,
                )
            )
            self.conn.commit()
            return int(cur.lastrowid)

    def recent_risk_events(self, limit: int = 20) -> List[dict]:
        limit = max(1, min(200, int(limit)))
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT id, ts, action, previous_reason, current_reason, note
                FROM risk_events
                ORDER BY id DESC LIMIT ?
                """,
                (limit,)
            )
            rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "ts": row[1],
                "action": row[2],
                "previous_reason": row[3],
                "current_reason": row[4],
                "note": row[5],
            }
            for row in rows
        ]

    def record_auto_learning_event(
        self,
        source: str,
        mode: str,
        cycle: int,
        strategy: str,
        action: str,
        weight_before: float | None = None,
        weight_after: float | None = None,
        enabled_after: bool | None = None,
        confidence: float | None = None,
        reason: str | None = None,
        meta: Dict[str, Any] | None = None,
    ) -> int:
        payload = json.dumps(meta or {}, ensure_ascii=False)
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                INSERT INTO auto_learning_events(
                    ts, source, mode, cycle, strategy, action,
                    weight_before, weight_after, enabled_after,
                    confidence, reason, meta
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.utcnow().isoformat(),
                    str(source or "unknown"),
                    str(mode or "unknown"),
                    int(cycle or 0),
                    str(strategy or ""),
                    str(action or "hold"),
                    weight_before,
                    weight_after,
                    None if enabled_after is None else (1 if enabled_after else 0),
                    confidence,
                    reason,
                    payload,
                ),
            )
            self.conn.commit()
            return int(cur.lastrowid)

    def recent_auto_learning_events(
        self,
        limit: int = 100,
        source: str | None = None,
    ) -> List[dict]:
        limit = max(1, min(1000, int(limit)))
        with self._lock:
            cur = self.conn.cursor()
            if source:
                cur.execute(
                    """
                    SELECT id, ts, source, mode, cycle, strategy, action,
                           weight_before, weight_after, enabled_after, confidence, reason, meta
                    FROM auto_learning_events
                    WHERE source = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (source, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT id, ts, source, mode, cycle, strategy, action,
                           weight_before, weight_after, enabled_after, confidence, reason, meta
                    FROM auto_learning_events
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            rows = cur.fetchall()

        out: List[dict] = []
        for row in rows:
            meta_raw = row[12] or "{}"
            try:
                meta_value = json.loads(meta_raw)
            except Exception:
                meta_value = {}
            out.append(
                {
                    "id": row[0],
                    "ts": row[1],
                    "source": row[2],
                    "mode": row[3],
                    "cycle": row[4],
                    "strategy": row[5],
                    "action": row[6],
                    "weight_before": row[7],
                    "weight_after": row[8],
                    "enabled_after": None if row[9] is None else bool(row[9]),
                    "confidence": row[10],
                    "reason": row[11],
                    "meta": meta_value,
                }
            )
        return out

    def recent_executions(self, strategy: Optional[str] = None, limit: int = 100) -> List[tuple]:
        with self._lock:
            if strategy:
                cur = self.conn.cursor()
                cur.execute(
                    """
                    SELECT e.* FROM executions e
                    JOIN signals s ON e.signal_id = s.id
                    WHERE s.strategy = ?
                    ORDER BY e.ts DESC LIMIT ?
                    """,
                    (strategy, limit),
                )
                return cur.fetchall()

            cur = self.conn.cursor()
            cur.execute("SELECT * FROM executions ORDER BY ts DESC LIMIT ?", (limit,))
            return cur.fetchall()

    def strategy_signal_rows(
        self,
        limit: int = 200,
        since_ts: Optional[str] = None,
    ) -> List[tuple]:
        success_statuses = ",".join([f"'{x}'" for x in self._success_statuses()])
        with self._lock:
            cur = self.conn.cursor()
            if since_ts is None:
                cur.execute(
                    f"""
                    SELECT s.strategy, e.realized_pnl
                    FROM executions e
                    JOIN signals s ON e.signal_id = s.id
                    WHERE e.order_status IN ({success_statuses})
                    ORDER BY e.ts DESC LIMIT ?
                    """,
                    (limit,),
                )
            else:
                cur.execute(
                    f"""
                    SELECT s.strategy, e.realized_pnl
                    FROM executions e
                    JOIN signals s ON e.signal_id = s.id
                    WHERE e.order_status IN ({success_statuses}) AND e.ts >= ?
                    ORDER BY e.ts DESC LIMIT ?
                    """,
                    (since_ts, limit),
                )
            return cur.fetchall()

    def today_performance(self) -> tuple[float, int, int]:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        success_statuses = ",".join([f"'{x}'" for x in self._success_statuses()])
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                f"""
                SELECT realized_pnl
                FROM executions
                WHERE order_status IN ({success_statuses}) AND ts >= ?
                ORDER BY ts DESC
                """,
                (today_start,),
            )
            rows = [r[0] if r[0] is not None else 0.0 for r in cur.fetchall()]

        pnl = sum(float(v) for v in rows)
        trades = len(rows)
        consecutive_losses = 0
        for value in rows:
            if value < 0:
                consecutive_losses += 1
                continue
            break
        return pnl, trades, consecutive_losses

    def latest_filled_at(self) -> Optional[str]:
        success_statuses = ",".join([f"'{x}'" for x in self._success_statuses()])
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(f"SELECT ts FROM executions WHERE order_status IN ({success_statuses}) ORDER BY ts DESC LIMIT 1")
            row = cur.fetchone()
            return row[0] if row else None

    def latest_filled_by_symbol(self) -> Dict[str, str]:
        success_statuses = ",".join([f"'{x}'" for x in self._success_statuses()])
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                f"""
                SELECT symbol, MAX(ts) AS last_ts
                FROM executions
                WHERE order_status IN ({success_statuses})
                GROUP BY symbol
                """
            )
            rows = cur.fetchall()
        out: Dict[str, str] = {}
        for symbol, ts in rows:
            if not symbol or not ts:
                continue
            out[str(symbol)] = str(ts)
        return out

    def execution_summary(
        self,
        limit: int = 20,
        status: str | None = None,
        reject_reason: str | None = None,
        is_partial: bool | None = None,
    ) -> List[dict]:
        limit = max(1, min(100000, int(limit)))
        filters = []
        params: list[object] = []
        if status:
            filters.append("e.order_status = ?")
            params.append(status)
        if reject_reason:
            filters.append("e.reject_reason = ?")
            params.append(reject_reason)
        if is_partial is not None:
            filters.append("e.is_partial = ?")
            params.append(1 if bool(is_partial) else 0)

        where_clause = ""
        if filters:
            where_clause = " WHERE " + " AND ".join(filters)

        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                f"""
                SELECT e.ts, s.strategy, e.symbol, e.side, e.order_status,
                       e.requested_size_usdt, e.size_usdt, e.leverage,
                       e.expected_fill_price, e.actual_fill_price, e.slippage_bps,
                       e.fee_bps, e.fee_usdt, e.gross_realized_pnl,
                       e.filled_price, e.attempt_count, e.is_partial, e.realized_pnl,
                       e.reject_reason, e.note
                FROM executions e
                LEFT JOIN signals s ON e.signal_id = s.id
                {where_clause}
                ORDER BY e.ts DESC
                LIMIT ?
                """,
                (*params, limit),
            )
            rows = cur.fetchall()

        return [
            {
                "ts": ts,
                "strategy": strategy,
                "symbol": symbol,
                "side": side,
                "order_status": event_status,
                "requested_size_usdt": requested_size_usdt,
                "size_usdt": size_usdt,
                "leverage": leverage,
                "expected_fill_price": expected_fill_price,
                "actual_fill_price": actual_fill_price,
                "slippage_bps": slippage_bps,
                "fee_bps": fee_bps,
                "fee_usdt": fee_usdt,
                "gross_realized_pnl": gross_realized_pnl,
                "filled_price": filled_price,
                "attempt_count": attempt_count,
                "is_partial": bool(row_is_partial),
                "realized_pnl": realized_pnl,
                "reject_reason": row_reject_reason,
                "note": note,
            }
            for ts, strategy, symbol, side, event_status, requested_size_usdt, size_usdt, leverage,
            expected_fill_price, actual_fill_price, slippage_bps, fee_bps, fee_usdt, gross_realized_pnl,
            filled_price, attempt_count, row_is_partial,
            realized_pnl, row_reject_reason, note in rows
        ]

    def reject_reason_statistics(self, limit: int = 200) -> Dict[str, Any]:
        limit = max(1, min(500, int(limit)))
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                f"""
                SELECT e.order_status, COALESCE(NULLIF(TRIM(e.reject_reason), ''), 'unknown_reject')
                FROM executions e
                ORDER BY e.ts DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall()

        total_count = len(rows)
        rejected_count = 0
        reason_counter: Dict[str, int] = {}
        status_counter: Dict[str, int] = {}

        for order_status, reject_reason in rows:
            status = str(order_status)
            status_counter[status] = status_counter.get(status, 0) + 1
            if status in self._success_statuses():
                continue

            rejected_count += 1
            reason = str(reject_reason or "unknown_reject")
            reason_counter[reason] = reason_counter.get(reason, 0) + 1

        reasons = [
            {
                "reason": reason,
                "count": count,
                "ratio": count / rejected_count if rejected_count > 0 else 0.0,
            }
            for reason, count in reason_counter.items()
        ]
        reasons.sort(key=lambda x: (x["count"], x["reason"]), reverse=True)

        return {
            "total_executions": total_count,
            "rejected_executions": rejected_count,
            "rejected_rate": rejected_count / total_count if total_count > 0 else 0.0,
            "status_counts": status_counter,
            "reasons": reasons,
            "limit": limit,
        }
    def strategy_stats(self, limit: int = 20) -> List[dict]:
        success_statuses = ",".join([f"'{x}'" for x in self._success_statuses()])
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                f"""
                SELECT s.strategy,
                       COUNT(*) AS trades,
                       SUM(CASE WHEN e.realized_pnl > 0 THEN 1 ELSE 0 END) AS wins,
                       SUM(e.realized_pnl) AS total_pnl
                FROM executions e
                JOIN signals s ON e.signal_id = s.id
                WHERE e.order_status IN ({success_statuses})
                GROUP BY s.strategy
                ORDER BY total_pnl DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall()

        return [
            {
                "strategy": strategy,
                "trades": trades,
                "wins": wins,
                "win_rate": (wins / trades) if trades else 0.0,
                "total_pnl": total_pnl or 0.0,
            }
            for strategy, trades, wins, total_pnl in rows
        ]

    def close(self) -> None:
        with self._lock:
            self.conn.close()





