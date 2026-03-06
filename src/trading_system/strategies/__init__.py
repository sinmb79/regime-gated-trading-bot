from .base import TradingStrategy
from .grid import GridStrategy
from .trend import TrendStrategy
from .defensive import DefensiveStrategy
from .funding_arb import FundingArbStrategy
from .indicator import BollingerReversionStrategy, EmaCrossoverStrategy, VolumeBreakoutStrategy


STRATEGY_MAP = {
    "grid": GridStrategy,
    "trend": TrendStrategy,
    "defensive": DefensiveStrategy,
    "funding_arb": FundingArbStrategy,
    "bollinger_reversion": BollingerReversionStrategy,
    "ema_crossover": EmaCrossoverStrategy,
    "volume_breakout": VolumeBreakoutStrategy,
}


def build_strategies(configs):
    strategies = []
    for key, cls in STRATEGY_MAP.items():
        cfg = configs.get(key, {}) if isinstance(configs, dict) else {}
        if cfg.get("enabled", True):
            strategies.append(
                cls(weight=cfg.get("weight", 1.0), cfg=cfg)
            )
    return strategies
