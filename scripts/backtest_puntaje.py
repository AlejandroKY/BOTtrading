"""Backtest del bot de TradingView (ORB 5 min con puntaje, NQ primero y ES de respaldo) y probabilidad
de aprobar cuentas de fondeo de 50K.

Uso:
    # datos de Databento (scripts/descargar_datos_databento.py), en UTC:
    python scripts/backtest_puntaje.py --nq "data/real/NQ_1m_*.parquet" --es "data/real/ES_1m_*.parquet"
    # datos de OANDA MT5 (data/oanda), hora del servidor:
    python scripts/backtest_puntaje.py --nq data/oanda/US100_M5.csv.gz --es data/oanda/US500_M5.csv.gz --tz mt5
    # sólo NQ, otro umbral y otro riesgo:
    python scripts/backtest_puntaje.py --nq "data/real/NQ_1m_*.parquet" --puntaje 60 --riesgo 150

Costos: NQ 1,2 puntos y ES 0,8 puntos por operación (comisión de micro + 2 ticks de deslizamiento).
Los precios de cada año se usan tal cual: con datos viejos (NQ a 8.000) el riesgo en puntos era chico y
los costos pesan más que hoy.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from futbot.contracts import get_contract  # noqa: E402
from futbot.data import load_csv  # noqa: E402
from futbot.engine import run_backtest  # noqa: E402
from futbot.portfolio import combine_first  # noqa: E402
from futbot.propfirm import historical_pass_rate  # noqa: E402
from futbot.recipes import RECIPES  # noqa: E402
from futbot.strategies import make_strategy  # noqa: E402

COST_PTS = {"nq_orb5_puntaje": 1.2, "es_orb5_puntaje": 0.8}
FIRMS = ("lucid_flex_50k", "topstep_50k", "tradeify_growth_50k", "mffu_pro_50k")


def run(path: str, tz: str, recipe: str, risk: float, score: int):
    r = RECIPES[recipe]
    c = get_contract(r.symbol)
    params = dict(r.params, risk_usd=risk, min_score=score)
    data = load_csv(path, tz=tz, use_cache=True)
    return run_backtest(data, c, make_strategy(r.strategy, **params), slippage_ticks=0, stop_slippage_ticks=0,
                        commission_rt=COST_PTS[recipe] * c.point_value)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nq", required=True, help="velas de NQ/MNQ de 1 o 5 minutos (acepta comodines)")
    ap.add_argument("--es", help="velas de ES/MES (opcional: respaldo cuando NQ no califica)")
    ap.add_argument("--tz", default="UTC", help="zona horaria de los archivos ('mt5' para data/oanda)")
    ap.add_argument("--riesgo", type=float, default=200.0, help="riesgo por operación en USD (por defecto 200)")
    ap.add_argument("--puntaje", type=int, default=40, help="puntaje mínimo (por defecto 40)")
    args = ap.parse_args()

    nq = run(args.nq, args.tz, "nq_orb5_puntaje", args.riesgo, args.puntaje)
    if args.es:
        es = run(args.es, args.tz, "es_orb5_puntaje", args.riesgo, args.puntaje)
        trades, daily = combine_first(nq, es)
    else:
        trades, daily = nq.trades.assign(market="NQ"), nq.daily
    if trades.empty:
        sys.exit("No hubo operaciones con esos datos.")
    t = trades.copy()
    pv = t["market"].map({"NQ": 2.0, "ES": 5.0})
    t["R"] = t["pnl"] / ((t["entry"] - t["stop"]).abs() * t["qty"] * pv)
    t["puntaje"] = t["tag"].str.split("=").str[1].astype(int)
    t["año"] = pd.to_datetime(t["entry_time"]).dt.year
    d = daily.copy()
    d.index = pd.to_datetime(d.index)
    full = pd.DataFrame(index=pd.bdate_range(d.index.min(), d.index.max())).join(d).fillna(0.0)
    weeks = len(full) / 5
    streak = worst = 0
    for v in t["pnl"]:
        streak = streak + 1 if v <= 0 else 0
        worst = max(worst, streak)
    eq = full["pnl"].cumsum()
    print(f"{len(t)} trades ({len(t) / weeks:.2f} por semana) · acierto {(t.pnl > 0).mean():.0%} · R medio {t.R.mean():+.2f} · "
          f"total ${t.pnl.sum():,.0f} · peor racha {worst} pérdidas · caída máxima ${(eq - eq.cummax()).min():,.0f}")
    print("\nPor año:")
    print(t.groupby("año").agg(trades=("pnl", "size"), acierto=("pnl", lambda x: f"{(x > 0).mean():.0%}"),
                               R_medio=("R", lambda x: f"{x.mean():+.2f}"), usd=("pnl", lambda x: f"{x.sum():,.0f}")).to_string())
    bins = pd.cut(t["puntaje"], [-1, 59, 79, 100], labels=["< 60", "60-79", "80+"])
    print("\nPor puntaje:")
    print(t.groupby(bins, observed=True).agg(trades=("pnl", "size"), acierto=("pnl", lambda x: f"{(x > 0).mean():.0%}"),
                                             R_medio=("R", lambda x: f"{x.mean():+.2f}")).to_string())
    print("\nPor mercado:", t["market"].value_counts().to_dict(), "· salidas:", t["reason"].value_counts().to_dict())
    print("\nCuentas de 50K (empezando la evaluación cada día del histórico, plazo de 1 año):")
    for f in FIRMS:
        h = historical_pass_rate(full, f)
        print(f"  {f:<20} aprueba {h['pass_rate']:.0%} · suspende {h['fail_rate']:.0%} · "
              f"no termina en 1 año {h['timeout_rate']:.0%} · mediana {h['median_days_pass']:.0f} sesiones")


if __name__ == "__main__":
    main()
