from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import AppConfig
from .data import MockMarketDataCollector
from .exchange import build_exchange
from .journal import TradeJournal
from .llm import LLMAdvisor
from .path_display import portable_path
from .pipeline import TradingOrchestrator
from .preflight import evaluate_live_preflight
from .validation_gate import evaluate_validation_gate
from .validation_history import save_validation_snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Boss AI trading system")
    parser.add_argument("--config", default="configs/default.json", help="Path to config JSON")
    parser.add_argument("--mode", choices=["dry", "paper", "live"], default="dry")
    parser.add_argument("--skip-validation-gate", action="store_true", help="Bypass validation gate checks")
    parser.add_argument("--iterations", type=int, default=1, help="Iteration count (0 = infinite loop)")
    parser.add_argument("--interval", type=int, default=5, help="Loop interval seconds")
    parser.add_argument("--ui", action="store_true", help="Run single-account web dashboard")
    parser.add_argument("--ui-desktop", action="store_true", help="Run single-account desktop dashboard")
    parser.add_argument("--ui-multi", action="store_true", help="Run multi-account web dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Dashboard host")
    parser.add_argument("--port", type=int, default=8000, help="Dashboard port")
    parser.add_argument("--live-confirm-token", default="", help="Live mode confirmation token")
    parser.add_argument("--live-readiness", action="store_true", help="Run live readiness check only")
    parser.add_argument(
        "--live-readiness-report",
        nargs="?",
        const="auto",
        default="",
        help="Save live readiness report (empty path => auto output path)",
    )
    parser.add_argument("--live-rehearsal", action="store_true", help="Build live rehearsal runbook only")
    parser.add_argument(
        "--live-rehearsal-report",
        nargs="?",
        const="auto",
        default="",
        help="Save live rehearsal runbook report (empty path => auto output path)",
    )
    parser.add_argument("--multi-config", default="", help="Path to multi profile config JSON")
    parser.add_argument(
        "--multi-command",
        choices=["status", "run-once", "loop"],
        default="status",
        help="Multi runtime command",
    )
    parser.add_argument(
        "--multi-interval",
        type=int,
        default=0,
        help="Common interval for multi runtime (0 = use each profile value)",
    )
    parser.add_argument("--multi-live-token", default="", help="Common live confirm token for multi runtime")
    parser.add_argument("--exchange-probe", action="store_true", help="Run exchange probe only")
    parser.add_argument(
        "--exchange-probe-report",
        nargs="?",
        const="auto",
        default="",
        help="Save exchange probe report (empty path => auto output path)",
    )
    parser.add_argument("--llm-test", action="store_true", help="Run LLM connectivity test only")
    parser.add_argument("--llm-test-symbol", default="BTCUSDT", help="Sample symbol for LLM test")

    parser.add_argument("--backtest-cycles", type=int, default=0, help="Backtest cycles")
    parser.add_argument("--walk-forward-windows", type=int, default=0, help="Walk-forward window count")
    parser.add_argument("--walk-forward-train-cycles", type=int, default=80, help="Train cycles per window")
    parser.add_argument("--walk-forward-test-cycles", type=int, default=40, help="Test cycles per window")
    parser.add_argument("--validation-seed", type=int, default=42, help="Validation random seed")
    parser.add_argument("--validation-use-llm", action="store_true", help="Use LLM scoring in validation")
    parser.add_argument("--validation-min-trades", type=int, default=20, help="Validation min trades")
    parser.add_argument("--validation-min-win-rate", type=float, default=0.45, help="Validation min win rate")
    parser.add_argument("--validation-min-pnl-usdt", type=float, default=0.0, help="Validation min net pnl (USDT)")
    parser.add_argument(
        "--validation-max-drawdown-pct",
        type=float,
        default=0.25,
        help="Validation max drawdown ratio",
    )
    parser.add_argument("--validation-report", default="", help="Path to save validation report JSON")
    return parser.parse_args()


