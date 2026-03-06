from __future__ import annotations

from collections import Counter
from datetime import datetime
from dataclasses import asdict, replace
from typing import Any, List, Tuple

from .config import AppConfig
from .data import DataCollector
from .domain import MarketRegime, MarketSnapshot, RegimeType, StrategySignal, SignalDirection, OrderStatus
from .exchange import ExchangeAdapter
from .journal import TradeJournal
from .learning import LearningEngine
from .llm import CycleSummary, LLMAdvisor
from .risk import AccountState, RiskEngine
from .execution import ExecutionEngine
from .regime import classify_market_regime
from .strategies import build_strategies


_REGIME_PREFERRED_STRATEGIES = {
    RegimeType.TREND_UP: [
        "trend",
        "ema_crossover",
        "volume_breakout",
        "grid",
        "bollinger_reversion",
        "defensive",
        "funding_arb",
    ],
    RegimeType.TREND_DOWN: [
        "trend",
        "ema_crossover",
        "volume_breakout",
        "defensive",
        "grid",
        "bollinger_reversion",
        "funding_arb",
    ],
    RegimeType.RANGE: [
        "grid",
        "bollinger_reversion",
        "volume_breakout",
        "defensive",
        "trend",
        "ema_crossover",
        "funding_arb",
    ],
    RegimeType.PANIC: [
        "defensive",
        "funding_arb",
        "ema_crossover",
        "grid",
        "bollinger_reversion",
        "volume_breakout",
        "trend",
    ],
    RegimeType.UNKNOWN: [
        "defensive",
        "trend",
        "ema_crossover",
        "grid",
        "bollinger_reversion",
        "volume_breakout",
        "funding_arb",
    ],
}

_BOT_TYPE_BY_STRATEGY = {
    "grid": "grid",
    "trend": "trend",
    "ema_crossover": "trend",
    "volume_breakout": "trend",
    "defensive": "defensive",
    "funding_arb": "funding_arb",
    "bollinger_reversion": "indicator",
}

_BOT_PROFILE_DEFAULTS: dict[str, dict[str, float]] = {
    "grid": {
        "position_size_multiplier": 1.0,
        "position_size_min": 0.01,
        "position_size_max": 0.12,
        "target_leverage": 1.0,
        "leverage_min": 1.0,
        "leverage_max": 2.0,
        "stop_loss_pct": 0.008,
        "take_profit_pct": 0.012,
        "confidence_bias": 0.0,
        "expected_edge_bps_bonus": 0.0,
        "slippage_multiplier": 1.0,
    },
    "trend": {
        "position_size_multiplier": 1.0,
        "position_size_min": 0.015,
        "position_size_max": 0.16,
        "target_leverage": 2.0,
        "leverage_min": 1.0,
        "leverage_max": 5.0,
        "stop_loss_pct": 0.01,
        "take_profit_pct": 0.02,
        "confidence_bias": 0.0,
        "expected_edge_bps_bonus": 0.0,
        "slippage_multiplier": 1.0,
    },
    "defensive": {
        "position_size_multiplier": 0.8,
        "position_size_min": 0.01,
        "position_size_max": 0.08,
        "target_leverage": 1.5,
        "leverage_min": 1.0,
        "leverage_max": 2.0,
        "stop_loss_pct": 0.006,
        "take_profit_pct": 0.012,
        "confidence_bias": 0.0,
        "expected_edge_bps_bonus": 0.0,
        "slippage_multiplier": 0.95,
    },
    "funding_arb": {
        "position_size_multiplier": 0.9,
        "position_size_min": 0.01,
        "position_size_max": 0.10,
        "target_leverage": 2.5,
        "leverage_min": 2.0,
        "leverage_max": 5.0,
        "stop_loss_pct": 0.004,
        "take_profit_pct": 0.008,
        "confidence_bias": 0.0,
        "expected_edge_bps_bonus": 0.0,
        "slippage_multiplier": 1.0,
    },
    "indicator": {
        "position_size_multiplier": 1.0,
        "position_size_min": 0.01,
        "position_size_max": 0.12,
        "target_leverage": 1.8,
        "leverage_min": 1.0,
        "leverage_max": 4.0,
        "stop_loss_pct": 0.008,
        "take_profit_pct": 0.016,
        "confidence_bias": 0.0,
        "expected_edge_bps_bonus": 0.0,
        "slippage_multiplier": 1.0,
    },
    "custom": {
        "position_size_multiplier": 1.0,
        "position_size_min": 0.005,
        "position_size_max": 0.20,
        "target_leverage": 2.0,
        "leverage_min": 1.0,
        "leverage_max": 5.0,
        "stop_loss_pct": 0.01,
        "take_profit_pct": 0.02,
        "confidence_bias": 0.0,
        "expected_edge_bps_bonus": 0.0,
        "slippage_multiplier": 1.0,
    },
}

