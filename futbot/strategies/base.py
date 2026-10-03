"""Clase base de estrategias.

Una estrategia:
- declara sus parámetros por defecto en `default_params` (incluida su ventana horaria ET
  `window_start`/`window_end`: el motor sólo le pasa barras dentro de esa ventana y cierra
  cualquier posición al final de la misma);
- implementa `on_session_start`, `on_bar` y/o `on_session_end` usando el `Context`
  (ctx.O/H/L/C/V/S son listas con las barras de la sesión, ctx.i es la barra actual).

Las órdenes enviadas en `on_bar` se ejecutan desde la barra siguiente. Las enviadas en
`on_session_start` se ejecutan en la primera barra de la ventana (al open).
"""

from __future__ import annotations

from ..engine import sm


class Strategy:
    name = "base"
    description = ""
    default_params: dict = {"window_start": "09:30", "window_end": "16:00", "qty": 1}

    def __init__(self, **params):
        unknown = set(params) - set(self.default_params)
        if unknown:
            raise ValueError(f"{self.name}: parámetros desconocidos {sorted(unknown)}. "
                             f"Válidos: {sorted(self.default_params)}")
        self.p = {**self.default_params, **params}
        self.setup()

    def window(self) -> tuple[int, int]:
        w0, w1 = sm(self.p["window_start"]), sm(self.p["window_end"])
        if w1 == 0:
            w1 = 1440  # ventana que termina justo a las 18:00
        return w0, w1

    # Hooks -------------------------------------------------------------------------------------
    def setup(self) -> None:
        """Pre-cálculos a partir de self.p (se llama en __init__)."""

    def on_session_start(self, ctx) -> None:
        pass

    def on_bar(self, ctx) -> None:
        pass

    def on_session_end(self, ctx) -> None:
        pass

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.p})"


def atr_from_history(history: list[dict], n: int, true_range: bool = False) -> float | None:
    """Rango medio de las últimas n sesiones de la ventana de la estrategia.

    true_range=True usa el True Range (incluye el gap con el cierre anterior), como el ATR clásico.
    """
    if len(history) < n + (1 if true_range else 0):
        return None
    if not true_range:
        return sum(r["high"] - r["low"] for r in history[-n:]) / n
    total = 0.0
    for prev, cur in zip(history[-n - 1:-1], history[-n:]):
        total += max(cur["high"], prev["close"]) - min(cur["low"], prev["close"])
    return total / n


def vol_target_qty(history: list[dict], point_value: float, target_usd: float, lookback: int,
                   max_qty: int) -> int | None:
    """Contratos para que la volatilidad diaria esperada sea ~`target_usd` (sizing por volatilidad).

    Usa la desviación típica de los retornos cierre-a-cierre de las últimas `lookback` sesiones.
    Devuelve 0 si ni un contrato cabe en el presupuesto (día demasiado volátil) y None si no hay historia.
    """
    if len(history) < lookback + 1:
        return None
    closes = [r["close"] for r in history[-lookback - 1:]]
    rets = [b / a - 1.0 for a, b in zip(closes[:-1], closes[1:])]
    mean = sum(rets) / len(rets)
    sd = (sum((x - mean) ** 2 for x in rets) / (len(rets) - 1)) ** 0.5
    if sd <= 0:
        return max_qty
    usd_vol_per_contract = sd * closes[-1] * point_value
    return int(min(max_qty, target_usd // usd_vol_per_contract))
