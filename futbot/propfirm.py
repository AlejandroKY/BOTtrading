"""Simulador de evaluaciones de prop firms de futuros (cuentas de fondeo).

Toma el P&L diario de un backtest hecho con 1 contrato (con su mínimo/máximo intradía y su
drawdown intradía) y responde: ¿con cuántos contratos y con qué probabilidad paso la evaluación
de tal firma antes de quemar la cuenta?

Dos métodos:
- historical: arranca una evaluación en CADA día del histórico y la sigue con los días reales
  posteriores hasta aprobar/suspender (respeta rachas reales).
- bootstrap: Monte Carlo remuestreando bloques de días (block bootstrap).

IMPORTANTE: las reglas de las firmas cambian a menudo. Los presets de abajo resumen las
condiciones públicas a octubre de 2026; verifícalas en la web oficial antes de comprar.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Optional

import numpy as np
import pandas as pd

PASS, FAIL, TIMEOUT, INCOMPLETE = "pass", "fail", "timeout", "incomplete"


@dataclass(frozen=True)
class PropRules:
    name: str
    account_size: float = 50_000
    profit_target: float = 3_000
    max_loss: float = 2_000
    drawdown: str = "eod"  # "eod" (trailing al cierre), "intraday" (trailing tick a tick) o "static"
    trail_lock: Optional[float] = 0.0  # el umbral deja de subir en account_size + trail_lock (None = nunca)
    daily_loss_limit: Optional[float] = None
    dll_fails: bool = False  # True: tocar el límite diario suspende la cuenta; False: sólo para el día
    consistency: Optional[float] = None  # mejor día <= consistency * beneficio total (0.5 = 50 %)
    min_days: int = 1  # días con trades mínimos
    max_days: Optional[int] = None  # sesiones máximas (aprox. del límite en días naturales)
    max_micros: int = 50  # límite de contratos (en micros)
    notes: str = ""


PROP_FIRMS: dict[str, PropRules] = {
    r.name: r
    for r in [
        PropRules("topstep_50k", drawdown="eod", trail_lock=0.0, consistency=0.5, min_days=2, max_micros=50,
                  notes="Trading Combine 50K: objetivo $3.000, Maximum Loss Limit $2.000 trailing EOD (se "
                        "fija en el saldo inicial), mejor día <= 50% del beneficio. DLL opcional. Bots "
                        "permitidos vía TopstepX API desde dispositivo propio (sin VPS/VPN)."),
        PropRules("apex_50k_eod", drawdown="eod", trail_lock=100.0, daily_loss_limit=1_000, dll_fails=False,
                  max_days=21, max_micros=40,
                  notes="Apex 4.0 50K EOD: objetivo $3.000, drawdown $2.000 EOD, DLL $1.000 (pausa el día), "
                        "30 días naturales (~21 sesiones), sin consistencia en evaluación. Automatización "
                        "totalmente desatendida restringida en cuentas PA: confirma la política vigente."),
        PropRules("tradeify_growth_50k", drawdown="eod", trail_lock=100.0, daily_loss_limit=1_250, dll_fails=False,
                  max_micros=40,
                  notes="Growth 50K: objetivo $3.000, drawdown $2.000 EOD, DLL $1.250 (pausa), sin consistencia "
                        "en evaluación."),
        PropRules("mffu_pro_50k", drawdown="eod", trail_lock=0.0, consistency=0.5, max_micros=50,
                  notes="MyFundedFutures Pro 50K: objetivo $3.000, drawdown $2.000 EOD, consistencia 50% en "
                        "evaluación, sin DLL. Algo trading permitido desde jul-2025."),
        PropRules("lucid_flex_50k", drawdown="eod", trail_lock=100.0, consistency=0.5, min_days=2, max_micros=40,
                  notes="LucidFlex 50K: objetivo $3.000, MLL $2.000 EOD, consistencia 50% en evaluación, 2 días mín."),
        PropRules("intraday_trailing_50k", drawdown="intraday", trail_lock=100.0, max_micros=50,
                  notes="Genérico con trailing INTRADÍA (incluye P&L no realizado), p.ej. cuentas 'intraday' "
                        "de Apex o el Rapid de MFFU. Mucho más exigente para estrategias con MFE grande."),
    ]
}


def _rules(rules: PropRules | str) -> PropRules:
    return PROP_FIRMS[rules] if isinstance(rules, str) else rules


def _day_matrix(daily: pd.DataFrame) -> np.ndarray:
    cols = ["pnl", "min_eq", "max_eq", "max_dd", "trades"]
    return daily[cols].to_numpy(dtype=float)


def run_evaluation(days: np.ndarray, rules: PropRules, scale: float = 1.0) -> tuple[str, int, float]:
    """Simula UNA evaluación recorriendo `days` (filas: pnl, min_eq, max_eq, max_dd, trades por 1 contrato).

    Devuelve (resultado, sesiones usadas, beneficio final).
    """
    a, L = rules.account_size, rules.max_loss
    lock = None if rules.trail_lock is None else a + rules.trail_lock
    balance = peak = a
    threshold = a - L
    best_day = 0.0
    traded = 0
    for n, (pnl, mn, mx, mdd, ntr) in enumerate(days, start=1):
        if ntr > 0:
            pnl, mn, mx, mdd = pnl * scale, mn * scale, mx * scale, mdd * scale
            dll = rules.daily_loss_limit
            if dll is not None and mn <= -dll:
                if rules.dll_fails:
                    return FAIL, n, balance - dll - a
                pnl, mn = -dll, -dll  # liquidado en el límite diario; el día se acaba
                mdd = min(mdd, mx + dll)
            if balance + mn <= threshold:
                return FAIL, n, balance + mn - a
            if rules.drawdown == "intraday" and mdd >= L:
                thr_t = balance + mn + mdd - L  # pico intradía previo al valle menos el drawdown
                if lock is not None:
                    thr_t = min(thr_t, lock)
                if balance + mn <= thr_t:
                    return FAIL, n, balance + mn - a
            if rules.drawdown == "intraday":
                peak = max(peak, balance + mx)
            balance += pnl
            if rules.drawdown == "eod":
                peak = max(peak, balance)
            if rules.drawdown != "static":
                new_thr = peak - L
                if lock is not None:
                    new_thr = min(new_thr, lock)
                threshold = max(threshold, new_thr)
            traded += 1
            best_day = max(best_day, pnl)
            profit = balance - a
            if (profit >= rules.profit_target and traded >= rules.min_days
                    and (rules.consistency is None or best_day <= rules.consistency * profit)):
                return PASS, n, profit
        if rules.max_days is not None and n >= rules.max_days:
            return TIMEOUT, n, balance - a
    return INCOMPLETE, len(days), balance - a


def _aggregate(outcomes: list[tuple[str, int, float]]) -> dict:
    done = [o for o in outcomes if o[0] != INCOMPLETE]
    n = len(done)
    if n == 0:
        return dict(n=0, pass_rate=np.nan, fail_rate=np.nan, timeout_rate=np.nan,
                    median_days_pass=np.nan, median_days_fail=np.nan)
    passed = [d for s, d, _ in done if s == PASS]
    failed = [d for s, d, _ in done if s == FAIL]
    return dict(
        n=n,
        pass_rate=len(passed) / n,
        fail_rate=len(failed) / n,
        timeout_rate=sum(1 for s, _, _ in done if s == TIMEOUT) / n,
        median_days_pass=float(np.median(passed)) if passed else np.nan,
        median_days_fail=float(np.median(failed)) if failed else np.nan,
    )


def historical_pass_rate(daily: pd.DataFrame, rules: PropRules | str, scale: float = 1.0, step: int = 1,
                         horizon: Optional[int] = 250) -> dict:
    """Empieza una evaluación en cada día (cada `step` días) del histórico.

    horizon: sesiones máximas por evaluación (250 = 1 año); si no aprueba ni suspende en ese
    plazo cuenta como "timeout" (en la práctica, nadie paga una evaluación eternamente).
    """
    rules = _rules(rules)
    if horizon is not None and (rules.max_days is None or rules.max_days > horizon):
        rules = replace(rules, max_days=horizon)
    days = _day_matrix(daily)
    outcomes = [run_evaluation(days[s:], rules, scale) for s in range(0, len(days), step)]
    return _aggregate(outcomes)


def bootstrap_pass_rate(daily: pd.DataFrame, rules: PropRules | str, scale: float = 1.0, n_sims: int = 2000,
                        block: int = 5, horizon: int = 250, seed: int = 0) -> dict:
    """Monte Carlo con block bootstrap (bloques de `block` días consecutivos)."""
    rules = _rules(rules)
    if rules.max_days is None or rules.max_days > horizon:
        rules = replace(rules, max_days=horizon)
    days = _day_matrix(daily)
    rng = np.random.default_rng(seed)
    n_blocks = -(-horizon // block)
    max_start = len(days) - block
    if max_start <= 0:
        raise ValueError("Muy pocos días para el bootstrap")
    outcomes = []
    for _ in range(n_sims):
        starts = rng.integers(0, max_start + 1, n_blocks)
        path = np.concatenate([days[s:s + block] for s in starts])
        outcomes.append(run_evaluation(path, rules, scale))
    return _aggregate(outcomes)


def scan_sizes(daily: pd.DataFrame, rules: PropRules | str, sizes, method: str = "historical",
               micros_per_contract: int = 1, **kw) -> pd.DataFrame:
    """Probabilidad de aprobar para distintos tamaños (número de contratos del backtest).

    micros_per_contract: 1 si el backtest se hizo con micros (MES, MNQ...), 10 si con minis.
    """
    rules = _rules(rules)
    fn = historical_pass_rate if method == "historical" else bootstrap_pass_rate
    rows = []
    for k in sizes:
        if k * micros_per_contract > rules.max_micros:
            continue
        r = fn(daily, rules, scale=k, **kw)
        rows.append(dict(size=k, **r))
    return pd.DataFrame(rows).set_index("size")


def best_size(table: pd.DataFrame) -> Optional[int]:
    if table.empty or table["pass_rate"].isna().all():
        return None
    best = table["pass_rate"].max()
    return int(table.index[(table["pass_rate"] >= best - 1e-12)].min())


def with_overrides(rules: PropRules | str, **kw) -> PropRules:
    return replace(_rules(rules), **kw)


# ---------------------------------------------------------------------------------------------
# Tamaño dinámico: el riesgo de cada trade depende del colchón que queda sobre el límite de pérdida


def escalones(cushion: float, profit: float = 0.0) -> float:
    """Riesgo por operación (USD) según el colchón sobre el límite de pérdida de la cuenta:
    $300 con $1.400 o más, $200 entre $800 y $1.400, y $100 por debajo (pensado para cuentas de 50K
    con límite de $2.000). Arriesga más cuando hay espacio y menos cerca del límite."""
    return 300.0 if cushion >= 1400 else 200.0 if cushion >= 800 else 100.0


def historical_pass_rate_sized(trades: pd.DataFrame, rules: PropRules | str, sizing=escalones,
                               days: Optional[pd.DatetimeIndex] = None, horizon: Optional[int] = 250,
                               step: int = 1) -> dict:
    """Como historical_pass_rate, pero con el tamaño decidido trade a trade según el estado de la cuenta.

    trades: una fila por trade con columnas date, R (resultado neto en múltiplos del riesgo), mae_r (peor
    excursión en contra, en R, <= 0), risk_pts (distancia al stop en puntos) y point_value.
    sizing(colchón, beneficio) -> riesgo en USD; se operan floor(riesgo / (risk_pts x point_value))
    contratos (máximo `max_micros` de la firma); si no cabe ninguno, ese trade se salta.
    days: días hábiles del histórico (por defecto, del primer al último trade). El drawdown intradía
    ("intraday") se aproxima como EOD.
    """
    rules = _rules(rules)
    t = trades.copy()
    t["date"] = pd.to_datetime(t["date"]).dt.normalize()
    if days is None:
        days = pd.bdate_range(t["date"].min(), t["date"].max())
    pos = pd.Index(days).get_indexer(t["date"])
    t = t[pos >= 0].assign(_d=pos[pos >= 0]).sort_values(["_d"])
    by_day: dict[int, list] = {}
    for d, r, m, rk, pv in zip(t["_d"], t["R"], t["mae_r"], t["risk_pts"], t["point_value"]):
        by_day.setdefault(int(d), []).append((float(r), min(float(m), 0.0), float(rk), float(pv)))
    n = len(days)
    a, L = rules.account_size, rules.max_loss
    lock = None if rules.trail_lock is None else a + rules.trail_lock
    limit = n if horizon is None else horizon
    outcomes = []
    for s in range(0, n, step):
        bal = peak = a
        thr = a - L
        best_day = 0.0
        traded = 0
        res = None
        for k in range(s, min(n, s + limit)):
            day_pnl, did = 0.0, False
            for r, m, rk, pv in by_day.get(k, ()):
                q = int(min(rules.max_micros, math.floor(sizing(bal - thr, bal - a) / (rk * pv))))
                if q < 1:
                    continue
                usd_r = q * rk * pv
                if rules.daily_loss_limit is not None and day_pnl + m * usd_r <= -rules.daily_loss_limit:
                    if rules.dll_fails:
                        res = (FAIL, k - s + 1, bal - a)
                        break
                    bal += -rules.daily_loss_limit - day_pnl
                    day_pnl, did = -rules.daily_loss_limit, True
                    break
                if bal + m * usd_r <= thr:
                    res = (FAIL, k - s + 1, bal + m * usd_r - a)
                    break
                bal += r * usd_r
                day_pnl += r * usd_r
                did = True
            if res is not None:
                break
            if did:
                if rules.drawdown != "static":
                    peak = max(peak, bal)
                    new_thr = peak - L if lock is None else min(peak - L, lock)
                    thr = max(thr, new_thr)
                if bal <= thr:
                    res = (FAIL, k - s + 1, bal - a)
                    break
                traded += 1
                best_day = max(best_day, day_pnl)
                profit = bal - a
                if (profit >= rules.profit_target and traded >= rules.min_days
                        and (rules.consistency is None or best_day <= rules.consistency * profit)):
                    res = (PASS, k - s + 1, profit)
                    break
            if rules.max_days is not None and k - s + 1 >= rules.max_days:
                res = (TIMEOUT, k - s + 1, bal - a)
                break
        if res is None:
            if s + limit > n:
                res = (INCOMPLETE, n - s, bal - a)
            else:
                res = (TIMEOUT, limit, bal - a)
        outcomes.append(res)
    return _aggregate(outcomes)
