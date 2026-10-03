"""Estrategias de reversión a la media y de sesgo horario."""

from __future__ import annotations

from ..engine import sm
from .base import Strategy


class GapFill(Strategy):
    """Cierre del gap de apertura (gap fade) en índices.

    Gap = open de las 09:30 - cierre de las 16:00 del día anterior. Si el gap (en %) está entre
    `min_gap_pct` y `max_gap_pct`, se opera en contra del gap a la apertura:
    - Target: cierre previo (gap cerrado al 100%; `target_fill` < 1 para cierre parcial).
    - Stop: `stop_gap_mult` veces el tamaño del gap más allá de la entrada.
    - Salida por tiempo en `exit_time`.
    Estadística de partida (ES 2015-2025): ~60-70% de los gaps pequeños se cierran en la sesión.
    """

    name = "gap_fill"
    description = "Fade del gap de apertura con target en el cierre previo (alto winrate)"
    default_params = dict(
        window_start="09:30", window_end="16:00", min_gap_pct=0.10, max_gap_pct=0.60,
        target_fill=1.0, stop_gap_mult=1.0, exit_time="12:00", direction="both", qty=1,
    )

    def setup(self):
        self.t0 = sm(self.p["window_start"])
        self.t_ex = sm(self.p["exit_time"])

    def on_session_start(self, ctx):
        self.exit_sent = False
        prev = ctx.prev
        if prev is None or ctx.n == 0 or ctx.S[0] != self.t0:
            return
        p = self.p
        o, prev_close = ctx.O[0], prev["close"]
        gap = o - prev_close
        gap_pct = 100.0 * gap / prev_close
        if not (p["min_gap_pct"] <= abs(gap_pct) <= p["max_gap_pct"]):
            return
        target = o - p["target_fill"] * gap
        stop = o + p["stop_gap_mult"] * gap
        if gap > 0 and p["direction"] in ("both", "short"):
            ctx.sell(p["qty"], stop=stop, target=target, tag="gap_up_fade")
        elif gap < 0 and p["direction"] in ("both", "long"):
            ctx.buy(p["qty"], stop=stop, target=target, tag="gap_down_fade")

    def on_bar(self, ctx):
        if ctx.position and not self.exit_sent and ctx.S[ctx.i] >= self.t_ex - 1:
            ctx.flatten("time_exit")
            self.exit_sent = True


class TimeOfDay(Strategy):
    """Sesgo horario: entra a `entry_time` en dirección `side` y sale al final de la ventana.

    Ejemplo: anomalía "día vs noche" del oro (retornos diurnos negativos en COMEX):
    side=-1, ventana 08:20-13:30. Es un experimento: valida con datos recientes antes de usarlo.
    """

    name = "time_of_day"
    description = "Sesgo horario (p.ej. oro: corto en la sesión diurna de COMEX)"
    default_params = dict(
        window_start="08:20", window_end="13:30", entry_time="08:20", side=-1,
        stop_pct=None, weekdays=None, qty=1,
    )

    def setup(self):
        self.t_entry = sm(self.p["entry_time"])

    def on_session_start(self, ctx):
        self.done = False
        wd = self.p["weekdays"]
        if wd is not None and ctx.date.weekday() not in wd:
            self.done = True
            return
        if ctx.n and ctx.S[0] >= self.t_entry:
            self._enter(ctx, ctx.O[0])

    def on_bar(self, ctx):
        if not self.done and ctx.S[ctx.i] >= self.t_entry - 1:
            self._enter(ctx, ctx.C[ctx.i])

    def _enter(self, ctx, ref):
        self.done = True
        p = self.p
        stop_offset = ref * p["stop_pct"] / 100.0 if p["stop_pct"] else None
        if p["side"] > 0:
            ctx.buy(p["qty"], stop_offset=stop_offset, tag="tod_long")
        else:
            ctx.sell(p["qty"], stop_offset=stop_offset, tag="tod_short")
