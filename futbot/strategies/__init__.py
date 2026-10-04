from .base import Strategy
from .momentum import LastHalfHour, NoiseArea, NoiseGap10
from .opening import OpeningQuick
from .orb import ORBZarattini, RangeBreakout
from .puntaje import ORBPuntaje
from .reversion import GapFill, TimeOfDay

STRATEGIES = {cls.name: cls for cls in (ORBZarattini, RangeBreakout, NoiseArea, LastHalfHour, GapFill, TimeOfDay,
                                        OpeningQuick, ORBPuntaje, NoiseGap10)}


def make_strategy(name: str, **params) -> Strategy:
    try:
        return STRATEGIES[name](**params)
    except KeyError as exc:
        raise KeyError(f"Estrategia desconocida: {name}. Disponibles: {', '.join(STRATEGIES)}") from exc


__all__ = ["Strategy", "STRATEGIES", "make_strategy", "ORBZarattini", "RangeBreakout", "NoiseArea",
           "LastHalfHour", "GapFill", "TimeOfDay", "OpeningQuick", "ORBPuntaje", "NoiseGap10"]
