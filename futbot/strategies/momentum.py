"""Estrategias de momentum intradía con base académica."""

from __future__ import annotations

from collections import deque

import numpy as np

from ..engine import sm
from .base import Strategy, vol_target_qty


class NoiseArea(Strategy):
    """Momentum intradía "Noise Area" de Zarattini, Aziz & Barbon (2024), "Beat the Market".

    - sigma(t): media de |close(t)/open_del_día - 1| a esa misma hora en los últimos `lookback` días.
    - Banda superior = max(open, cierre previo) * (1 + sigma(t)); inferior = min(open, cierre previo) * (1 - sigma(t)).
    - Cada `check_minutes` (10:00, 10:30, ... 15:30): si el precio está sobre la banda superior ->
      largo; bajo la inferior -> corto; dentro -> nada (es "ruido").
    - Salida: trailing stop en max(banda superior, VWAP) para largos (min(banda inferior, VWAP)
      para cortos), evaluado en los mismos checkpoints; cierre obligatorio al final del día.
    - `stop_pct` (opcional, no está en el paper): stop duro para acotar el riesgo entre checkpoints,
      útil en prop firms.
    - `vol_target_usd` (opcional, como el paper): nº de contratos para que la volatilidad diaria
      esperada sea ~ese importe en USD (con tope `max_qty`); si no cabe ni 1 contrato, no opera.
    """

    name = "noise_area"
    description = "Momentum intradía 'Noise Area' (Zarattini, Aziz & Barbon 2024)"
    default_params = dict(
        window_start="09:30", window_end="16:00", lookback=14, check_minutes=30,
        first_check="10:00", last_entry="15:30", band_mult=1.0, use_vwap=True,
        allow_reversal=True, stop_pct=None, direction="both", qty=1,
        vol_target_usd=None, max_qty=10,
    )

    def setup(self):
        p = self.p
        self.t0, self.t1 = self.window()
        self.n = self.t1 - self.t0
        self.first_check = sm(p["first_check"])
        self.last_entry = sm(p["last_entry"])
        self.profiles: deque = deque(maxlen=p["lookback"])

    def on_session_start(self, ctx):
        prev = ctx.prev
        self.prev_close = prev["close"] if prev else None
        self.day_open = None
        self.move = np.full(self.n, np.nan)
        self.pv = 0.0
        self.vol = 0.0
        self.skip = ctx.n == 0 or ctx.S[0] != self.t0
        self.qty = self.p["qty"]
        if self.p["vol_target_usd"]:
            q = vol_target_qty(ctx.history, ctx.contract.point_value, self.p["vol_target_usd"],
                               self.p["lookback"], self.p["max_qty"])
            self.qty = q or 0
        if len(self.profiles) == self.p["lookback"]:
            self.sigma = np.nanmean(np.vstack(self.profiles), axis=0).tolist()
        else:
            self.sigma = None

    def on_bar(self, ctx):
        i, p = ctx.i, self.p
        o, h, l, c = ctx.O[i], ctx.H[i], ctx.L[i], ctx.C[i]
        k = ctx.S[i] - self.t0
        if self.day_open is None:
            self.day_open = o
        self.move[k] = abs(c / self.day_open - 1.0)
        v = ctx.V[i] if ctx.V[i] > 0 else 1.0
        self.pv += (h + l + c) / 3.0 * v
        self.vol += v
        if self.skip or self.sigma is None or self.prev_close is None:
            return
        t_end = ctx.S[i] + 1  # hora de cierre de esta barra
        if t_end < self.first_check or (t_end - self.t0) % p["check_minutes"]:
            return
        sig = self.sigma[k]
        if sig != sig:  # NaN
            return
        sig *= p["band_mult"]
        ub = max(self.day_open, self.prev_close) * (1 + sig)
        lb = min(self.day_open, self.prev_close) * (1 - sig)
        vwap = self.pv / self.vol
        pos = ctx.position
        can_long = t_end <= self.last_entry and p["direction"] in ("both", "long")
        can_short = t_end <= self.last_entry and p["direction"] in ("both", "short")
        if pos == 0:
            if c > ub and can_long:
                self._enter(ctx, +1, c)
            elif c < lb and can_short:
                self._enter(ctx, -1, c)
        elif pos > 0:
            if c < (max(ub, vwap) if p["use_vwap"] else ub):
                ctx.flatten("trail")
                if c < lb and can_short and p["allow_reversal"]:
                    self._enter(ctx, -1, c)
        else:
            if c > (min(lb, vwap) if p["use_vwap"] else lb):
                ctx.flatten("trail")
                if c > ub and can_long and p["allow_reversal"]:
                    self._enter(ctx, +1, c)

    def _enter(self, ctx, side, ref):
        if self.qty <= 0:
            return
        sp = self.p["stop_pct"]
        stop_offset = ref * sp / 100.0 if sp else None
        if side > 0:
            ctx.buy(self.qty, stop_offset=stop_offset, tag="noise_long")
        else:
            ctx.sell(self.qty, stop_offset=stop_offset, tag="noise_short")

    def on_session_end(self, ctx):
        if not self.skip and np.isfinite(self.move).mean() > 0.8:
            self.profiles.append(self.move)


