"""Estrategias de ruptura de rango (Opening Range Breakout y rupturas de sesión)."""

from __future__ import annotations

import math

from ..engine import sm
from .base import Strategy, atr_from_history


class ORBZarattini(Strategy):
    """ORB de 5 minutos de Zarattini & Aziz (2023), "Can Day Trading Really Be Profitable?".

    Reglas del paper (QQQ, 2016-2023):
    - Vela de los primeros `or_minutes` tras la apertura (09:30 ET).
    - Si cierra alcista -> COMPRA al open de la vela siguiente; bajista -> VENTA; doji -> nada.
    - Stop: mínimo de esa vela (largos) / máximo (cortos).
    - Target: `target_r` veces el riesgo (10R en el paper); si no se toca, se cierra al final del día.

    Variante del 2º paper (Zarattini, Barbon & Aziz 2024, "A Profitable Day Trading Strategy For
    The U.S. Equity Market"): stop a `stop_atr` x ATR(14) diario (0,10 en el paper) y salida al
    cierre (target_r=None).
    """

    name = "orb_zarattini"
    description = "ORB 5 min (Zarattini & Aziz 2023): dirección de la 1ª vela, stop en su extremo, 10R o cierre"
    default_params = dict(
        window_start="09:30", window_end="16:00", or_minutes=5, target_r=10.0,
        stop_atr=None, atr_len=14, direction="both", min_range_ticks=4, qty=1,
    )

    def setup(self):
        self.t0 = sm(self.p["window_start"])
        self.t_or = self.t0 + self.p["or_minutes"]

    def on_session_start(self, ctx):
        self.hi, self.lo, self.first_open, self.done = -math.inf, math.inf, None, False
        if ctx.n == 0 or ctx.S[0] != self.t0:
            self.done = True  # falta la barra de apertura: no se opera ese día
        self.atr = atr_from_history(ctx.history, self.p["atr_len"], true_range=True)
        if self.p["stop_atr"] and self.atr is None:
            self.done = True

    def on_bar(self, ctx):
        if self.done:
            return
        i = ctx.i
        s = ctx.S[i]
        if s >= self.t_or:
            self.done = True
            return
        if self.first_open is None:
            self.first_open = ctx.O[i]
        self.hi = max(self.hi, ctx.H[i])
        self.lo = min(self.lo, ctx.L[i])
        if s == self.t_or - 1:
            self.done = True
            if self.hi - self.lo < self.p["min_range_ticks"] * ctx.contract.tick_size:
                return
            close, d, p = ctx.C[i], self.p["direction"], self.p
            if p["stop_atr"]:
                long_stop = short_stop = None
                offset = p["stop_atr"] * self.atr
            else:
                long_stop, short_stop, offset = self.lo, self.hi, None
            if close > self.first_open and d in ("both", "long"):
                ctx.buy(p["qty"], stop=long_stop, stop_offset=offset, target_r=p["target_r"], tag="orb_long")
            elif close < self.first_open and d in ("both", "short"):
                ctx.sell(p["qty"], stop=short_stop, stop_offset=offset, target_r=p["target_r"], tag="orb_short")


class RangeBreakout(Strategy):
    """Ruptura de un rango horario con órdenes stop OCO (un solo trade por día).

    Sirve para:
    - ORB clásico de índices (rango 09:30-10:00, se opera la ruptura hasta el mediodía).
    - ORB del petróleo en la apertura de NYMEX (rango 09:00-09:15 ET).
    - "London breakout" / ruptura del rango asiático en oro y EUR/USD (rango 19:00-03:00 ET).

    Stop: lado opuesto del rango ("opposite") o mitad del rango ("mid").
    Target: `target_r` x riesgo; con target_r=None se mantiene hasta `exit_time`.
    Filtro opcional: ancho del rango entre min_range_atr y max_range_atr veces el rango medio
    de las últimas `atr_len` sesiones (evita rangos ridículamente estrechos o gigantes).
    """

    name = "range_breakout"
    description = "Ruptura de rango horario con stops OCO, stop en el lado opuesto/mitad, target en R"
    default_params = dict(
        window_start="09:30", window_end="16:00",
        range_start="09:30", range_end="10:00", trade_end="12:00", exit_time="16:00",
        buffer_ticks=1, stop_mode="opposite", target_r=1.5, direction="both",
        atr_len=14, min_range_atr=0.0, max_range_atr=99.0, qty=1,
    )

    def setup(self):
        p = self.p
        self.t_rs, self.t_re = sm(p["range_start"]), sm(p["range_end"])
        self.t_te, self.t_ex = sm(p["trade_end"]), sm(p["exit_time"])
        if p["window_end"] == p["exit_time"]:
            self.t_ex = 10**9  # se sale al final de la ventana (lo hace el motor)
        if p["stop_mode"] not in ("opposite", "mid"):
            raise ValueError("stop_mode debe ser 'opposite' o 'mid'")

    def on_session_start(self, ctx):
        self.hi, self.lo = -math.inf, math.inf
        self.armed = self.done = self.exit_sent = False
        self.atr = atr_from_history(ctx.history, self.p["atr_len"])

    def on_bar(self, ctx):
        i = ctx.i
        s = ctx.S[i]
        if self.t_rs <= s < self.t_re:
            self.hi = max(self.hi, ctx.H[i])
            self.lo = min(self.lo, ctx.L[i])
        if not self.done and s >= self.t_re - 1 and self.hi > -math.inf:
            self.done = True
            if s >= self.t_te - 1:
                return
            self._arm(ctx)
        if self.armed and s >= self.t_te - 1:
            ctx.cancel_entries()
            self.armed = False
        if ctx.position and not self.exit_sent and s >= self.t_ex - 1:
            ctx.flatten("time_exit")
            self.exit_sent = True

    def _arm(self, ctx):
        p, tick = self.p, ctx.contract.tick_size
        rng = self.hi - self.lo
        if rng < 2 * tick:
            return
        if self.atr and not (p["min_range_atr"] * self.atr <= rng <= p["max_range_atr"] * self.atr):
            return
        buf = p["buffer_ticks"] * tick
        mid = (self.hi + self.lo) / 2
        long_px, short_px = self.hi + buf, self.lo - buf
        long_stop = self.lo - buf if p["stop_mode"] == "opposite" else mid
        short_stop = self.hi + buf if p["stop_mode"] == "opposite" else mid
        tr = p["target_r"]
        if p["direction"] in ("both", "long"):
            ctx.buy_stop(long_px, p["qty"], stop=long_stop, target_r=tr, oco="rb", tag="break_long")
        if p["direction"] in ("both", "short"):
            ctx.sell_stop(short_px, p["qty"], stop=short_stop, target_r=tr, oco="rb", tag="break_short")
        self.armed = True
