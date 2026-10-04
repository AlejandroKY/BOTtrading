"""Motor de backtesting intradía barra a barra (event-driven) para futuros.

Pensado para estrategias de prop firm: cada estrategia declara una ventana horaria (ET) y toda
posición abierta se cierra al final de esa ventana (nada de overnight).

Supuestos de ejecución (conservadores a propósito):
- Las órdenes que la estrategia envía al cierre de una barra se procesan desde la barra siguiente.
- Market: se llena al OPEN de la barra siguiente +/- `slippage_ticks` (por defecto 0,5 tick).
- Stop: se activa si el high/low de la barra toca el precio; se llena al peor entre el open y el
  precio del stop (gaps), +/- `stop_slippage_ticks` (por defecto 1 tick).
- Limit (incluidos los targets): sólo se llena si el precio ATRAVIESA el límite por
  `limit_penetration_ticks` (por defecto 1 tick), sin slippage.
- Si en la misma barra se tocan el stop y el target, se asume que primero se tocó el STOP.
- Los precios de ejecución se redondean al tick del contrato en contra del trader. Con datos de
  precio medio (CFDs, mid quotes) ese redondeo + 0,5 tick equivale a cruzar el spread.
- Comisión de ida y vuelta por contrato descontada al cerrar cada trade.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Iterator, Optional

import numpy as np
import pandas as pd

from .contracts import Contract, get_contract

ET = "America/New_York"
SESSION_START = 18 * 60  # la sesión Globex de CME arranca a las 18:00 ET del día anterior


def sm(hhmm: str) -> int:
    """'09:30' -> minuto de sesión (minutos transcurridos desde las 18:00 ET del día anterior)."""
    h, m = hhmm.split(":")
    return (int(h) * 60 + int(m) - SESSION_START) % 1440


def sm_to_hhmm(x: int) -> str:
    t = (x + SESSION_START) % 1440
    return f"{t // 60:02d}:{t % 60:02d}"


@dataclass
class Order:
    id: int
    side: int  # +1 compra, -1 venta
    qty: int
    kind: str  # "market" | "stop" | "limit"
    price: Optional[float] = None
    is_entry: bool = True
    tag: str = ""
    oco: Optional[str] = None
    stop: Optional[float] = None  # stop de protección absoluto
    stop_offset: Optional[float] = None  # ...o distancia en puntos desde el precio de entrada
    target: Optional[float] = None  # target absoluto
    target_offset: Optional[float] = None  # ...o distancia en puntos
    target_r: Optional[float] = None  # ...o múltiplo del riesgo inicial (R)
    reason: str = ""


def iter_sessions(
    df: pd.DataFrame, w0: int, w1: int, start=None, end=None
) -> Iterator[tuple[date, pd.DatetimeIndex, list, list, list, list, list, list]]:
    """Divide las barras en sesiones Globex (18:00-17:00 ET) recortadas a la ventana [w0, w1)."""
    if df.index.tz is None:
        raise ValueError("El índice de datos debe tener zona horaria (usa futbot.data para cargar).")
    if not 0 <= w0 < w1 <= 1440:
        raise ValueError("Ventana horaria inválida: debe empezar después de las 18:00 ET y no cruzarlas.")
    local = df.index.tz_convert(ET).tz_localize(None)
    mod = local.hour.to_numpy() * 60 + local.minute.to_numpy()
    smin = (mod - SESSION_START) % 1440
    sdate = (local + pd.Timedelta(hours=6)).normalize()
    mask = (smin >= w0) & (smin < w1) & (sdate.dayofweek.to_numpy() < 5)
    if start is not None:
        mask &= np.asarray(sdate >= pd.Timestamp(start))
    if end is not None:
        mask &= np.asarray(sdate <= pd.Timestamp(end))
    pos = np.flatnonzero(mask)
    if len(pos) == 0:
        return
    sd = sdate.to_numpy()[pos]
    cuts = np.flatnonzero(sd[1:] != sd[:-1]) + 1
    bounds = np.concatenate([[0], cuts, [len(pos)]])
    cols = [df[c].to_numpy(dtype=float)[pos] for c in ("open", "high", "low", "close", "volume")]
    smin = smin[pos]
    for a, b in zip(bounds[:-1], bounds[1:]):
        yield (
            pd.Timestamp(sd[a]).date(),
            df.index[pos[a:b]],
            *(col[a:b].tolist() for col in cols),
            smin[a:b].tolist(),
        )


class Context:
    """Lo que ve la estrategia: barras de la sesión actual, historial diario y órdenes."""

    def __init__(self, engine: "Engine"):
        self._e = engine
        self.contract: Contract = engine.contract
        self.history: list[dict] = engine.history  # una fila por sesión ya terminada (ventana)
        self.date: Optional[date] = None
        self.index: Optional[pd.DatetimeIndex] = None
        self.O: list = []
        self.H: list = []
        self.L: list = []
        self.C: list = []
        self.V: list = []
        self.S: list = []  # minuto de sesión de cada barra (ver `sm`)
        self.n = 0
        self.i = 0

    # ---- estado -------------------------------------------------------------------------
    @property
    def position(self) -> int:
        return self._e.pos_side * self._e.pos_qty

    @property
    def entry_price(self) -> Optional[float]:
        return self._e.pos_entry if self._e.pos_side else None

    @property
    def stop_price(self) -> Optional[float]:
        return self._e.pos_stop

    @property
    def trades_today(self) -> int:
        return self._e.trades_today

    @property
    def halted(self) -> bool:
        return self._e.halted

    @property
    def prev(self) -> Optional[dict]:
        return self.history[-1] if self.history else None

    def time(self, i: Optional[int] = None) -> pd.Timestamp:
        return self.index[self.i if i is None else i]

    # ---- órdenes ------------------------------------------------------------------------
    def buy(self, qty: int = 1, **bracket) -> int:
        """Compra a mercado (se llena al open de la siguiente barra)."""
        return self._e.submit(+1, "market", None, qty, **bracket)

    def sell(self, qty: int = 1, **bracket) -> int:
        return self._e.submit(-1, "market", None, qty, **bracket)

    def buy_stop(self, price: float, qty: int = 1, **bracket) -> int:
        return self._e.submit(+1, "stop", price, qty, **bracket)

    def sell_stop(self, price: float, qty: int = 1, **bracket) -> int:
        return self._e.submit(-1, "stop", price, qty, **bracket)

    def buy_limit(self, price: float, qty: int = 1, **bracket) -> int:
        return self._e.submit(+1, "limit", price, qty, **bracket)

    def sell_limit(self, price: float, qty: int = 1, **bracket) -> int:
        return self._e.submit(-1, "limit", price, qty, **bracket)

    def cancel_entries(self) -> None:
        self._e.orders = [o for o in self._e.orders if not o.is_entry]

    def flatten(self, reason: str = "exit") -> None:
        """Cancela entradas pendientes y cierra la posición a mercado en la siguiente barra."""
        self.cancel_entries()
        if self._e.pos_side and not any(not o.is_entry for o in self._e.orders):
            self._e.orders.append(Order(self._e.new_id(), -self._e.pos_side, self._e.pos_qty, "market",
                                        is_entry=False, reason=reason))

    def set_stop(self, price: Optional[float]) -> None:
        self._e.pos_stop = None if price is None else self.contract.round_nearest(price)

    def set_target(self, price: Optional[float]) -> None:
        self._e.pos_target = None if price is None else self.contract.round_nearest(price)


class Engine:
    def __init__(
        self,
        data: pd.DataFrame,
        contract: Contract | str,
        strategy,
        *,
        slippage_ticks: float = 0.5,
        stop_slippage_ticks: float = 1.0,
        commission_rt: Optional[float] = None,
        limit_penetration_ticks: int = 1,
        daily_loss_limit: Optional[float] = None,
        max_trades_per_day: Optional[int] = None,
        start=None,
        end=None,
    ):
        self.data = data
        c = get_contract(contract) if isinstance(contract, str) else contract
        self.contract = c.with_costs(commission_rt)
        self.strategy = strategy
        self.slip = slippage_ticks * self.contract.tick_size
        self.stop_slip = stop_slippage_ticks * self.contract.tick_size
        self.pen = limit_penetration_ticks * self.contract.tick_size
        self.dll = daily_loss_limit
        self.max_trades = max_trades_per_day
        self.start, self.end = start, end
        self.settings = dict(
            slippage_ticks=slippage_ticks,
            stop_slippage_ticks=stop_slippage_ticks,
            commission_rt=self.contract.commission_rt,
            limit_penetration_ticks=limit_penetration_ticks,
            daily_loss_limit=daily_loss_limit,
            max_trades_per_day=max_trades_per_day,
        )
        self.history: list[dict] = []
        self.trades: list[dict] = []
        self.days: list[dict] = []
        self.orders: list[Order] = []
        self._id = 0
        self._reset_position()
        self.ctx = Context(self)

    # ---- API usada por Context --------------------------------------------------------------
    def new_id(self) -> int:
        self._id += 1
        return self._id

    def submit(self, side: int, kind: str, price: Optional[float], qty: int, *, tag: str = "",
               oco: Optional[str] = None, stop=None, stop_offset=None, target=None,
               target_offset=None, target_r=None) -> int:
        if qty <= 0:
            raise ValueError("qty debe ser > 0")
        od = Order(self.new_id(), side, int(qty), kind, price, True, tag, oco, stop, stop_offset,
                   target, target_offset, target_r)
        self.orders.append(od)
        return od.id

    # ---- bucle principal ----------------------------------------------------------------------
    def run(self) -> "BacktestResult":
        w0, w1 = self.strategy.window()
        self.strategy.prepare(self.data)
        ctx = self.ctx
        for sdate, idx, O, H, L, C, V, S in iter_sessions(self.data, w0, w1, self.start, self.end):
            self.O, self.H, self.L, self.C, self.n = O, H, L, C, len(O)
            ctx.date, ctx.index, ctx.O, ctx.H, ctx.L, ctx.C, ctx.V, ctx.S, ctx.n = (
                sdate, idx, O, H, L, C, V, S, len(O))
            self.index = idx
            self._begin_day()
            ctx.i = 0
            self.strategy.on_session_start(ctx)
            for i in range(self.n):
                ctx.i = i
                if self.orders or self.pos_side:
                    self._process_orders(i)
                if self.pos_side:
                    self._mark(i)
                self.strategy.on_bar(ctx)
            self._end_day(sdate, O, H, L, C, S)
        return BacktestResult(
            strategy=self.strategy.name,
            params=dict(self.strategy.p),
            contract=self.contract,
            trades=pd.DataFrame(self.trades, columns=TRADE_COLUMNS),
            daily=pd.DataFrame(self.days, columns=DAY_COLUMNS).set_index("date"),
            settings=self.settings,
        )

    # ---- estado diario y de posición -----------------------------------------------------------
    def _reset_position(self) -> None:
        self.pos_side = 0
        self.pos_qty = 0
        self.pos_entry = 0.0
        self.pos_stop: Optional[float] = None
        self.pos_target: Optional[float] = None
        self.pos_risk: Optional[float] = None
        self.pos_i = -1
        self.pos_tag = ""
        self.pos_hi = -math.inf
        self.pos_lo = math.inf

    def _begin_day(self) -> None:
        self.orders = []
        self.realized = 0.0
        self.trades_today = 0
        self.halted = False
        self.d_peak = 0.0  # pico de equity intradía (relativo al inicio del día)
        self.d_min = 0.0
        self.d_max = 0.0
        self.d_maxdd = 0.0

    def _end_day(self, sdate, O, H, L, C, S) -> None:
        if self.pos_side:
            self._close(self.n - 1, C[-1] - self.pos_side * self.slip, "session_end")
        self.orders = []
        self.strategy.on_session_end(self.ctx)
        self.days.append(dict(date=sdate, pnl=self.realized, trades=self.trades_today,
                              min_eq=self.d_min, max_eq=self.d_max, max_dd=self.d_maxdd))
        self.history.append(dict(date=sdate, open=O[0], high=max(H), low=min(L), close=C[-1],
                                 first_sm=S[0], last_sm=S[-1], bars=len(O)))

    def _update_eq(self, best: float, worst: float) -> None:
        if best > self.d_peak:
            self.d_peak = best
        if self.d_peak - worst > self.d_maxdd:
            self.d_maxdd = self.d_peak - worst
        if worst < self.d_min:
            self.d_min = worst
        if best > self.d_max:
            self.d_max = best

    def _entries_allowed(self) -> bool:
        return not self.halted and (self.max_trades is None or self.trades_today < self.max_trades)

    # ---- ejecución ----------------------------------------------------------------------------
    def _process_orders(self, i: int) -> None:
        o, h, l = self.O[i], self.H[i], self.L[i]
        exited = False
        markets = [od for od in self.orders if od.kind == "market"]
        if markets:
            self.orders = [od for od in self.orders if od.kind != "market"]
            for od in markets:  # primero salidas...
                if not od.is_entry and self.pos_side:
                    self._close(i, o - self.pos_side * self.slip, od.reason or "exit")
                    exited = True
            for od in markets:  # ...luego entradas (permite revertir la posición)
                if od.is_entry and self.pos_side == 0 and self._entries_allowed():
                    if self._open(i, od, o + od.side * self.slip):
                        self._check_bracket(i, o, h, l, same_bar=True, allow_target=True)
                        exited = exited or self.pos_side == 0
        if self.pos_side and self.pos_i != i:
            self._check_bracket(i, o, h, l, same_bar=False, allow_target=True)
            exited = exited or self.pos_side == 0
        if self.pos_side == 0 and not exited and self.orders and self._entries_allowed():
            best = None
            for od in self.orders:
                if od.is_entry:
                    px = self._trigger(od, o, h, l)
                    if px is not None and (best is None or abs(px - o) < best[0]):
                        best = (abs(px - o), od, px)
            if best is not None:
                _, od, px = best
                self.orders = [x for x in self.orders
                               if x is not od and (od.oco is None or x.oco != od.oco)]
                if self._open(i, od, px):
                    self._check_bracket(i, o, h, l, same_bar=True, allow_target=od.kind != "limit")

    def _trigger(self, od: Order, o: float, h: float, l: float) -> Optional[float]:
        if od.kind == "stop":
            if od.side > 0 and h >= od.price:
                return max(o, od.price) + self.stop_slip
            if od.side < 0 and l <= od.price:
                return min(o, od.price) - self.stop_slip
        elif od.kind == "limit":
            if od.side > 0 and l <= od.price - self.pen:
                return min(o, od.price)
            if od.side < 0 and h >= od.price + self.pen:
                return max(o, od.price)
        return None

    def _open(self, i: int, od: Order, raw_px: float) -> bool:
        c = self.contract
        px = c.round_up(raw_px) if od.side > 0 else c.round_down(raw_px)
        stop = od.stop
        if stop is None and od.stop_offset is not None:
            stop = px - od.side * od.stop_offset
        if stop is not None:
            stop = c.round_nearest(stop)
            if (stop - px) * od.side >= 0:  # stop del lado equivocado (p.ej. gap): no se opera
                return False
        risk = abs(px - stop) if stop is not None else None
        if od.target is not None:
            target = od.target
        elif od.target_offset is not None:
            target = px + od.side * od.target_offset
        elif od.target_r is not None and risk:
            target = px + od.side * od.target_r * risk
        else:
            target = None
        if target is not None:
            target = c.round_nearest(target)
            if (target - px) * od.side <= 0:
                return False
        self.pos_side, self.pos_qty, self.pos_entry = od.side, od.qty, px
        self.pos_stop, self.pos_target, self.pos_risk = stop, target, risk
        self.pos_i, self.pos_tag = i, od.tag
        self.pos_hi = self.pos_lo = px
        self.trades_today += 1
        return True

    def _check_bracket(self, i: int, o: float, h: float, l: float, same_bar: bool, allow_target: bool) -> None:
        side, stop, target = self.pos_side, self.pos_stop, self.pos_target
        if stop is not None and ((side > 0 and l <= stop) or (side < 0 and h >= stop)):
            fill = stop if same_bar else (min(o, stop) if side > 0 else max(o, stop))
            self._close(i, fill - side * self.stop_slip, "stop")
        elif allow_target and target is not None and (
            (side > 0 and h >= target + self.pen) or (side < 0 and l <= target - self.pen)
        ):
            fill = target if same_bar else (max(o, target) if side > 0 else min(o, target))
            self._close(i, fill, "target")

    def _mark(self, i: int) -> None:
        h, l = self.H[i], self.L[i]
        side, entry = self.pos_side, self.pos_entry
        if h > self.pos_hi:
            self.pos_hi = h
        if l < self.pos_lo:
            self.pos_lo = l
        mult = self.contract.point_value * self.pos_qty
        best = self.realized + ((h - entry) if side > 0 else (entry - l)) * mult
        worst = self.realized + ((l - entry) if side > 0 else (entry - h)) * mult
        if self.dll is not None and worst <= -self.dll:
            # liquidación por límite de pérdida diaria: se sale al precio que deja el día en -DLL
            # (o al open si la barra ya abrió más allá de ese nivel)
            allowed = self.dll + self.realized
            px = entry - side * max(allowed, 0.0) / mult
            o = self.O[i]
            px = min(o, px) if side > 0 else max(o, px)
            self._update_eq(best, -self.dll)
            self._close(i, px - side * self.slip, "daily_loss_limit")
            self.halted = True
            self.orders = []
            return
        self._update_eq(best, worst)

    def _close(self, i: int, raw_px: float, reason: str) -> None:
        c = self.contract
        side, qty, entry = self.pos_side, self.pos_qty, self.pos_entry
        px = c.round_down(raw_px) if side > 0 else c.round_up(raw_px)
        hi, lo = max(self.pos_hi, px), min(self.pos_lo, px)
        points = (px - entry) * side
        pnl = points * c.point_value * qty - c.commission_rt * qty
        self.trades.append(dict(
            entry_time=self.index[self.pos_i], exit_time=self.index[i], side=side, qty=qty,
            entry=entry, exit=px, stop=self.pos_stop, target=self.pos_target,
            points=points, pnl=pnl,
            r=(points / self.pos_risk) if self.pos_risk else np.nan,
            mae=((lo - entry) if side > 0 else (entry - hi)),
            mfe=((hi - entry) if side > 0 else (entry - lo)),
            reason=reason, tag=self.pos_tag,
        ))
        self.realized += pnl
        self._reset_position()
        self._update_eq(self.realized, self.realized)
        if self.dll is not None and self.realized <= -self.dll:
            self.halted = True


TRADE_COLUMNS = ["entry_time", "exit_time", "side", "qty", "entry", "exit", "stop", "target",
                 "points", "pnl", "r", "mae", "mfe", "reason", "tag"]
DAY_COLUMNS = ["date", "pnl", "trades", "min_eq", "max_eq", "max_dd"]


@dataclass
class BacktestResult:
    strategy: str
    params: dict
    contract: Contract
    trades: pd.DataFrame
    daily: pd.DataFrame
    settings: dict = field(default_factory=dict)

    def summary(self) -> dict:
        from .metrics import summarize

        return summarize(self)

    def yearly(self) -> pd.DataFrame:
        from .metrics import yearly_table

        return yearly_table(self)


def run_backtest(data: pd.DataFrame, contract: Contract | str, strategy, **kwargs) -> BacktestResult:
    return Engine(data, contract, strategy, **kwargs).run()
