"""Paper-trading simulation engine. SIMULATION ONLY — never places real orders."""

from .backtester import SIMULATION_LABEL, run_backtest
from .forward import ForwardSimulator
from .metrics import performance_metrics
from .strategies import STRATEGIES, get_strategy

__all__ = ["SIMULATION_LABEL", "run_backtest", "ForwardSimulator", "performance_metrics", "STRATEGIES", "get_strategy"]
