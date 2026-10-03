"""Genera docs/RESULTADOS_BACKTEST.md corriendo todas las recetas.

Uso: python -m futbot report [--out docs/RESULTADOS_BACKTEST.md] [--recipes nq_orb5 es_gap_fill ...]
"""

from __future__ import annotations

import datetime as dt
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .contracts import get_contract
from .data import FUTURESHARKS_MAP, load_futuresharks
from .engine import run_backtest
from .metrics import daily_stats, summarize
from .propfirm import PROP_FIRMS, best_size, historical_pass_rate, scan_sizes
from .recipes import RECIPES
from .strategies import make_strategy

MINI_OF = {"MES": "ES", "MNQ": "NQ", "MGC": "GC", "MCL": "CL", "M6E": "6E", "M2K": "RTY", "MYM": "YM"}
FIRMS = ["topstep_50k", "apex_50k_eod", "tradeify_growth_50k"]
MICRO_SIZES = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20]
MINI_SIZES = [1, 2, 3]
RECENT = dt.date(2015, 1, 1)


def _fmt(x, kind="num"):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    if isinstance(x, float) and math.isinf(x):
        return "∞"
    if kind == "pct":
        return f"{100 * x:.1f}%"
    if kind == "usd":
        return f"{x:,.0f}"
    return f"{x:.2f}"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def _recent_sharpe(daily: pd.DataFrame) -> float:
    d = daily[daily.index >= RECENT]
    return daily_stats(d)["sharpe"] if len(d) > 20 else float("nan")


def synthetic_baseline(rules: str, sigma: float = 500.0, sharpes=(0.0, 0.5, 1.0, 1.5, 2.0, 3.0),
                       n_days: int = 20_000, seed: int = 7) -> list[tuple[float, dict]]:
    """Probabilidad de aprobar de una estrategia "ideal" con P&L diario normal y Sharpe dado."""
    rng = np.random.default_rng(seed)
    out = []
    for sh in sharpes:
        mu = sh * sigma / math.sqrt(252)
        pnl = rng.normal(mu, sigma, n_days)
        swing = np.abs(rng.normal(0, 0.3 * sigma, n_days))
        daily = pd.DataFrame(dict(pnl=pnl, min_eq=np.minimum(pnl, 0) - swing, max_eq=np.maximum(pnl, 0) + swing,
                                  max_dd=np.abs(pnl) + 2 * swing, trades=1))
        out.append((sh, historical_pass_rate(daily, rules, step=10)))
    return out


