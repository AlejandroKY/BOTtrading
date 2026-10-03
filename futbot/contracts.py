"""Especificaciones de contratos de futuros (CME Group).

Las comisiones son estimaciones "todo incluido" (broker + exchange + NFA) por contrato y por
viaje completo (entrada + salida), del orden de lo que cobran las prop firms en 2026.
Ajústalas a tu cuenta real: en estrategias con stops cortos cambian mucho el resultado.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Contract:
    symbol: str
    name: str
    tick_size: float  # movimiento mínimo de precio
    tick_value: float  # USD por tick y por contrato
    commission_rt: float  # USD por contrato, ida y vuelta
    rth_start: str  # horario "principal" (ET) que usan las estrategias por defecto
    rth_end: str  # cierre / settlement (ET)

    @property
    def point_value(self) -> float:
        """USD por punto completo de precio y por contrato."""
        return self.tick_value / self.tick_size

    def round_up(self, price: float) -> float:
        return math.ceil(round(price / self.tick_size, 6)) * self.tick_size

    def round_down(self, price: float) -> float:
        return math.floor(round(price / self.tick_size, 6)) * self.tick_size

    def round_nearest(self, price: float) -> float:
        return round(price / self.tick_size) * self.tick_size

    def with_costs(self, commission_rt: float | None = None) -> "Contract":
        return self if commission_rt is None else replace(self, commission_rt=commission_rt)


_MINI_FEE = 4.50
_MICRO_FEE = 1.40

CONTRACTS: dict[str, Contract] = {
    c.symbol: c
    for c in [
        # Índices bursátiles (CME / CBOT) — horario cash 09:30-16:00 ET
        Contract("ES", "E-mini S&P 500", 0.25, 12.50, _MINI_FEE, "09:30", "16:00"),
        Contract("MES", "Micro E-mini S&P 500", 0.25, 1.25, _MICRO_FEE, "09:30", "16:00"),
        Contract("NQ", "E-mini Nasdaq-100", 0.25, 5.00, _MINI_FEE, "09:30", "16:00"),
        Contract("MNQ", "Micro E-mini Nasdaq-100", 0.25, 0.50, _MICRO_FEE, "09:30", "16:00"),
        Contract("RTY", "E-mini Russell 2000", 0.10, 5.00, _MINI_FEE, "09:30", "16:00"),
        Contract("M2K", "Micro E-mini Russell 2000", 0.10, 0.50, _MICRO_FEE, "09:30", "16:00"),
        Contract("YM", "E-mini Dow", 1.0, 5.00, _MINI_FEE, "09:30", "16:00"),
        Contract("MYM", "Micro E-mini Dow", 1.0, 0.50, _MICRO_FEE, "09:30", "16:00"),
        # Metales (COMEX) — sesión principal 08:20-13:30 ET
        Contract("GC", "Gold", 0.10, 10.00, _MINI_FEE, "08:20", "13:30"),
        Contract("MGC", "Micro Gold", 0.10, 1.00, _MICRO_FEE, "08:20", "13:30"),
        # Energía (NYMEX) — sesión principal 09:00-14:30 ET
        Contract("CL", "Crude Oil WTI", 0.01, 10.00, _MINI_FEE, "09:00", "14:30"),
        Contract("MCL", "Micro WTI Crude Oil", 0.01, 1.00, _MICRO_FEE, "09:00", "14:30"),
        # Tasas (CBOT) — sesión principal 08:20-15:00 ET
        Contract("ZN", "10-Year T-Note", 1 / 64, 15.625, _MINI_FEE, "08:20", "15:00"),
        # Divisas (CME) — settlement 15:00 ET (14:00 CT)
        Contract("6E", "Euro FX", 0.00005, 6.25, _MINI_FEE, "08:20", "15:00"),
        Contract("M6E", "Micro EUR/USD", 0.0001, 1.25, _MICRO_FEE, "08:20", "15:00"),
    ]
}


def get_contract(symbol: str) -> Contract:
    try:
        return CONTRACTS[symbol.upper()]
    except KeyError as exc:
        raise KeyError(f"Contrato desconocido: {symbol}. Disponibles: {', '.join(CONTRACTS)}") from exc
