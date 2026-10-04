"""Trades rápidos de la apertura de Nueva York (pensados para operar 9:30-11:30 y salir pronto)."""

from __future__ import annotations

import math

from ..engine import sm
from .base import Strategy


class OpeningQuick(Strategy):
    """Trade rápido de la apertura: una operación por día, salida por target, stop o tiempo.

    Modos de entrada (`mode`):
    - "market":   dirección de la 1ª vela de `or_minutes`; entra a mercado al abrir la siguiente.
    - "pullback": misma dirección, pero espera un retroceso: orden LÍMITE dentro de esa vela
                  (`entry_frac` = 0,5 -> en la mitad de la vela), válida hasta `entry_deadline`.
                  El stop queda en el extremo opuesto de la vela, así el riesgo es la mitad.
    - "confirm":  rango de `window_start` a `range_end`; entra cuando una vela de
                  `confirm_minutes` CIERRA fuera del rango (hasta `entry_deadline`).

    Stop (`stop_mode`): "extreme" (extremo de la vela / lado opuesto del rango), "mid" (mitad,
    redondeada al tick alejándose de la entrada, igual que el Pine) o "atr" (`stop_atr` x ATR(14)
    diario desde la entrada). Target: `target_r` x riesgo.
    Salida por tiempo: fin de la ventana (`window_end`).
    Filtros: gap >= `min_gap_atr` x ATR diario (día "en juego"), `direction` y `min_risk_pts`
    (no operar si el stop queda a menos de esos puntos: las comisiones se comerían el trade).
    Tamaño: `qty` fijo o `risk_usd` (contratos = floor(riesgo USD / riesgo por contrato)).
    """

    name = "opening_quick"
    description = "Trade rápido de la apertura de NY (ORB a mercado, en retroceso o con cierre de confirmación)"
    default_params = dict(
        window_start="09:30", window_end="10:30", mode="pullback", or_minutes=5,
        range_end="10:00", confirm_minutes=5, entry_frac=0.5, entry_deadline="10:00",
        stop_mode="extreme", stop_atr=0.05, buffer_ticks=0, target_r=1.5,
        min_gap_atr=0.0, atr_len=14, direction="both", min_range_ticks=4, min_risk_pts=0.0,
        qty=1, risk_usd=None, max_qty=50,
    )

    def setup(self):
        p = self.p
        if p["mode"] not in ("market", "pullback", "confirm"):
            raise ValueError("mode debe ser 'market', 'pullback' o 'confirm'")
        if p["stop_mode"] not in ("extreme", "mid", "atr"):
            raise ValueError("stop_mode debe ser 'extreme', 'mid' o 'atr'")
        self.t0 = sm(p["window_start"])
        self.t_or = self.t0 + p["or_minutes"] if p["mode"] != "confirm" else sm(p["range_end"])
        self.t_dead = sm(p["entry_deadline"])
        self.daily = {}

    def prepare(self, data):
        if self.p["min_gap_atr"] or self.p["stop_mode"] == "atr":
            from ..data import daily_bars

            d = daily_bars(data, self.p["atr_len"], rth_start=self.p["window_start"])
            self.daily = {k: (a, g) for k, a, g in zip(d.index, d["atr_prev"], d["gap_atr"])}

    def on_session_start(self, ctx):
        self.hi, self.lo, self.first_open = -math.inf, math.inf, None
        self.state = "range"  # range -> waiting -> done
        self.side = 0
        self.atr, gap = self.daily.get(ctx.date, (math.nan, math.nan))
        if ctx.n == 0 or ctx.S[0] != self.t0:
            self.state = "done"
        elif self.p["min_gap_atr"] and not gap >= self.p["min_gap_atr"]:
            self.state = "done"

    # ------------------------------------------------------------------------------------------
    def _allowed(self, side: int) -> bool:
        d = self.p["direction"]
        return side != 0 and not (side > 0 and d == "short") and not (side < 0 and d == "long")

    def _stop_for(self, side: int, entry: float) -> float:
        p = self.p
        buf = p["buffer_ticks"] * self.tick
        if p["stop_mode"] == "atr":
            return entry - side * p["stop_atr"] * self.atr
        if p["stop_mode"] == "mid":
            mid = (self.hi + self.lo) / 2
            return self.contract.round_down(mid) if side > 0 else self.contract.round_up(mid)
        return self.lo - buf if side > 0 else self.hi + buf

    def _qty(self, ctx, entry: float, stop: float) -> int:
        p = self.p
        if not p["risk_usd"]:
            return p["qty"]
        risk = abs(entry - stop) * ctx.contract.point_value
        return min(p["max_qty"], int(p["risk_usd"] // risk)) if risk > 0 else 0

    def _send(self, ctx, side: int, kind: str, entry_ref: float, limit: float | None = None):
        stop = self._stop_for(side, entry_ref)
        if not stop == stop or (entry_ref - stop) * side <= 0:  # NaN o stop del lado equivocado
            return
        if abs(entry_ref - stop) < self.p["min_risk_pts"]:
            return
        qty = self._qty(ctx, entry_ref, stop)
        if qty < 1:
            return
        args = dict(stop=stop, target_r=self.p["target_r"], tag=f"{self.p['mode']}_{'long' if side > 0 else 'short'}")
        if self.p["stop_mode"] == "atr":
            args = dict(stop_offset=abs(entry_ref - stop), target_r=self.p["target_r"], tag=args["tag"])
        if kind == "market":
            (ctx.buy if side > 0 else ctx.sell)(qty, **args)
        else:
            (ctx.buy_limit if side > 0 else ctx.sell_limit)(limit, qty, **args)

    def on_bar(self, ctx):
        if self.state == "done":
            return
        p, i = self.p, ctx.i
        s = ctx.S[i]
        self.contract = ctx.contract
        self.tick = ctx.contract.tick_size
        if self.state == "range":
            if s < self.t_or:
                if self.first_open is None:
                    self.first_open = ctx.O[i]
                self.hi = max(self.hi, ctx.H[i])
                self.lo = min(self.lo, ctx.L[i])
            if s + ctx.bar_minutes < self.t_or:
                return
            if self.hi - self.lo < p["min_range_ticks"] * self.tick or self.first_open is None:
                self.state = "done"
                return
            self.state = "waiting"
            if p["mode"] == "confirm":
                return
            c = ctx.C[i]
            side = 1 if c > self.first_open else -1 if c < self.first_open else 0
            if not self._allowed(side):
                self.state = "done"
                return
            self.side = side
            if p["mode"] == "market":
                self._send(ctx, side, "market", c)
                self.state = "done"
            else:
                rng = self.hi - self.lo
                limit = ctx.contract.round_nearest(self.hi - p["entry_frac"] * rng if side > 0
                                                   else self.lo + p["entry_frac"] * rng)
                self._send(ctx, side, "limit", limit, limit)
            return
        # state == "waiting"
        if p["mode"] == "pullback":
            if ctx.position or ctx.trades_today:
                self.state = "done"
            elif s + ctx.bar_minutes >= self.t_dead:
                ctx.cancel_entries()
                self.state = "done"
            return
        # mode == "confirm": cierre de una vela de confirm_minutes fuera del rango
        if s >= self.t_dead:
            self.state = "done"
            return
        if (s + ctx.bar_minutes - self.t0) % p["confirm_minutes"]:
            return
        c = ctx.C[i]
        side = 1 if c > self.hi else -1 if c < self.lo else 0
        if side and self._allowed(side):
            self._send(ctx, side, "market", c)
            self.state = "done"
