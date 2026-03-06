from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from dataclasses import asdict
from datetime import datetime, timedelta
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
            "regime_label": "TEXT",
            "entry_rationale": "TEXT",
            "market_state": "TEXT",
            "slippage_cause": "TEXT",
            "signal_meta": "TEXT",
        }
        for col, ddl in required.items():
            if col not in existing:
                try:
                    cur.execute(f"ALTER TABLE executions ADD COLUMN {col} {ddl}")
                except sqlite3.OperationalError as exc:
                    if "duplicate column name" in str(exc).lower():
                        continue
                    raise

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
                    regime_label TEXT,
                    entry_rationale TEXT,
                    market_state TEXT,
                    slippage_cause TEXT,
                    signal_meta TEXT,
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
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS auto_learning_proposals(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    source TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    cycle INTEGER NOT NULL,
                    strategy TEXT NOT NULL,
                    action TEXT NOT NULL,
                    current_weight REAL,
                    suggested_weight REAL,
                    confidence REAL,
                    reason TEXT,
                    status TEXT NOT NULL,
                    decision_note TEXT,
                    applied_event_id INTEGER,
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

    def _signal_meta_text(self, signal: StrategySignal) -> str:
        try:
            return json.dumps(signal.meta or {}, ensure_ascii=False, default=self._json_default)
        except Exception:
            return "{}"

    @staticmethod
    def _regime_label_from_meta(meta: Dict[str, Any]) -> str:
        if not isinstance(meta, dict):
            return ""
        for key in ["regime", "regime_label"]:
            raw = str(meta.get(key) or "").strip()
            if raw:
                return raw
        state = meta.get("market_state")
        if isinstance(state, dict):
            raw = str(state.get("regime") or "").strip()
            if raw:
                return raw
        return ""

    @staticmethod
    def _entry_rationale_from_meta(signal: StrategySignal) -> str:
        meta = signal.meta if isinstance(signal.meta, dict) else {}
        rationale = meta.get("entry_rationale")
        if isinstance(rationale, dict):
            summary = str(rationale.get("summary") or "").strip()
            if summary:
                return summary
            factors = rationale.get("factors")
            if isinstance(factors, list):
                out = " / ".join([str(x).strip() for x in factors if str(x).strip()])
                if out:
                    return out[:700]
        if isinstance(rationale, str) and rationale.strip():
            return rationale.strip()[:700]
        return str(signal.comment or "").strip()[:700]

    @staticmethod
    def _market_state_from_meta(signal: StrategySignal, regime_label: str) -> str:
        meta = signal.meta if isinstance(signal.meta, dict) else {}
        state = meta.get("market_state")
        if isinstance(state, dict):
            payload = dict(state)
            if regime_label and not payload.get("regime"):
                payload["regime"] = regime_label
            try:
                return json.dumps(payload, ensure_ascii=False)
            except Exception:
                pass

        payload: Dict[str, Any] = {}
        for key in [
            "regime",
            "momentum",
            "volatility",
            "spread_bps",
            "funding_rate",
            "kalman_trend_score",
            "kalman_innovation_z",
            "kalman_uncertainty",
        ]:
            if key in meta:
                payload[key] = meta.get(key)
        if regime_label and "regime" not in payload:
            payload["regime"] = regime_label
        try:
            return json.dumps(payload, ensure_ascii=False)
        except Exception:
            return "{}"

    @staticmethod
    def _slippage_cause(signal: StrategySignal, event: TradeEvent) -> str:
        status_value = event.status.value if isinstance(event.status, OrderStatus) else str(event.status or "")
        status_value = status_value.lower()
        if status_value in {"rejected", "cancelled"}:
            reason = str(event.reject_reason or "").strip()
            return f"rejected:{reason or 'unknown'}"

        meta = signal.meta if isinstance(signal.meta, dict) else {}
        spread_est = abs(float(meta.get("spread_bps", signal.slippage_estimate_bps) or signal.slippage_estimate_bps or 0.0))
        volatility = abs(float(meta.get("volatility", 0.0) or 0.0))
        kalman_shock = abs(float(meta.get("kalman_innovation_z", 0.0) or 0.0))
        slip = abs(float(event.slippage_bps or 0.0))
        attempts = max(1, int(event.attempt_count or 1))

        if bool(event.is_partial):
            return "partial_fill_liquidity"
        if attempts > 1 and slip >= max(6.0, spread_est * 0.4):
            return "retry_requote_latency"
        if slip <= max(3.0, spread_est * 0.35):
            return "within_expected_spread"
        if kalman_shock >= 3.0:
            return "kalman_shock"
        if volatility >= 0.035:
            return "high_volatility"
        if spread_est >= 20.0:
            return "wide_spread"
        if slip >= 40.0:
            return "market_impact"
        return "normal_variation"

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
            regime_label = self._regime_label_from_meta(signal.meta if isinstance(signal.meta, dict) else {})
            entry_rationale = self._entry_rationale_from_meta(signal)
            market_state = self._market_state_from_meta(signal, regime_label=regime_label)
            slippage_cause = self._slippage_cause(signal, event)
            signal_meta = self._signal_meta_text(signal)
            cur.execute(
                "INSERT OR REPLACE INTO executions(id, signal_id, ts, symbol, side, order_status, requested_size_usdt, size_usdt, leverage, expected_fill_price, actual_fill_price, slippage_bps, fee_bps, fee_usdt, gross_realized_pnl, attempt_count, is_partial, filled_price, realized_pnl, reject_reason, note, regime_label, entry_rationale, market_state, slippage_cause, signal_meta) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                    regime_label,
                    entry_rationale,
                    market_state,
                    slippage_cause,
                    signal_meta,
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

    def record_auto_learning_proposals(
        self,
        source: str,
        mode: str,
        cycle: int,
        proposals: List[Dict[str, Any]],
        meta: Dict[str, Any] | None = None,
    ) -> List[int]:
        ts = datetime.utcnow().isoformat()
        base_meta = dict(meta or {})
        inserted: List[int] = []
        with self._lock:
            cur = self.conn.cursor()
            for item in proposals:
                strategy = str(item.get("strategy", "") or "").strip()
                action = str(item.get("action", "hold") or "hold").strip()
                if not strategy:
                    continue
                payload = dict(base_meta)
                if isinstance(item.get("meta"), dict):
                    payload = {**payload, **item.get("meta")}
                payload_text = json.dumps(payload, ensure_ascii=False)
                cur.execute(
                    """
                    INSERT INTO auto_learning_proposals(
                        ts, source, mode, cycle, strategy, action,
                        current_weight, suggested_weight, confidence, reason,
                        status, decision_note, applied_event_id, meta
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ts,
                        str(source or "unknown"),
                        str(mode or "unknown"),
                        int(cycle or 0),
                        strategy,
                        action,
                        float(item.get("current_weight", 0.0) or 0.0),
                        float(item.get("suggested_weight", 0.0) or 0.0),
                        float(item.get("confidence", 0.0) or 0.0),
                        str(item.get("reason", "") or ""),
                        "pending",
                        "",
                        None,
                        payload_text,
                    ),
                )
                inserted.append(int(cur.lastrowid))
            self.conn.commit()
        return inserted

    def recent_auto_learning_proposals(
        self,
        limit: int = 100,
        status: str | None = None,
        source: str | None = None,
    ) -> List[dict]:
        limit = max(1, min(2000, int(limit)))
        filters: List[str] = []
        params: List[Any] = []
        if status:
            filters.append("status = ?")
            params.append(str(status))
        if source:
            filters.append("source = ?")
            params.append(str(source))

        where = ""
        if filters:
            where = " WHERE " + " AND ".join(filters)

        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                f"""
                SELECT id, ts, source, mode, cycle, strategy, action,
                       current_weight, suggested_weight, confidence, reason,
                       status, decision_note, applied_event_id, meta
                FROM auto_learning_proposals
                {where}
                ORDER BY id DESC
                LIMIT ?
                """,
                (*params, limit),
            )
            rows = cur.fetchall()

        out: List[dict] = []
        for row in rows:
            meta_raw = row[14] or "{}"
            try:
                meta_value = json.loads(meta_raw)
            except Exception:
                meta_value = {}
            out.append(
                {
                    "id": int(row[0]),
                    "ts": row[1],
                    "source": row[2],
                    "mode": row[3],
                    "cycle": int(row[4] or 0),
                    "strategy": row[5],
                    "action": row[6],
                    "current_weight": row[7],
                    "suggested_weight": row[8],
                    "confidence": row[9],
                    "reason": row[10],
                    "status": row[11],
                    "decision_note": row[12],
                    "applied_event_id": row[13],
                    "meta": meta_value,
                }
            )
        return out

    def auto_learning_proposal_stats(self) -> Dict[str, Any]:
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT status, COUNT(*)
                FROM auto_learning_proposals
                GROUP BY status
                """
            )
            rows = cur.fetchall()
        by_status: Dict[str, int] = {}
        for status, count in rows:
            by_status[str(status or "unknown")] = int(count or 0)
        return {
            "total": int(sum(by_status.values())),
            "by_status": by_status,
            "pending": int(by_status.get("pending", 0)),
        }

    def update_auto_learning_proposal_status(
        self,
        proposal_ids: List[int],
        status: str,
        decision_note: str | None = None,
        applied_event_id: int | None = None,
    ) -> int:
        ids = [int(x) for x in proposal_ids if isinstance(x, (int, float, str)) and str(x).strip()]
        if not ids:
            return 0
        placeholders = ",".join(["?"] * len(ids))
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                f"""
                UPDATE auto_learning_proposals
                SET status = ?, decision_note = ?, applied_event_id = ?
                WHERE id IN ({placeholders})
                """,
                (
                    str(status),
                    str(decision_note or ""),
                    applied_event_id,
                    *ids,
                ),
            )
            changed = int(cur.rowcount or 0)
            self.conn.commit()
        return changed

    def expire_auto_learning_proposals(self, expiry_hours: int) -> int:
        if int(expiry_hours or 0) <= 0:
            return 0
        cutoff = (datetime.utcnow() - timedelta(hours=int(expiry_hours))).isoformat()
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                UPDATE auto_learning_proposals
                SET status = 'expired', decision_note = 'expired_by_ttl'
                WHERE status = 'pending' AND ts <= ?
                """,
                (cutoff,),
            )
            changed = int(cur.rowcount or 0)
            self.conn.commit()
        return changed

    def performance_leaderboard(self, limit: int = 10, window_days: int = 14) -> Dict[str, Any]:
        per_group_limit = max(1, min(100, int(limit)))
        query_limit = max(300, per_group_limit * 60)
        success_statuses = ",".join([f"'{x}'" for x in self._success_statuses()])
        cutoff_ts: str | None = None
        if int(window_days) > 0:
            cutoff_ts = (datetime.utcnow() - timedelta(days=int(window_days))).isoformat()

        with self._lock:
            cur = self.conn.cursor()
            if cutoff_ts:
                cur.execute(
                    f"""
                    SELECT e.ts, s.strategy, e.symbol, e.realized_pnl, e.regime_label, s.payload
                    FROM executions e
                    JOIN signals s ON e.signal_id = s.id
                    WHERE e.order_status IN ({success_statuses}) AND e.ts >= ?
                    ORDER BY e.ts DESC
                    LIMIT ?
                    """,
                    (cutoff_ts, query_limit),
                )
            else:
                cur.execute(
                    f"""
                    SELECT e.ts, s.strategy, e.symbol, e.realized_pnl, e.regime_label, s.payload
                    FROM executions e
                    JOIN signals s ON e.signal_id = s.id
                    WHERE e.order_status IN ({success_statuses})
                    ORDER BY e.ts DESC
                    LIMIT ?
                    """,
                    (query_limit,),
                )
            rows = cur.fetchall()

        def _extract_regime(explicit: Any, payload_raw: Any) -> str:
            raw = str(explicit or "").strip()
            if raw:
                return raw
            try:
                payload = json.loads(str(payload_raw or "{}"))
            except Exception:
                payload = {}
            meta = payload.get("meta") if isinstance(payload, dict) else {}
            if isinstance(meta, dict):
                for key in ["regime", "regime_label"]:
                    value = str(meta.get(key) or "").strip()
                    if value:
                        return value
                state = meta.get("market_state")
                if isinstance(state, dict):
                    value = str(state.get("regime") or "").strip()
                    if value:
                        return value
            return "unknown"

        def _update_bucket(store: Dict[str, Dict[str, float]], key: str, pnl: float) -> None:
            node = store.setdefault(key, {"trades": 0.0, "wins": 0.0, "total_pnl": 0.0})
            node["trades"] += 1.0
            if pnl > 0:
                node["wins"] += 1.0
            node["total_pnl"] += float(pnl)

        by_strategy: Dict[str, Dict[str, float]] = {}
        by_regime: Dict[str, Dict[str, float]] = {}
        by_symbol: Dict[str, Dict[str, float]] = {}

        for _, strategy, symbol, realized_pnl, regime_label, payload_raw in rows:
            pnl = float(realized_pnl or 0.0)
            strategy_key = str(strategy or "unknown")
            symbol_key = str(symbol or "unknown")
            regime_key = _extract_regime(regime_label, payload_raw)
            _update_bucket(by_strategy, strategy_key, pnl)
            _update_bucket(by_symbol, symbol_key, pnl)
            _update_bucket(by_regime, regime_key, pnl)

        def _finalize(source: Dict[str, Dict[str, float]], key_name: str) -> List[Dict[str, Any]]:
            out: List[Dict[str, Any]] = []
            for key, item in source.items():
                trades = int(item.get("trades", 0.0) or 0)
                wins = int(item.get("wins", 0.0) or 0)
                total_pnl = float(item.get("total_pnl", 0.0) or 0.0)
                out.append(
                    {
                        key_name: key,
                        "trades": trades,
                        "wins": wins,
                        "win_rate": (wins / trades) if trades > 0 else 0.0,
                        "total_pnl": total_pnl,
                        "avg_pnl": (total_pnl / trades) if trades > 0 else 0.0,
                    }
                )
            out.sort(key=lambda x: (float(x.get("total_pnl", 0.0)), float(x.get("win_rate", 0.0))), reverse=True)
            return out[:per_group_limit]

        return {
            "window_days": int(window_days),
            "sample_count": len(rows),
            "strategy": _finalize(by_strategy, "strategy"),
            "regime": _finalize(by_regime, "regime"),
            "symbol": _finalize(by_symbol, "symbol"),
        }

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
                       e.reject_reason, e.note,
                       e.regime_label, e.entry_rationale, e.market_state, e.slippage_cause, e.signal_meta
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
                "regime_label": regime_label,
                "entry_rationale": entry_rationale,
                "market_state": market_state,
                "slippage_cause": slippage_cause,
                "signal_meta": signal_meta,
            }
            for ts, strategy, symbol, side, event_status, requested_size_usdt, size_usdt, leverage,
            expected_fill_price, actual_fill_price, slippage_bps, fee_bps, fee_usdt, gross_realized_pnl,
            filled_price, attempt_count, row_is_partial,
            realized_pnl, row_reject_reason, note, regime_label, entry_rationale, market_state, slippage_cause, signal_meta in rows
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