def build_report(out: Path, recipes=None, futuresharks_dir=None, start=None, end=None) -> None:
    t0 = time.time()
    ids = recipes or list(RECIPES)
    cache: dict[str, pd.DataFrame] = {}
    rows_mini, rows_micro, rows_prop, yearly = [], [], [], {}

    for rid in ids:
        r = RECIPES[rid]
        inst = FUTURESHARKS_MAP[r.symbol]
        if inst not in cache:
            cache[inst] = load_futuresharks(r.symbol, root=futuresharks_dir)
        data = cache[inst]
        mini = MINI_OF.get(r.symbol, r.symbol)
        results = {}
        for sym in dict.fromkeys([mini, r.symbol]):
            res = run_backtest(data, get_contract(sym), make_strategy(r.strategy, **r.params), start=start, end=end)
            results[sym] = res
        gross = run_backtest(data, get_contract(mini), make_strategy(r.strategy, **r.params), slippage_ticks=0,
                             stop_slippage_ticks=0, commission_rt=0.0, start=start, end=end)
        g = summarize(gross)
        s = summarize(results[mini])
        rows_mini.append([
            f"`{rid}`", r.title, mini, str(s["trades"]), _fmt(s["win_rate"], "pct"), _fmt(s["profit_factor"]),
            _fmt(s["payoff"]), _fmt(s["avg_trade"], "usd"), _fmt(s["net_per_year"], "usd"), _fmt(s["max_dd"], "usd"),
            _fmt(s["worst_day"], "usd"), _fmt(s["sharpe"]), _fmt(_recent_sharpe(results[mini].daily)), _fmt(g["sharpe"]),
        ])
        if r.symbol != mini:
            m = summarize(results[r.symbol])
            rows_micro.append([
                f"`{rid}`", r.symbol, _fmt(m["win_rate"], "pct"), _fmt(m["profit_factor"]), _fmt(m["avg_trade"], "usd"),
                _fmt(m["net_per_year"], "usd"), _fmt(m["max_dd"], "usd"), _fmt(m["sharpe"]),
                _fmt(_recent_sharpe(results[r.symbol].daily)),
            ])
        yearly[rid] = (mini, results[mini].yearly())

        prop_cells = []
        candidates = [(mini, MINI_SIZES, 10)]
        if r.symbol != mini:
            candidates.append((r.symbol, MICRO_SIZES, 1))
        for firm in FIRMS:
            best = None
            for sym, sizes, mpc in candidates:
                tab = scan_sizes(results[sym].daily, firm, sizes, step=2, micros_per_contract=mpc)
                k = best_size(tab)
                if k is None:
                    continue
                row = tab.loc[k]
                if best is None or row.pass_rate > best[2].pass_rate:
                    best = (sym, k, row)
            if best is None:
                prop_cells.append("—")
            else:
                sym, k, row = best
                prop_cells.append(f"{_fmt(row.pass_rate, 'pct')} / {_fmt(row.fail_rate, 'pct')} "
                                  f"({k}×{sym}, {_fmt(row.median_days_pass, 'usd')} ses.)")
        rows_prop.append([f"`{rid}`"] + prop_cells)
        print(f"  {rid}: listo ({time.time() - t0:.0f}s)", flush=True)

    first = min(df.index[0] for df in cache.values()).date()
    last = max(df.index[-1] for df in cache.values()).date()
    lines = [
        "# Resultados de backtest (generado automáticamente)",
        "",
        f"> Generado con `python -m futbot report` el {dt.date.today().isoformat()}. "
        f"Datos: CFDs de Oanda de 1 minuto ({first} → {last}) del repositorio público "
        "[FutureSharks/financial-data](https://github.com/FutureSharks/financial-data), usados como "
        "aproximación de los futuros equivalentes (SPX500→ES, NAS100→NQ, XAU→GC, WTICO→CL, USB10Y→ZN, EUR/USD→6E). "
        "**No es dato de CME**: sirve para filtrar ideas, no para decidir con dinero real.",
        "",
        "**Costes simulados**: comisión ida+vuelta de $4,50 por mini y $1,40 por micro; órdenes market con "
        "0,5 tick de slippage y stops con 1 tick, más redondeo del precio al tick en contra (con precios medios "
        "equivale a cruzar el spread); los targets (limit) exigen 1 tick de penetración y, si en la misma barra "
        "se tocan stop y target, cuenta el stop. Todo intradía: sin posiciones overnight.",
        "",
        "**Parámetros**: los de los papers/fuentes de cada receta (`futbot/recipes.py`), sin optimizar sobre estos datos.",
        "",
        "Formato numérico: punto decimal y coma para los miles (como en las plataformas de trading).",
        "",
        "**Cómo leerlo**: la interpretación y las conclusiones están en "
        "[INVESTIGACION_ESTRATEGIAS.md](INVESTIGACION_ESTRATEGIAS.md). Notas: (1) el CFD del bono a 10 años "
        "(USB10Y) sólo tiene datos en el 50-60 % de los minutos de 2013-2019, así que `zn_last30` es poco fiable; "
        "(2) en Apex el \"mejor\" tamaño suele ser el máximo probado porque el plazo de 30 días obliga a arriesgar más.",
        "",
        "## 1. Resultados por estrategia (1 contrato mini)",
        "",
        "Sharpe calculado con el P&L diario (días sin trades = 0). *Sharpe 2015+* = sólo 2015-2020. "
        "*Sharpe bruto* = sin comisiones ni slippage, sólo con el redondeo al tick (mide la ventaja \"pura\" antes de costes).",
        "",
        _table(["Receta", "Estrategia", "Contrato", "Trades", "Win rate", "Profit factor", "Payoff", "Trade medio $",
                "Neto $/año", "Max DD $", "Peor día $", "Sharpe", "Sharpe 2015+", "Sharpe bruto"], rows_mini),
        "",
        "## 2. Las mismas estrategias con micros (1 contrato)",
        "",
        "Las comisiones de los micros pesan ~3 veces más por punto que las de los minis (MNQ: $1,40 = 0,7 puntos "
        "de NQ por trade). Por eso muchas ventajas pequeñas desaparecen con micros.",
        "",
        _table(["Receta", "Contrato", "Win rate", "Profit factor", "Trade medio $", "Neto $/año", "Max DD $",
                "Sharpe", "Sharpe 2015+"], rows_micro),
        "",
        "## 3. Probabilidad de aprobar una evaluación 50K",
        "",
        "Se simula una evaluación empezando en cada día del histórico (método *historical*, cada 2 días) con las "
        "reglas resumidas en `futbot/propfirm.py`, para varios tamaños (1-3 minis o 1-20 micros) y se muestra el "
        "mejor: **% aprueba / % suspende (tamaño, mediana de sesiones hasta aprobar)**. El resto hasta 100% son "
        "evaluaciones que no terminan en 1 año (o en 30 días en Apex).",
        "",
        _table(["Receta"] + [PROP_FIRMS[f].name for f in FIRMS], rows_prop),
        "",
        "### Referencia: ¿qué Sharpe hace falta para aprobar?",
        "",
        "Estrategias sintéticas con P&L diario normal bajo las reglas de Topstep 50K, con dos tamaños: "
        "volatilidad diaria de $500 (≈ 1 NQ intradía) y de $250 (≈ la mitad de contratos). Una estrategia sin "
        "ventaja (Sharpe 0) aprueba a veces por pura suerte: aprobar una evaluación NO demuestra que la "
        "estrategia funcione. Y con poco tamaño se suspende menos pero se tarda mucho más (y hay que seguir "
        "pagando la suscripción).",
        "",
    ]
    big = synthetic_baseline("topstep_50k", sigma=500.0)
    small = synthetic_baseline("topstep_50k", sigma=250.0)
    base_rows = []
    for (sh, a), (_, b) in zip(big, small):
        base_rows.append([f"{sh:.1f}", _fmt(a["pass_rate"], "pct"), _fmt(a["fail_rate"], "pct"),
                          _fmt(a["median_days_pass"], "usd"), _fmt(b["pass_rate"], "pct"), _fmt(b["fail_rate"], "pct"),
                          _fmt(b["timeout_rate"], "pct"), _fmt(b["median_days_pass"], "usd")])
    lines += [_table(["Sharpe anual", "σ $500: aprueba", "suspende", "mediana ses.", "σ $250: aprueba", "suspende",
                      "no termina en 1 año", "mediana ses."], base_rows), ""]
    lines += ["## 4. Resultados por año (1 contrato mini)", ""]
    for rid, (sym, table) in yearly.items():
        rows = [[str(y), _fmt(v.net, "usd"), str(int(v.trades)), _fmt(v.win_rate, "pct"), _fmt(v.profit_factor),
                 _fmt(v.max_dd, "usd")] for y, v in table.iterrows()]
        lines += [f"<details><summary><code>{rid}</code> — {RECIPES[rid].title} ({sym})</summary>", "",
                  _table(["Año", "Neto $", "Trades", "Win rate", "Profit factor", "Max DD $"], rows), "", "</details>", ""]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Informe escrito en {out} ({time.time() - t0:.0f}s)")