def _build_llm(cfg, use_llm: bool) -> LLMAdvisor:
    enabled = bool(cfg.llm.enabled) if use_llm else False
    provider = cfg.llm.provider if use_llm else "mock"
    return LLMAdvisor(
        enabled=enabled,
        provider=provider,
        api_key=cfg.llm.api_key,
        api_key_env=cfg.llm.api_key_env,
        api_base_url=cfg.llm.api_base_url,
        model=cfg.llm.model,
        temperature=cfg.llm.temperature,
        timeout_seconds=cfg.llm.timeout_seconds,
        max_retries=cfg.llm.max_retries,
        retry_delay_ms=cfg.llm.retry_delay_ms,
        max_tokens=cfg.llm.max_tokens,
        score_scale=cfg.llm.score_scale,
        score_candidates_limit=cfg.llm.score_candidates_limit,
        request_mode=cfg.llm.request_mode,
    )


def _build_validation_config(config: AppConfig, journal_path: str) -> AppConfig:
    paper_exchange = replace(config.exchange, type="paper", allow_live=False)
    paper_journal = replace(config.journal, path=journal_path)
    paper_risk = replace(
        config.risk_limits,
        # Validation should evaluate strategy behavior, not be blocked by intraday safety throttles.
        cooldown_minutes=0,
        max_consecutive_losses=max(int(config.risk_limits.max_consecutive_losses), 50),
        max_daily_trades=max(int(config.risk_limits.max_daily_trades), 500),
        max_total_exposure=max(float(config.risk_limits.max_total_exposure), 2.0),
        max_symbol_exposure=max(float(config.risk_limits.max_symbol_exposure), 0.8),
        max_open_positions=max(int(config.risk_limits.max_open_positions), 10),
        max_slippage_bps=max(float(config.risk_limits.max_slippage_bps), 60.0),
        min_expectancy_pct=min(float(config.risk_limits.min_expectancy_pct), 0.03),
    )
    strategy_cfg = {
        key: (dict(value) if isinstance(value, dict) else {})
        for key, value in config.strategies.items()
    }

    for sid in ["trend", "ema_crossover", "grid"]:
        current = dict(strategy_cfg.get(sid, {}))
        current["enabled"] = False
        strategy_cfg[sid] = current

    for sid, floor_weight in {
        "funding_arb": 1.4,
        "bollinger_reversion": 1.2,
        "defensive": 0.9,
    }.items():
        current = dict(strategy_cfg.get(sid, {}))
        weight_raw = current.get("weight", 1.0)
        try:
            weight = float(weight_raw)
        except Exception:
            weight = 1.0
        current["enabled"] = True
        current["weight"] = max(weight, float(floor_weight))
        strategy_cfg[sid] = current

    return replace(
        config,
        mode="paper",
        exchange=paper_exchange,
        journal=paper_journal,
        risk_limits=paper_risk,
        strategies=strategy_cfg,
    )


def _build_validation_stack(
    config: AppConfig,
    seed: int,
    use_llm: bool,
    journal_path: str,
) -> tuple[AppConfig, TradingOrchestrator, TradeJournal, Any]:
    run_cfg = _build_validation_config(config, journal_path=journal_path)
    exchange = build_exchange(run_cfg.exchange)
    collector = MockMarketDataCollector(seed=seed, symbols=run_cfg.pipeline.universe)
    journal = TradeJournal(path=run_cfg.journal.path)
    llm = _build_llm(run_cfg, use_llm=use_llm)
    orchestrator = TradingOrchestrator(
        config=run_cfg,
        data_collector=collector,
        exchange=exchange,
        journal=journal,
        llm=llm,
    )
    return run_cfg, orchestrator, journal, exchange


def _validation_journal_path(prefix: str) -> str:
    now = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_dir = Path("data") / "validation"
    out_dir.mkdir(parents=True, exist_ok=True)
    return str((out_dir / f"{prefix}_{now}.sqlite").resolve())


