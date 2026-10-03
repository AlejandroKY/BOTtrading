"""Utilidades para fabricar barras sintéticas de 1 minuto en hora de Nueva York."""

from __future__ import annotations

import pandas as pd

from futbot.strategies.base import Strategy

ET = "America/New_York"


def bars(day: str, rows: list[tuple]) -> pd.DataFrame:
    """rows: (HH:MM, open, high, low, close[, volume]) en ET para la fecha `day`."""
    idx, data = [], []
    for r in rows:
        hhmm, o, h, l, c = r[:5]
        v = r[5] if len(r) > 5 else 100.0
        idx.append(pd.Timestamp(f"{day} {hhmm}", tz=ET))
        data.append((o, h, l, c, v))
    return pd.DataFrame(data, columns=["open", "high", "low", "close", "volume"], index=pd.DatetimeIndex(idx))


def flat_session(day: str, start: str, n: int, price: float, step: float = 0.0, rng: float = 0.25) -> pd.DataFrame:
    """n barras consecutivas desde `start`, con tendencia `step` por barra y rango +-rng."""
    t0 = pd.Timestamp(f"{day} {start}", tz=ET)
    rows = []
    p = price
    for k in range(n):
        o = p
        c = p + step
        rows.append(((t0 + pd.Timedelta(minutes=k)).strftime("%H:%M"), o, max(o, c) + rng, min(o, c) - rng, c))
        p = c
    return bars(day, rows)


class Scripted(Strategy):
    """Estrategia de test: ejecuta acciones programadas por índice de barra."""

    name = "scripted"
    default_params = dict(window_start="09:30", window_end="16:00", actions=None, at_start=None)

    def on_session_start(self, ctx):
        if self.p["at_start"]:
            self.p["at_start"](ctx)

    def on_bar(self, ctx):
        act = (self.p["actions"] or {}).get(ctx.i)
        if act:
            act(ctx)