_BOT_PROFILE_BY_REGIME: dict[str, dict[str, dict[str, float]]] = {
    "panic": {
        "grid": {"position_size_multiplier": 0.65, "leverage_max": 1.5, "target_leverage": 1.0, "confidence_bias": -0.05},
        "trend": {"position_size_multiplier": 0.6, "leverage_max": 2.0, "target_leverage": 1.3, "confidence_bias": -0.08},
        "defensive": {"position_size_multiplier": 0.9, "leverage_max": 1.8, "target_leverage": 1.2},
        "funding_arb": {"position_size_multiplier": 0.7, "leverage_max": 3.0, "target_leverage": 2.0, "confidence_bias": -0.04},
        "indicator": {"position_size_multiplier": 0.7, "leverage_max": 2.0, "target_leverage": 1.5, "confidence_bias": -0.05},
        "custom": {"position_size_multiplier": 0.7, "leverage_max": 2.0, "target_leverage": 1.5},
    },
    "range": {
        "grid": {"position_size_multiplier": 1.1, "expected_edge_bps_bonus": 1.5},
        "trend": {"position_size_multiplier": 0.9, "confidence_bias": -0.02},
        "defensive": {"position_size_multiplier": 1.0},
        "indicator": {"position_size_multiplier": 1.05},
    },
    "trend_up": {
        "trend": {"position_size_multiplier": 1.05, "target_leverage": 2.2, "expected_edge_bps_bonus": 2.0},
        "grid": {"position_size_multiplier": 0.9},
        "defensive": {"position_size_multiplier": 0.85},
    },
    "trend_down": {
        "trend": {"position_size_multiplier": 1.0, "target_leverage": 2.2, "expected_edge_bps_bonus": 1.0},
        "grid": {"position_size_multiplier": 0.85},
        "defensive": {"position_size_multiplier": 0.85},
    },
}