def _run_cycles(orchestrator: TradingOrchestrator, cycles: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for _ in range(max(1, int(cycles))):
        out.append(orchestrator.run_once())
    return out


def _equity_from_balance(summary: dict[str, Any], fallback: float = 0.0) -> float:
    balance = summary.get("balance", {}) if isinstance(summary, dict) else {}
    value = balance.get("equity_usdt", fallback) if isinstance(balance, dict) else fallback
    try:
        return float(value)
    except Exception:
        return float(fallback)


def _max_drawdown(equities: list[float]) -> float:
    if not equities:
        return 0.0
    peak = equities[0]
    max_dd = 0.0
    for eq in equities:
        if eq > peak:
            peak = eq
        if peak > 0:
            dd = (peak - eq) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd


def _compute_metrics(
    cycle_summaries: list[dict[str, Any]],
    execution_rows: list[dict[str, Any]],
    start_equity: float,
    end_equity: float,
) -> dict[str, Any]:
    selected = sum(int(x.get("selected", 0) or 0) for x in cycle_summaries)
    executed = sum(int(x.get("executed", 0) or 0) for x in cycle_summaries)
    rejected = sum(int(x.get("rejected", 0) or 0) for x in cycle_summaries)
    reasons: Counter[str] = Counter()
    for item in cycle_summaries:
        for key, value in (item.get("reasons", {}) or {}).items():
            reasons[str(key)] += int(value or 0)

    filled_statuses = {"filled", "partially_filled"}
    filled_rows = [row for row in execution_rows if str(row.get("order_status", "")).lower() in filled_statuses]
    rejected_rows = [row for row in execution_rows if str(row.get("order_status", "")).lower() == "rejected"]
    wins = sum(1 for row in filled_rows if float(row.get("realized_pnl", 0.0) or 0.0) > 0.0)
    total_realized = sum(float(row.get("realized_pnl", 0.0) or 0.0) for row in filled_rows)
    avg_slippage = (
        sum(float(row.get("slippage_bps", 0.0) or 0.0) for row in filled_rows) / len(filled_rows)
        if filled_rows else 0.0
    )

    equities = [start_equity]
    for row in cycle_summaries:
        equities.append(_equity_from_balance(row, fallback=equities[-1]))

    attempts = len(filled_rows) + len(rejected_rows)
    reject_rate = (len(rejected_rows) / attempts) if attempts > 0 else 0.0
    win_rate = (wins / len(filled_rows)) if filled_rows else 0.0

    return {
        "cycles": len(cycle_summaries),
        "selected_signals": selected,
        "executed_signals": executed,
        "rejected_signals": rejected,
        "filled_trades": len(filled_rows),
        "rejected_trades": len(rejected_rows),
        "win_trades": wins,
        "win_rate": win_rate,
        "reject_rate": reject_rate,
        "avg_slippage_bps": avg_slippage,
        "avg_realized_pnl_per_trade": (total_realized / len(filled_rows)) if filled_rows else 0.0,
        "realized_pnl_sum": total_realized,
        "start_equity_usdt": start_equity,
        "end_equity_usdt": end_equity,
        "pnl_total_usdt": end_equity - start_equity,
        "max_drawdown_pct": _max_drawdown(equities),
        "top_reject_reasons": dict(reasons.most_common(8)),
    }


def _evaluate_gate(metrics: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    checks = {
        "min_trades": {
            "required": int(args.validation_min_trades),
            "actual": int(metrics.get("filled_trades", 0)),
            "pass": int(metrics.get("filled_trades", 0)) >= int(args.validation_min_trades),
        },
        "min_win_rate": {
            "required": float(args.validation_min_win_rate),
            "actual": float(metrics.get("win_rate", 0.0)),
            "pass": float(metrics.get("win_rate", 0.0)) >= float(args.validation_min_win_rate),
        },
        "min_pnl_usdt": {
            "required": float(args.validation_min_pnl_usdt),
            "actual": float(metrics.get("pnl_total_usdt", 0.0)),
            "pass": float(metrics.get("pnl_total_usdt", 0.0)) >= float(args.validation_min_pnl_usdt),
        },
        "max_drawdown_pct": {
            "required": float(args.validation_max_drawdown_pct),
            "actual": float(metrics.get("max_drawdown_pct", 0.0)),
            "pass": float(metrics.get("max_drawdown_pct", 0.0)) <= float(args.validation_max_drawdown_pct),
        },
    }
    passed = all(item["pass"] for item in checks.values())
    return {
        "passed": passed,
        "checks": checks,
    }


def _apply_learning_to_config(config: AppConfig, tunings: list[Any]) -> AppConfig:
    strategy_cfg = {
        key: (dict(value) if isinstance(value, dict) else {})
        for key, value in config.strategies.items()
    }
    for item in tunings:
        strategy = getattr(item, "strategy", "")
        action = getattr(item, "action", "hold")
        suggested_weight = float(getattr(item, "suggested_weight", 1.0))
        if not strategy:
            continue
        current = dict(strategy_cfg.get(strategy, {}))
        if action == "pause":
            current["enabled"] = False
        elif action in {"increase", "decrease"}:
            current["enabled"] = True
            current["weight"] = round(max(0.01, min(3.0, suggested_weight)), 3)
        strategy_cfg[strategy] = current
    return replace(config, strategies=strategy_cfg)


def run_backtest_validation(config: AppConfig, args: argparse.Namespace) -> dict[str, Any]:
    cycles = max(1, int(args.backtest_cycles))
    journal_path = _validation_journal_path("backtest")
    run_cfg, orchestrator, journal, exchange = _build_validation_stack(
        config=config,
        seed=int(args.validation_seed),
        use_llm=bool(args.validation_use_llm),
        journal_path=journal_path,
    )
    try:
        start_equity = float(exchange.get_balance().get("equity_usdt", run_cfg.exchange.initial_cash_usdt))
        summaries = _run_cycles(orchestrator, cycles=cycles)
        try:
            exchange.settle_all()
        except Exception:
            pass
        end_equity = float(exchange.get_balance().get("equity_usdt", start_equity))
        execution_rows = journal.execution_summary(limit=max(2000, cycles * 20))
        metrics = _compute_metrics(
            cycle_summaries=summaries,
            execution_rows=execution_rows,
            start_equity=start_equity,
            end_equity=end_equity,
        )
        gate = _evaluate_gate(metrics, args)
        return {
            "mode": "backtest",
            "journal_path": portable_path(journal_path, base_dir=Path.cwd()),
            "config_mode": run_cfg.mode,
            "cycles": cycles,
            "seed": int(args.validation_seed),
            "llm_used": bool(args.validation_use_llm and run_cfg.llm.enabled),
            "metrics": metrics,
            "gate": gate,
            "recommendation": "go_paper_loop" if gate["passed"] else "revise_strategy_or_risk",
        }
    finally:
        journal.close()


def run_walk_forward_validation(config: AppConfig, args: argparse.Namespace) -> dict[str, Any]:
    windows = max(1, int(args.walk_forward_windows))
    train_cycles = max(1, int(args.walk_forward_train_cycles))
    test_cycles = max(1, int(args.walk_forward_test_cycles))
    journal_path = _validation_journal_path("walk_forward")
    run_cfg = _build_validation_config(config, journal_path=journal_path)
    base_seed = int(args.validation_seed) + 101

    window_reports: list[dict[str, Any]] = []
    all_test_summaries: list[dict[str, Any]] = []
    all_test_rows: list[dict[str, Any]] = []
    first_test_start_equity: float | None = None
    last_test_end_equity: float = float(run_cfg.exchange.initial_cash_usdt)

    for idx in range(windows):
        window_journal_path = _validation_journal_path(f"walk_forward_w{idx + 1}")
        window_cfg, orchestrator, journal, _train_exchange = _build_validation_stack(
            config=run_cfg,
            seed=base_seed + idx,
            use_llm=bool(args.validation_use_llm),
            journal_path=window_journal_path,
        )
        test_journal: TradeJournal | None = None
        try:
            _run_cycles(orchestrator, cycles=train_cycles)
            tunings = orchestrator.learning.suggest_tuning(
                current_strategy_weights=window_cfg.strategy_weights(),
                window_days=0,
                min_trades=max(3, int(args.validation_min_trades // 2)),
            )

            tuned_cfg = _apply_learning_to_config(window_cfg, tunings)
            run_cfg = _apply_learning_to_config(run_cfg, tunings)

            # Reset account/journal for out-of-sample test while preserving trained market sequence.
            test_exchange = build_exchange(tuned_cfg.exchange)
            test_journal_path = _validation_journal_path(f"walk_forward_w{idx + 1}_test")
            test_journal = TradeJournal(path=test_journal_path)
            test_orchestrator = TradingOrchestrator(
                config=tuned_cfg,
                data_collector=orchestrator.collector,
                exchange=test_exchange,
                journal=test_journal,
                llm=_build_llm(tuned_cfg, use_llm=bool(args.validation_use_llm)),
            )

            test_start_equity = float(test_exchange.get_balance().get("equity_usdt", tuned_cfg.exchange.initial_cash_usdt))
            if first_test_start_equity is None:
                first_test_start_equity = test_start_equity

            test_summaries = _run_cycles(test_orchestrator, cycles=test_cycles)
            try:
                test_exchange.settle_all()
            except Exception:
                pass
            test_end_equity = float(test_exchange.get_balance().get("equity_usdt", test_start_equity))
            last_test_end_equity = test_end_equity

            execution_rows = test_journal.execution_summary(limit=max(2000, test_cycles * 50))
            window_rows = execution_rows

            metrics = _compute_metrics(
                cycle_summaries=test_summaries,
                execution_rows=window_rows,
                start_equity=test_start_equity,
                end_equity=test_end_equity,
            )
            gate = _evaluate_gate(metrics, args)

            window_reports.append(
                {
                    "window": idx + 1,
                    "train_cycles": train_cycles,
                    "test_cycles": test_cycles,
                    "journal_path": portable_path(test_journal_path, base_dir=Path.cwd()),
                    "applied_tuning": [
                        {
                            "strategy": getattr(t, "strategy", ""),
                            "action": getattr(t, "action", ""),
                            "suggested_weight": getattr(t, "suggested_weight", None),
                            "reason": getattr(t, "reason", ""),
                        }
                        for t in tunings
                        if getattr(t, "action", "hold") in {"increase", "decrease", "pause"}
                    ][:8],
                    "metrics": metrics,
                    "gate": gate,
                }
            )
            all_test_summaries.extend(test_summaries)
            all_test_rows.extend(window_rows)
        finally:
            if test_journal is not None:
                test_journal.close()
            journal.close()

    start_equity = first_test_start_equity if first_test_start_equity is not None else run_cfg.exchange.initial_cash_usdt
    overall_metrics = _compute_metrics(
        cycle_summaries=all_test_summaries,
        execution_rows=all_test_rows,
        start_equity=float(start_equity),
        end_equity=float(last_test_end_equity),
    )
    overall_gate = _evaluate_gate(overall_metrics, args)
    return {
        "mode": "walk_forward",
        "journal_path": portable_path(journal_path, base_dir=Path.cwd()),
        "windows": windows,
        "train_cycles": train_cycles,
        "test_cycles": test_cycles,
        "seed": base_seed,
        "llm_used": bool(args.validation_use_llm and run_cfg.llm.enabled),
        "overall_metrics": overall_metrics,
        "overall_gate": overall_gate,
        "windows_result": window_reports,
        "recommendation": "go_paper_loop" if overall_gate["passed"] else "revise_strategy_or_risk",
    }


def run_validation(config_path: str, args: argparse.Namespace) -> dict[str, Any]:
    config = AppConfig.from_file(config_path)
    report: dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat(),
        "config_path": portable_path(config_path, base_dir=Path.cwd()),
        "validation": {},
    }

    if args.backtest_cycles > 0:
        report["validation"]["backtest"] = run_backtest_validation(config, args)
    if args.walk_forward_windows > 0:
        report["validation"]["walk_forward"] = run_walk_forward_validation(config, args)

    sections = report["validation"]
    section_passes = []
    for key in ["backtest", "walk_forward"]:
        section = sections.get(key)
        if not section:
            continue
        gate = section.get("gate") or section.get("overall_gate") or {}
        if isinstance(gate, dict) and "passed" in gate:
            section_passes.append(bool(gate["passed"]))

    report["validation"]["overall_passed"] = bool(section_passes) and all(section_passes)
    report["validation"]["next_step"] = (
        "paper_live_staging" if report["validation"]["overall_passed"] else "tune_strategy_and_risk"
    )
    return report


def run(config_path: str, mode: str, iterations: int, interval: int, live_confirm_token: str = "") -> None:
    config = AppConfig.from_file(config_path)
    config = config.with_mode(mode)

    if str(config.mode).lower() == "live":
        preflight = evaluate_live_preflight(config)
        if not preflight.get("passed", False):
            errors = " / ".join(preflight.get("errors", []))
            raise RuntimeError(f"live preflight failed: {errors}")
        gate = evaluate_validation_gate(config, base_dir=Path.cwd())
        if config.validation_gate.enforce_for_live and not gate.get("passed", False):
            errors = " / ".join(gate.get("errors", []))
            raise RuntimeError(f"validation gate failed: {errors}")
        if config.live_guard.enabled and config.live_guard.require_ack:
            if str(live_confirm_token or "").strip() != str(config.live_guard.confirm_token):
                raise RuntimeError("live confirm token mismatch")

    exchange = build_exchange(config.exchange)
    collector = MockMarketDataCollector(symbols=config.pipeline.universe)
    journal = TradeJournal(path=config.journal.path)
    llm = _build_llm(config, use_llm=True)

    orchestrator = TradingOrchestrator(
        config=config,
        data_collector=collector,
        exchange=exchange,
        journal=journal,
        llm=llm,
    )

    if iterations == 0:
        while True:
            summary = orchestrator.run_once()
            print(summary)
            time.sleep(interval)
    else:
        for _ in range(iterations):
            summary = orchestrator.run_once()
            print(summary)

    journal.close()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    if bool(args.skip_validation_gate):
        import os
        os.environ["TRADING_SYSTEM_SKIP_VALIDATION_GATE"] = "1"

    if str(args.multi_config or "").strip() and not args.ui_multi:
        from .multi_runtime import MultiRuntimeManager

        multi_path = Path(str(args.multi_config)).resolve()
        manager = MultiRuntimeManager(str(multi_path))
        try:
            cmd = str(args.multi_command or "status").strip().lower()
            if cmd == "status":
                payload = manager.get_status()
                print(json.dumps(payload, ensure_ascii=False, indent=2))
                return

            if cmd == "run-once":
                payload = manager.run_once_all()
                print(json.dumps(payload, ensure_ascii=False, indent=2))
                return

            interval = int(args.multi_interval or 0)
            interval_override = interval if interval > 0 else None
            start_payload = manager.start_all(
                interval_override=interval_override,
                live_confirm_token=str(args.multi_live_token or ""),
            )
            print(json.dumps(start_payload, ensure_ascii=False, indent=2))
            if cmd == "loop":
                try:
                    while True:
                        time.sleep(1.0)
                except KeyboardInterrupt:
                    stop_payload = manager.stop_all()
                    print(json.dumps(stop_payload, ensure_ascii=False, indent=2))
                    return
        finally:
            manager.close()
        return

    if args.live_readiness or str(args.live_readiness_report or "").strip():
        from .runtime import TradingRuntime

        runtime = TradingRuntime(str(config_path))
        try:
            report_arg = str(args.live_readiness_report or "").strip()
            if report_arg:
                output_path = "" if report_arg == "auto" else report_arg
                payload = runtime.save_live_readiness_report(output_path=output_path)
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(json.dumps(runtime.run_live_readiness(), ensure_ascii=False, indent=2))
        finally:
            runtime.close()
        return

    if args.live_rehearsal or str(args.live_rehearsal_report or "").strip():
        from .runtime import TradingRuntime

        runtime = TradingRuntime(str(config_path))
        try:
            report_arg = str(args.live_rehearsal_report or "").strip()
            if report_arg:
                output_path = "" if report_arg == "auto" else report_arg
                payload = runtime.save_live_rehearsal_report(output_path=output_path)
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(json.dumps(runtime.run_live_rehearsal(), ensure_ascii=False, indent=2))
        finally:
            runtime.close()
        return

    if args.exchange_probe or str(args.exchange_probe_report or "").strip():
        from .runtime import TradingRuntime

        runtime = TradingRuntime(str(config_path))
        try:
            report_arg = str(args.exchange_probe_report or "").strip()
            if report_arg:
                output_path = "" if report_arg == "auto" else report_arg
                payload = runtime.save_exchange_probe_report(output_path=output_path)
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(json.dumps(runtime.run_exchange_probe(), ensure_ascii=False, indent=2))
        finally:
            runtime.close()
        return

    if args.llm_test:
        from .runtime import TradingRuntime

        runtime = TradingRuntime(str(config_path))
        try:
            payload = runtime.test_llm_connection(sample_symbol=str(args.llm_test_symbol or "BTCUSDT"))
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        finally:
            runtime.close()
        return

    if args.ui_multi:
        from .multi_ui import create_multi_dashboard_app

        try:
            import uvicorn
        except Exception as exc:
            raise RuntimeError("멀티 대시보드를 사용하려면 pip install -r requirements.txt 로 uvicorn을 설치하세요.") from exc

        multi_config_path = str(args.multi_config or "configs/multi_accounts.sample.json")
        app = create_multi_dashboard_app(multi_config_path=multi_config_path)
        uvicorn.run(app, host=args.host, port=args.port)
        return

    if args.ui:
        from .ui import create_dashboard_app

        try:
            import uvicorn
        except Exception as exc:
            raise RuntimeError("FastAPI ??쒕낫?쒕? ?ъ슜?섎젮硫?pip install -r requirements.txt ??uvicorn ?ㅼ튂媛 ?꾩슂?⑸땲??") from exc

        app = create_dashboard_app(str(config_path))
        uvicorn.run(app, host=args.host, port=args.port)
        return

    if args.ui_desktop:
        from .desktop_dashboard import main as desktop_main

        desktop_main(str(config_path))
        return

    if args.backtest_cycles > 0 or args.walk_forward_windows > 0:
        report = run_validation(str(config_path), args)
        report_json = json.dumps(report, ensure_ascii=False, indent=2)
        print(report_json)

        report_path = str(args.validation_report or "").strip()
        targets: list[Path] = []
        if report_path:
            out = Path(report_path)
            if not out.is_absolute():
                out = Path.cwd() / out
            targets.append(out)
        try:
            cfg = AppConfig.from_file(str(config_path))
            gate_path = str(cfg.validation_gate.report_path or "").strip()
            if gate_path:
                gate_out = Path(gate_path)
                if not gate_out.is_absolute():
                    gate_out = (Path.cwd() / gate_out).resolve()
                targets.append(gate_out)
        except Exception:
            pass

        dedup = []
        seen = set()
        for item in targets:
            key = str(item.resolve())
            if key in seen:
                continue
            seen.add(key)
            dedup.append(item)
        for out in dedup:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(report_json, encoding="utf-8")
            print(f"[validation] report saved: {portable_path(out, base_dir=Path.cwd())}")

        try:
            cfg = AppConfig.from_file(str(config_path))
            history_path = str(cfg.validation_gate.history_path or "").strip()
            if history_path:
                history_out = Path(history_path)
                if not history_out.is_absolute():
                    history_out = (Path.cwd() / history_out).resolve()
                snapshot = save_validation_snapshot(
                    report=report,
                    history_path=history_out,
                    source_path=portable_path(dedup[0], base_dir=Path.cwd()) if dedup else "",
                )
                print(
                    f"[validation] history appended: {portable_path(history_out, base_dir=Path.cwd())} "
                    f"(overall_passed={snapshot.get('overall_passed')}, ts={snapshot.get('timestamp')})"
                )
        except Exception as exc:
            print(f"[validation] history append skipped: {exc}")
        return

    run(
        config_path=str(config_path),
        mode=args.mode,
        iterations=args.iterations,
        interval=args.interval,
        live_confirm_token=args.live_confirm_token,
    )


if __name__ == "__main__":
    main()