class LastHalfHour(Strategy):
    """Momentum de la última media hora: Gao, Han, Li & Zhou (2018, JFE) y Baltussen, Da,
    Lammers & Martens (2021, JFE, 60+ futuros de acciones, bonos, materias primas y divisas).

    - predictor="first_half_hour": retorno desde el cierre previo hasta los primeros 30 min de la sesión (Gao et al.).
    - predictor="rest_of_day": retorno desde el cierre previo hasta 30 min antes del cierre (Baltussen et al.).
    - `entry_minutes_before_close` antes del cierre se entra en la dirección del predictor y se
      sale al cierre (fin de la ventana). `min_abs_ret_pct` filtra días con movimiento pequeño.
    """

    name = "last_half_hour"
    description = "Momentum de la última media hora (Gao et al. 2018; Baltussen et al. 2021)"
    default_params = dict(
        window_start="09:30", window_end="16:00", predictor="rest_of_day", first_minutes=30,
        entry_minutes_before_close=30, min_abs_ret_pct=0.0, stop_pct=None, direction="both", qty=1,
    )

    def setup(self):
        p = self.p
        if p["predictor"] not in ("first_half_hour", "rest_of_day"):
            raise ValueError("predictor debe ser 'first_half_hour' o 'rest_of_day'")
        self.t0, self.t1 = self.window()
        self.t_first = self.t0 + p["first_minutes"]
        self.t_entry = self.t1 - p["entry_minutes_before_close"]

    def on_session_start(self, ctx):
        prev = ctx.prev
        self.prev_close = prev["close"] if prev else None
        self.p_first = None
        self.done = False

    def on_bar(self, ctx):
        i, p = ctx.i, self.p
        s = ctx.S[i]
        if self.p_first is None and s >= self.t_first - 1 and s <= self.t_first + 4:
            self.p_first = ctx.C[i]
        if self.done or s < self.t_entry - 1:
            return
        self.done = True
        if s > self.t_entry + 2 or self.prev_close is None:
            return  # faltan datos alrededor de la hora de entrada
        ref = ctx.C[i] if p["predictor"] == "rest_of_day" else self.p_first
        if ref is None:
            return
        ret = 100.0 * (ref / self.prev_close - 1.0)
        if abs(ret) < p["min_abs_ret_pct"] or ret == 0:
            return
        side = 1 if ret > 0 else -1
        if (side > 0 and p["direction"] == "short") or (side < 0 and p["direction"] == "long"):
            return
        stop_offset = ctx.C[i] * p["stop_pct"] / 100.0 if p["stop_pct"] else None
        if side > 0:
            ctx.buy(p["qty"], stop_offset=stop_offset, tag="lhh_long")
        else:
            ctx.sell(p["qty"], stop_offset=stop_offset, tag="lhh_short")
