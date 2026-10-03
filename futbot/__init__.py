"""futbot: backtesting de estrategias intradía de futuros y simulador de evaluaciones de prop firms."""

from .contracts import CONTRACTS, Contract, get_contract
from .engine import BacktestResult, Engine, run_backtest

__version__ = "0.1.0"

__all__ = ["CONTRACTS", "Contract", "get_contract", "Engine", "BacktestResult", "run_backtest"]