class TradingOrchestrator:
    def __init__(
        self,
        config: AppConfig,
        data_collector: DataCollector,
        exchange: ExchangeAdapter,
        journal: TradeJournal,
        llm: LLMAdvisor,
    ):
        self.config = config
        self.collector = data_collector
        self.exchange = exchange
        self.journal = journal
        self.llm = llm

        self.strategies = build_strategies(config.strategies)
        self.risk = RiskEngine(
            daily_max_loss_pct=config.risk_limits.daily_max_loss_pct,
            max_total_exposure=config.risk_limits.max_total_exposure,
            max_symbol_exposure=config.risk_limits.max_symbol_exposure,
            max_open_positions=config.risk_limits.max_open_positions,
            max_daily_trades=config.risk_limits.max_daily_trades,
            max_leverage=config.risk_limits.max_leverage,
            min_signal_confidence=config.risk_limits.min_signal_confidence,
            max_slippage_bps=config.risk_limits.max_slippage_bps,
            min_expectancy_pct=config.risk_limits.min_expectancy_pct,
            cooldown_minutes=config.risk_limits.cooldown_minutes,
            max_consecutive_losses=config.risk_limits.max_consecutive_losses,
            max_reject_ratio=config.risk_limits.max_reject_ratio,
        )
        self.execution = ExecutionEngine(
            exchange=exchange,
            journal=journal,
            maker_fee_bps=config.execution.maker_fee_bps,
            taker_fee_bps=config.execution.taker_fee_bps,
            order_retries=config.execution.order_retries,
            retry_base_wait_ms=config.execution.retry_base_wait_ms,
            mode=config.mode,
            live_staging=asdict(config.live_staging),
        )
        self.learning = LearningEngine(journal)
        self._cycle = 0

    def _snapshot_universe(self) -> List[MarketSnapshot]:
        scan_count = min(self.config.pipeline.scan_limit, self.config.pipeline.symbols_to_scan)
        universe = self.config.pipeline.universe[:scan_count]
        snapshots = self.collector.collect_batch(universe)

        # keep exchange price cache updated
        for snapshot in snapshots.values():
            self.exchange.set_price(snapshot.symbol, snapshot.price)
        return list(snapshots.values())

    def _regime_strategy_order(self, regime: MarketRegime) -> List[str]:
        preferred = _REGIME_PREFERRED_STRATEGIES.get(
            regime.regime,
            _REGIME_PREFERRED_STRATEGIES[RegimeType.UNKNOWN],
        )
        active_ids = {s.id for s in self.strategies}
        ordered = [sid for sid in preferred if sid in active_ids]
        ordered.extend([sid for sid in active_ids if sid not in ordered])
        return ordered

    def _ordered_strategies_for_regime(self, regime: MarketRegime):
        strategy_map = {s.id: s for s in self.strategies}
        ordered_ids = self._regime_strategy_order(regime)
        return [(sid, strategy_map[sid]) for sid in ordered_ids if sid in strategy_map]

    def _build_regime(self, snapshot: MarketSnapshot) -> MarketRegime:
        hist = self.collector.get_history(snapshot.symbol)
        return classify_market_regime(snapshot.symbol, list(hist)[:12])

    def _build_account_state(self) -> AccountState:
        balances = self.exchange.get_balance()
        today_pnl, today_trades, consecutive_losses = self.journal.today_performance()
        last_filled = self.journal.latest_filled_at()
        last_trade_at = datetime.fromisoformat(last_filled) if last_filled else None
        by_symbol_raw = self.journal.latest_filled_by_symbol()
        last_trade_by_symbol: dict[str, datetime] = {}
        for symbol, ts in by_symbol_raw.items():
            try:
                last_trade_by_symbol[str(symbol)] = datetime.fromisoformat(str(ts))
            except Exception:
                continue

        return AccountState(
            cash_usdt=balances.get("USDT", 0.0),
            equity_usdt=balances.get("equity_usdt", balances.get("USDT", 0.0)),
            open_positions=self.exchange.get_open_positions(),
            last_trade_by_symbol=last_trade_by_symbol,
            today_pnl=today_pnl,
            today_trades=today_trades,
            consecutive_loss_count=consecutive_losses,
            last_trade_at=last_trade_at,
        )

    def _gather_candidates(self, snapshots: List[MarketSnapshot]) -> Tuple[List[Tuple[StrategySignal, MarketRegime]], dict]:
        candidates: List[Tuple[StrategySignal, MarketRegime]] = []
        regime_distribution: Counter[str] = Counter()
        signal_count: Counter[str] = Counter()
        bot_signal_count: Counter[str] = Counter()
        snapshot_plans: List[dict] = []

        for snapshot in snapshots:
            regime = self._build_regime(snapshot)
            strategy_order = self._regime_strategy_order(regime)
            regime_distribution[regime.regime.value] += 1

            snapshot_candidates = 0
            for strategy_id, strategy in self._ordered_strategies_for_regime(regime):
                for sig in strategy.generate(snapshot, regime):
                    sig = self._apply_bot_profile(sig, regime)
                    if sig.confidence < self.config.risk_limits.min_signal_confidence:
                        continue
                    if sig.direction == SignalDirection.HOLD:
                        continue
                    candidates.append((sig, regime))
                    snapshot_candidates += 1
                    signal_count[strategy_id] += 1
                    bot_signal_count[str(sig.meta.get("bot_type", "custom"))] += 1

            snapshot_plans.append(
                {
                    "symbol": snapshot.symbol,
                    "regime": regime.regime.value,
                    "regime_reason": regime.reason,
                    "regime_confidence": regime.confidence,
                    "strategy_order": strategy_order,
                    "candidate_count": snapshot_candidates,
                }
            )

        plan = {
            "snapshot_plans": snapshot_plans,
            "regime_distribution": dict(regime_distribution),
            "strategy_signal_counts": dict(signal_count),
            "bot_signal_counts": dict(bot_signal_count),
            "strategy_order_map": {
                sid: [item["symbol"] for item in snapshot_plans if sid in item["strategy_order"]]
                for sid in sorted({sid for item in snapshot_plans for sid in item["strategy_order"]})
            },
        }
        return candidates, plan

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    def _strategy_cfg(self, strategy_id: str) -> dict[str, Any]:
        raw = self.config.strategies.get(strategy_id, {}) if isinstance(self.config.strategies, dict) else {}
        return raw if isinstance(raw, dict) else {}

    def _resolve_bot_type(self, strategy_id: str, strategy_cfg: dict[str, Any]) -> str:
        explicit = str(strategy_cfg.get("bot_type", "")).strip().lower()
        if explicit:
            return explicit
        return _BOT_TYPE_BY_STRATEGY.get(strategy_id, "custom")

    def _resolve_bot_profile(self, strategy_id: str, regime: MarketRegime) -> tuple[str, dict[str, float]]:
        strategy_cfg = self._strategy_cfg(strategy_id)
        bot_type = self._resolve_bot_type(strategy_id, strategy_cfg)

        profile = dict(_BOT_PROFILE_DEFAULTS.get(bot_type, _BOT_PROFILE_DEFAULTS["custom"]))
        regime_defaults = _BOT_PROFILE_BY_REGIME.get(regime.regime.value, {})
        profile.update(regime_defaults.get(bot_type, {}))

        cfg_profile = strategy_cfg.get("bot_profile", {})
        if isinstance(cfg_profile, dict):
            profile.update(cfg_profile)

        cfg_profile_by_regime = strategy_cfg.get("bot_profile_by_regime", {})
        if isinstance(cfg_profile_by_regime, dict):
            regime_profile = cfg_profile_by_regime.get(regime.regime.value, {})
            if isinstance(regime_profile, dict):
                profile.update(regime_profile)

        return bot_type, profile

    def _apply_bot_profile(self, signal: StrategySignal, regime: MarketRegime) -> StrategySignal:
        bot_type, profile = self._resolve_bot_profile(signal.strategy_id, regime)

        size_mult = float(profile.get("position_size_multiplier", 1.0))
        size_min = float(profile.get("position_size_min", 0.001))
        size_max = float(profile.get("position_size_max", 1.0))
        new_size = self._clamp(signal.position_size_ratio * size_mult, size_min, size_max)

        lev_min = float(profile.get("leverage_min", 1.0))
        lev_max = float(profile.get("leverage_max", self.config.risk_limits.max_leverage))
        target_lev = float(profile.get("target_leverage", signal.leverage))
        new_lev = self._clamp(target_lev, lev_min, min(lev_max, self.config.risk_limits.max_leverage))

        new_stop_loss = float(profile.get("stop_loss_pct", signal.stop_loss_pct))
        new_take_profit = float(profile.get("take_profit_pct", signal.take_profit_pct))
        new_conf = self._clamp(signal.confidence + float(profile.get("confidence_bias", 0.0)), 0.01, 0.99)
        new_edge = signal.expected_edge_bps + float(profile.get("expected_edge_bps_bonus", 0.0))
        new_slippage = max(0.1, signal.slippage_estimate_bps * float(profile.get("slippage_multiplier", 1.0)))

        new_meta = dict(signal.meta or {})
        new_meta["bot_type"] = bot_type
        new_meta["bot_profile"] = {
            "position_size_multiplier": size_mult,
            "position_size_min": size_min,
            "position_size_max": size_max,
            "target_leverage": target_lev,
            "leverage_min": lev_min,
            "leverage_max": lev_max,
            "stop_loss_pct": new_stop_loss,
            "take_profit_pct": new_take_profit,
            "confidence_bias": float(profile.get("confidence_bias", 0.0)),
            "expected_edge_bps_bonus": float(profile.get("expected_edge_bps_bonus", 0.0)),
            "slippage_multiplier": float(profile.get("slippage_multiplier", 1.0)),
        }

        return replace(
            signal,
            confidence=new_conf,
            expected_edge_bps=new_edge,
            slippage_estimate_bps=new_slippage,
            position_size_ratio=new_size,
            leverage=new_lev,
            stop_loss_pct=new_stop_loss,
            take_profit_pct=new_take_profit,
            comment=f"{signal.comment}|bot:{bot_type}",
            meta=new_meta,
        )

    def _candidate_id(self, index: int, signal: StrategySignal, regime: MarketRegime) -> str:
        ts = signal.timestamp.isoformat()
        return f"{index}|{signal.symbol}|{signal.strategy_id}|{signal.direction.value}|{ts}"

    def _sort_score(self, sig: StrategySignal, regime: MarketRegime) -> float:
        ev = self._expectancy_bps(sig)
        return (ev * 0.7) + (sig.confidence * 100 * 0.2) + (regime.confidence * 30)

    def _expectancy_bps(self, sig: StrategySignal) -> float:
        fees = self.config.execution.taker_fee_bps + self.config.execution.maker_fee_bps
        return sig.expected_edge_bps * sig.confidence - sig.slippage_estimate_bps - fees

    def _llm_candidate_scores(self, raw_candidates: List[Tuple[StrategySignal, MarketRegime]], state: AccountState) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        cfg = self.config.llm
        if not cfg.enabled:
            return {}, {"status": "disabled"}

        prepared: List[Dict[str, Any]] = []
        for idx, (signal, regime) in enumerate(raw_candidates[: cfg.score_candidates_limit]):
            base_score = self._sort_score(signal, regime)
            prepared.append(
                {
                    "id": self._candidate_id(idx, signal, regime),
                    "symbol": signal.symbol,
                    "strategy_id": signal.strategy_id,
                    "direction": signal.direction.value,
                    "confidence": signal.confidence,
                    "expected_edge_bps": signal.expected_edge_bps,
                    "slippage_estimate_bps": signal.slippage_estimate_bps,
                    "position_size_ratio": signal.position_size_ratio,
                    "leverage": signal.leverage,
                    "regime": regime.regime.value,
                    "regime_confidence": regime.confidence,
                    "regime_reason": regime.reason,
                    "volatility": signal.meta.get("volatility", 0.0),
                    "spread_bps": signal.meta.get("spread_bps", 0.0),
                    "base_score": base_score,
                }
            )

        context = {
            "cycle": self._cycle + 1,
            "mode": self.config.mode,
            "account": {
                "cash_usdt": state.cash_usdt,
                "equity_usdt": state.equity_usdt,
                "open_positions": state.open_positions,
                "today_pnl": state.today_pnl,
                "today_trades": state.today_trades,
                "consecutive_loss_count": state.consecutive_loss_count,
            },
            "risk_limits": asdict(self.config.risk_limits),
        }

        scores = self.llm.score_candidates(prepared, context=context)
        meta = self.llm.get_last_metadata()
        return scores, meta

    def _build_llm_meta(self, selected_scored: List[tuple], score_map: Dict[str, Dict[str, Any]], meta: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "enabled": self.config.llm.enabled,
            "provider": self.config.llm.provider,
            "request_mode": self.config.llm.request_mode,
            "meta": meta,
            "top_scored": [
                {
                    "candidate_id": candidate_id,
                    "score_delta": score_meta.get("score_delta", 0.0),
                    "confidence": score_meta.get("confidence", 0.0),
                    "reason": score_meta.get("reason", ""),
                    "symbol": signal.symbol,
                    "strategy_id": signal.strategy_id,
                    "direction": signal.direction.value,
                }
                for signal, _, candidate_id, _, _, _, score_meta in selected_scored
                if score_meta
            ],
        }

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    def _enrich_signal_for_logging(
        self,
        signal: StrategySignal,
        regime: MarketRegime,
        total_score: float,
        base_score: float,
        llm_score_bonus: float,
        llm_reason: str,
        llm_confidence: float,
    ) -> StrategySignal:
        meta = dict(signal.meta or {})
        spread_bps = self._safe_float(meta.get("spread_bps"), signal.slippage_estimate_bps)
        volatility = self._safe_float(meta.get("volatility"), 0.0)
        momentum = self._safe_float(meta.get("momentum"), 0.0)
        funding_rate = self._safe_float(meta.get("funding_rate"), 0.0)
        kalman_trend = self._safe_float(meta.get("kalman_trend_score"), 0.0)
        kalman_shock = self._safe_float(meta.get("kalman_innovation_z"), 0.0)
        kalman_uncertainty = self._safe_float(meta.get("kalman_uncertainty"), 0.0)

        market_state = {
            "regime": regime.regime.value,
            "regime_confidence": round(float(regime.confidence), 4),
            "regime_reason": str(regime.reason),
            "spread_bps": round(spread_bps, 4),
            "volatility": round(volatility, 6),
            "momentum": round(momentum, 6),
            "funding_rate": round(funding_rate, 6),
            "kalman_trend_score": round(kalman_trend, 6),
            "kalman_innovation_z": round(kalman_shock, 6),
            "kalman_uncertainty": round(kalman_uncertainty, 6),
        }

        factors: list[str] = [
            f"regime={regime.regime.value}({float(regime.confidence):.2f})",
            f"edge={float(signal.expected_edge_bps):.2f}bps",
            f"spread={spread_bps:.2f}bps",
            f"volatility={volatility:.4f}",
            f"kalman_shock={kalman_shock:.2f}",
            f"score={total_score:.2f}(base={base_score:.2f}, llm={llm_score_bonus:.2f})",
        ]
        if llm_reason:
            factors.append(f"llm={llm_reason[:120]}")

        direction = signal.direction.value if isinstance(signal.direction, SignalDirection) else str(signal.direction)
        rationale = {
            "summary": (
                f"{signal.strategy_id} {direction} 진입: "
                f"레짐 {regime.regime.value} + 기대엣지 {float(signal.expected_edge_bps):.1f}bps + "
                f"리스크 적합(신뢰도 {float(signal.confidence):.2f})"
            ),
            "factors": factors,
            "score": {
                "total": round(float(total_score), 4),
                "base": round(float(base_score), 4),
                "llm_bonus": round(float(llm_score_bonus), 4),
                "llm_confidence": round(float(llm_confidence), 4),
            },
        }

        meta["regime"] = regime.regime.value
        meta["market_state"] = market_state
        meta["entry_rationale"] = rationale
        return replace(signal, meta=meta)

    def run_once(self) -> dict:
        self._cycle += 1
        created = datetime.utcnow().isoformat()
        snapshots = self._snapshot_universe()
        state = self._build_account_state()

        raw_candidates, strategy_plan = self._gather_candidates(snapshots)
        llm_scores, llm_meta = self._llm_candidate_scores(raw_candidates, state)

        ranked: List[tuple] = []
        for idx, (signal, regime) in enumerate(raw_candidates):
            base_score = self._sort_score(signal, regime)
            candidate_id = self._candidate_id(idx, signal, regime)
            score_meta = llm_scores.get(candidate_id, {}) if isinstance(llm_scores, dict) else {}
            bonus = 0.0
            if isinstance(score_meta, dict):
                bonus = float(score_meta.get("score_delta", 0.0))

            ranked.append(
                (
                    signal,
                    regime,
                    candidate_id,
                    base_score + bonus,
                    base_score,
                    bonus,
                    score_meta,
                )
            )

        selected = sorted(ranked, key=lambda x: x[3], reverse=True)[: self.config.pipeline.candidate_count]

        executed = 0
        rejected = 0
        reject_reasons: Counter[str] = Counter()
        selected_strategy_counts: Counter[str] = Counter()
        selected_bot_counts: Counter[str] = Counter()
        selected_plan = []

        for signal, regime, candidate_id, total_score, base_score, bonus, score_meta in selected:
            selected_strategy_counts[signal.strategy_id] += 1
            bot_type = str(signal.meta.get("bot_type", "custom"))
            selected_bot_counts[bot_type] += 1
            llm_reason = ""
            llm_confidence = 0.0
            if isinstance(score_meta, dict):
                llm_reason = str(score_meta.get("reason", "")).strip()
                llm_confidence = float(score_meta.get("confidence", 0.0))

            signal = self._enrich_signal_for_logging(
                signal=signal,
                regime=regime,
                total_score=total_score,
                base_score=base_score,
                llm_score_bonus=bonus,
                llm_reason=llm_reason,
                llm_confidence=llm_confidence,
            )

            selected_plan.append(
                {
                    "symbol": signal.symbol,
                    "strategy": signal.strategy_id,
                    "regime": regime.regime.value,
                    "direction": signal.direction.value,
                    "score": total_score,
                    "score_base": base_score,
                    "llm_score_bonus": bonus,
                    "llm_confidence": llm_confidence,
                    "comment": signal.comment,
                    "llm_reason": llm_reason,
                    "confidence": signal.confidence,
                    "expected_edge_bps": signal.expected_edge_bps,
                    "position_size_ratio": signal.position_size_ratio,
                    "leverage": signal.leverage,
                    "stop_loss_pct": signal.stop_loss_pct,
                    "take_profit_pct": signal.take_profit_pct,
                    "bot_type": bot_type,
                    "bot_profile": signal.meta.get("bot_profile", {}),
                }
            )

            ev = self._expectancy_bps(signal)
            if ev < self.config.risk_limits.min_expectancy_pct * 100:
                rejected += 1
                reject_reasons["expectancy_check"] += 1
                continue

            signal_id = self.journal.log_signal(signal)
            decision = self.risk.evaluate(
                signal,
                regime,
                state,
            )
            if not decision.allowed:
                rejected += 1
                for reason in decision.reasons:
                    reject_reasons[reason] += 1
                continue

            event = self.execution.execute(signal, decision, state.equity_usdt, signal_id=signal_id)
            if event.status in {OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED}:
                executed += 1
                state.today_trades += 1
                state.last_trade_at = signal.timestamp
                state.last_trade_by_symbol[signal.symbol] = signal.timestamp

                realized = event.realized_pnl or 0.0
                state.today_pnl += realized
                if realized < 0:
                    state.consecutive_loss_count += 1
                else:
                    state.consecutive_loss_count = 0

            else:
                rejected += 1
                reject_key = event.reject_reason or "execution_rejected"
                reject_reasons[reject_key] += 1

        balance = self.exchange.get_balance()

        summary = {
            "timestamp": created,
            "cycle": self._cycle,
            "snapshot_count": len(snapshots),
            "raw_candidates": len(raw_candidates),
            "selected": len(selected),
            "executed": executed,
            "rejected": rejected,
            "strategy_plan": {
                "snapshot_plans": strategy_plan["snapshot_plans"],
                "regime_distribution": strategy_plan["regime_distribution"],
                "strategy_signal_counts": strategy_plan["strategy_signal_counts"],
                "bot_signal_counts": strategy_plan.get("bot_signal_counts", {}),
                "strategy_order_map": strategy_plan["strategy_order_map"],
                "selected_strategy_counts": dict(selected_strategy_counts),
                "selected_bot_counts": dict(selected_bot_counts),
                "selected_plan": selected_plan,
            },
            "reasons": dict(reject_reasons),
            "balance": balance,
            "positions": state.open_positions,
            "account_state": {
                "cash_usdt": state.cash_usdt,
                "equity_usdt": state.equity_usdt,
                "today_pnl": state.today_pnl,
                "today_trades": state.today_trades,
                "consecutive_loss_count": state.consecutive_loss_count,
            },
            "llm": self._build_llm_meta(selected, llm_scores if isinstance(llm_scores, dict) else {}, llm_meta),
            "live_staging": self.execution.get_live_staging_status(),
            "execution_guard": self.execution.get_execution_guard_status(),
            "explanation": self.llm.explain(
                CycleSummary(
                    selected=len(selected),
                    executed=executed,
                    rejected=rejected,
                    reasons=dict(reject_reasons),
                )
            ),
            "learning": [vars(x) for x in self.learning.summarize()[:5]],
        }
        return summary
