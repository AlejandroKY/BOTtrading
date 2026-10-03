from .base import Strategy
from .momentum import LastHalfHour, NoiseArea
from .orb import ORBZarattini, RangeBreakout
from .reversion import GapFill, TimeOfDay

STRATEGIES = {cls.name: cls for cls in (ORBZarattini, RangeBreakout, NoiseArea, LastHalfHour, GapFill, TimeOfDay)}


def make_strategy(name: str, **params) -> Strategy:
    try:
        return STRATEGIES[name](**params)
    except KeyError as exc:
        raise KeyError(f"Estrategia desconocida: {name}. Disponibles: {', '.join(STRATEGIES)}") from exc


__all__ = ["Strategy", "STRATEGIES", "make_strategy", "ORBZarattini", "RangeBreakout", "NoiseArea",
           "LastHalfHour", "GapFill", "TimeOfDay"]
