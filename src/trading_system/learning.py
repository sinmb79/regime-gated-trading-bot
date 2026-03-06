from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import mean
from typing import Dict, List

from .journal import TradeJournal


@dataclass
class StrategyMetric:
    strategy: str
    trades: int
    avg_pnl: float
    win_rate: float
    suggestion: str


@dataclass
class StrategyTuning:
    strategy: str
    action: str
    weight_multiplier: float
    current_weight: float
    suggested_weight: float
    reason: str
    confidence: float


class LearningEngine:
    def __init__(self, journal: TradeJournal):
        self.journal = journal

    def summarize(self, window_days: int = 14) -> List[StrategyMetric]:
        cutoff_ts = None
        if window_days > 0:
            cutoff_ts = (datetime.utcnow() - timedelta(days=window_days)).isoformat()

        rows = self.journal.strategy_signal_rows(limit=500, since_ts=cutoff_ts)
        by_strategy: Dict[str, List[float]] = {}
        for strategy, pnl in rows:
            by_strategy.setdefault(strategy, []).append(float(pnl or 0.0))

        result = []
        for strategy, pnls in by_strategy.items():
            trades = len(pnls)
            if trades == 0:
                continue
            wins = len([x for x in pnls if x > 0])
            metric = StrategyMetric(
                strategy=strategy,
                trades=trades,
                avg_pnl=mean(pnls),
                win_rate=wins / trades,
                suggestion="",
            )
            if metric.win_rate < 0.45 and metric.avg_pnl < 0:
                metric.suggestion = "손실이 잦고 기대수익이 낮아 비중 하향 필요"
            elif metric.win_rate > 0.65 and metric.avg_pnl > 0:
                metric.suggestion = "안정적 수익 구간, 비중을 소폭 상향 가능"
            else:
                metric.suggestion = "현 상태 유지"

            self.journal.record_feedback(strategy, "win_rate", metric.win_rate, metric.suggestion)
            result.append(metric)

        return result

    def suggest_tuning(
        self,
        current_strategy_weights: Dict[str, float],
        window_days: int = 14,
        min_trades: int = 8,
    ) -> List[StrategyTuning]:
        metrics = self.summarize(window_days=window_days)
        suggestions: List[StrategyTuning] = []

        for metric in metrics:
            current = float(current_strategy_weights.get(metric.strategy, 1.0))

            if metric.trades < min_trades:
                suggestions.append(
                    StrategyTuning(
                        strategy=metric.strategy,
                        action="hold",
                        weight_multiplier=1.0,
                        current_weight=current,
                        suggested_weight=current,
                        reason="샘플 수가 적어 보류", 
                        confidence=min(1.0, metric.trades / min_trades),
                    )
                )
                continue

            if metric.win_rate < 0.38 and metric.avg_pnl < 0:
                multiplier = 0.65
                action = "decrease"
                reason = "승률/평균손익 모두 약함: 비중 축소"
            elif metric.win_rate > 0.70 and metric.avg_pnl > 0:
                multiplier = 1.12
                action = "increase"
                reason = "연속 승률이 양호: 비중 확대"
            elif metric.win_rate < 0.28 and metric.avg_pnl < 0 and metric.trades >= 20:
                multiplier = 0.0
                action = "pause"
                reason = "심각한 성능 악화: 일시 비활성 권고"
            else:
                multiplier = 1.0
                action = "hold"
                reason = "안정 구간: 조정 없음"

            if action in {"decrease", "increase"}:
                target = round(max(0.05, min(2.0, current * multiplier)), 3)
            elif action == "pause":
                target = 0.0
            else:
                target = current

            suggestions.append(
                StrategyTuning(
                    strategy=metric.strategy,
                    action=action,
                    weight_multiplier=multiplier,
                    current_weight=current,
                    suggested_weight=target,
                    reason=reason,
                    confidence=min(0.99, 0.35 + metric.win_rate),
                )
            )

        return suggestions




