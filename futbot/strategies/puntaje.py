"""ORB de 5 minutos con puntaje de calidad (0-100) para NQ y ES: la estrategia del bot de TradingView."""

from __future__ import annotations

import math

from ..engine import sm
from .base import Strategy

# puntos máximos de cada condición del puntaje (suman 100)
PESOS = dict(overnight=30, cuerpo=25, gap=20, fuera_ayer=15, lunes=10)


def puntaje(side: int, open_: float, high: float, low: float, close: float, gap_atr: float,
            on_high: float, on_low: float, prev_high: float, prev_low: float, monday: bool) -> tuple[int, dict]:
    """Puntaje 0-100 de la vela de 9:30-9:35 (mismas reglas que el Pine).

    - overnight (30): la vela cierra por encima del máximo overnight (compras) o debajo del mínimo (ventas).
    - cuerpo (0-25): cuerpo / rango de la vela; 0 puntos con 30 % o menos, 25 con 80 % o más.
    - gap (0-20): gap en ATR; 0 puntos con 0,15 ATR, 20 con 0,60 ATR o más.
    - fuera_ayer (15): la apertura de las 9:30 quedó fuera del rango de ayer, a favor del trade.
    - lunes (10).
    Se redondea al entero (media unidad hacia arriba).
    """
    rng = high - low
    body = abs(close - open_) / rng if rng > 0 else 0.0
    parts = dict(
        overnight=PESOS["overnight"] * float(close > on_high if side > 0 else close < on_low),
        cuerpo=PESOS["cuerpo"] * min(1.0, max(0.0, (body - 0.3) / 0.5)),
        gap=PESOS["gap"] * (min(1.0, max(0.0, (gap_atr - 0.15) / 0.45)) if gap_atr == gap_atr else 0.0),
        fuera_ayer=PESOS["fuera_ayer"] * float(open_ > prev_high if side > 0 else open_ < prev_low),
        lunes=PESOS["lunes"] * float(monday),
    )
    return int(math.floor(sum(parts.values()) + 0.5)), parts


class ORBPuntaje(Strategy):
    """ORB de 5 min con puntaje: entra a las 9:35 en la dirección de la 1ª vela si el día está "en juego"
    (gap >= `min_gap_atr` x ATR) y el puntaje es >= `min_score`.

    Stop: mitad de la vela (redondeada alejándose de la entrada); no se opera si queda a menos de
    `min_risk_pts`. Salidas: parcial de `partial_qty_frac` de los contratos a `partial_r` R con stop a
    la entrada para el resto (si hay 2 o más contratos), target a `target_r` R y salida por tiempo al
    final de la ventana. Con `skip_fomc` no opera los días de anuncio de la Fed (futbot/calendario.py); está
    apagado en las recetas porque en NQ 2019-2026 no mejoró la simulación de las cuentas de fondeo.
    Guarda el puntaje de cada día con señal en `self.scores` y en el tag del trade.
    """

    name = "orb_puntaje"
    description = "ORB 5 min con puntaje de calidad 0-100 (overnight, cuerpo, gap, rango de ayer, lunes)"
    default_params = dict(
        window_start="09:30", window_end="10:35", or_minutes=5, min_gap_atr=0.15, min_score=40,
        min_risk_pts=6.0, min_range_ticks=4, target_r=10.0, partial_r=2.0, partial_qty_frac=0.5,
        be_after_partial=True, atr_len=14, direction="both", qty=1, risk_usd=None, max_qty=50, skip_fomc=False,
    )

    def setup(self):
        self.t0 = sm(self.p["window_start"])
        self.t_or = self.t0 + self.p["or_minutes"]
        self.daily = {}
        self.scores = {}
        if self.p["skip_fomc"]:
            from ..calendario import fomc_dates

            self.skip = fomc_dates()
        else:
            self.skip = frozenset()

    def prepare(self, data):
        from ..data import daily_bars

        d = daily_bars(data, self.p["atr_len"], rth_start=self.p["window_start"])
        cols = ["gap_atr", "on_high", "on_low", "prev_rth_high", "prev_rth_low"]
        self.daily = {k: tuple(v) for k, v in zip(d.index, d[cols].itertuples(index=False, name=None))}

    def on_session_start(self, ctx):
        self.hi, self.lo, self.first_open = -math.inf, math.inf, None
        self.done = ctx.n == 0 or ctx.S[0] != self.t0
        self.feat = self.daily.get(ctx.date)
        if self.feat is None or not self.feat[0] >= self.p["min_gap_atr"] or ctx.date in self.skip:
            self.done = True

    def on_bar(self, ctx):
        if self.done:
            return
        p, i = self.p, ctx.i
        s = ctx.S[i]
        if s < self.t_or:
            if self.first_open is None:
                self.first_open = ctx.O[i]
            self.hi = max(self.hi, ctx.H[i])
            self.lo = min(self.lo, ctx.L[i])
        if s + ctx.bar_minutes < self.t_or:  # todavía no termina la vela de 5 min
            return
        self.done = True
        c, o, tick = ctx.C[i], self.first_open, ctx.contract.tick_size
        side = 1 if c > o else -1 if c < o else 0
        if side == 0 or self.hi - self.lo < p["min_range_ticks"] * tick:
            return
        if (p["direction"] == "long" and side < 0) or (p["direction"] == "short" and side > 0):
            return
        mid = (self.hi + self.lo) / 2
        stop = ctx.contract.round_down(mid) if side > 0 else ctx.contract.round_up(mid)
        risk = (c - stop) * side
        if risk <= 0 or risk < p["min_risk_pts"]:
            return
        gap_atr, on_h, on_l, pd_h, pd_l = self.feat
        score, _ = puntaje(side, o, self.hi, self.lo, c, gap_atr, on_h, on_l, pd_h, pd_l, ctx.date.weekday() == 0)
        self.scores[ctx.date] = (score, side)
        if score < p["min_score"]:
            return
        qty = p["qty"]
        if p["risk_usd"]:
            qty = min(p["max_qty"], int(p["risk_usd"] // (risk * ctx.contract.point_value)))
        if qty < 1:
            return
        part = int(qty * p["partial_qty_frac"]) if p["partial_r"] else 0
        (ctx.buy if side > 0 else ctx.sell)(qty, stop=stop, target_r=p["target_r"], tag=f"puntaje={score}",
                                             partial_r=p["partial_r"] if part else None, partial_qty=part,
                                             be_after_partial=p["be_after_partial"])
