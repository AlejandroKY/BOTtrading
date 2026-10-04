"""Backtest del bot de TradingView y probabilidad de aprobar cuentas de fondeo de 50K.

Estrategia 1 (E1): ORB 5 min con puntaje, NQ primero y ES de respaldo.
Estrategia 2 (E2): Noise Area a las 10:00 a favor del gap, sólo NQ, a la mitad del riesgo de E1 y sólo con
colchón de $1.400 o más (se apaga con --sin-e2).

Uso:
    # datos de Databento (scripts/descargar_datos_databento.py), en UTC:
    python scripts/backtest_puntaje.py --nq "data/real/NQ_1m_*.parquet" --es "data/real/ES_1m_*.parquet"
    # datos de OANDA MT5 (data/oanda), hora del servidor:
    python scripts/backtest_puntaje.py --nq data/oanda/US100_M5.csv.gz --es data/oanda/US500_M5.csv.gz --tz mt5
    # sólo NQ, otro umbral y otro riesgo:
    python scripts/backtest_puntaje.py --nq "data/real/NQ_1m_*.parquet" --puntaje 60 --riesgo 150

Muestra también la probabilidad de aprobar con riesgo por escalones según el colchón ($300/$200/$75) y
la "salud" de cada estrategia: si sus últimos 30 trades rinden peor que el 95 % de las ventanas históricas.

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
from futbot.portfolio import add_second, combine_first  # noqa: E402
from futbot.propfirm import escalones, historical_pass_rate, historical_pass_rate_sized  # noqa: E402
from futbot.recipes import RECIPES  # noqa: E402
from futbot.strategies import make_strategy  # noqa: E402

COST_PTS = {"nq_orb5_puntaje": 1.2, "es_orb5_puntaje": 0.8, "nq_ruido10": 1.2}
E2_MULT, E2_MIN_CUSHION = 0.5, 1400.0  # E2: mitad del riesgo de E1 y sólo con colchón >= $1.400
FIRMS = ("lucid_flex_50k", "topstep_50k", "tradeify_growth_50k", "mffu_pro_50k")


def run(path: str, tz: str, recipe: str, risk: float | None, score: int | None = None):
    r = RECIPES[recipe]
    c = get_contract(r.symbol)
    params = dict(r.params, risk_usd=risk, qty=1)
    if score is not None:
        params["min_score"] = score
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
    ap.add_argument("--sin-e2", action="store_true", help="sólo la estrategia 1")
    args = ap.parse_args()

    nq = run(args.nq, args.tz, "nq_orb5_puntaje", args.riesgo, args.puntaje)
    if args.es:
        es = run(args.es, args.tz, "es_orb5_puntaje", args.riesgo, args.puntaje)
        trades, daily = combine_first(nq, es)
    else:
        trades, daily = nq.trades.assign(market="NQ"), nq.daily
    if trades.empty:
        sys.exit("No hubo operaciones con esos datos.")
    trades = trades.assign(strategy="E1")
    both = trades
    if not args.sin_e2:
        # todas las señales de E2 con 1 contrato: el resultado se mide en R y el tamaño lo decide la simulación
        e2 = run(args.nq, args.tz, "nq_ruido10", None)
        both, _ = add_second(trades, daily, e2, market="NQ", name="E2")
    t = both.copy()
    pv = t["market"].map({"NQ": 2.0, "ES": 5.0})
    t["R"] = t["pnl"] / ((t["entry"] - t["stop"]).abs() * t["qty"] * pv)
    t["año"] = pd.to_datetime(t["entry_time"]).dt.year
    # USD con riesgo fijo: E1 tal cual (riesgo --riesgo) y E2 a la mitad
    t["usd"] = t["pnl"].where(t["strategy"] == "E1", t["R"] * args.riesgo * E2_MULT)
    d = daily.copy()
    d.index = pd.to_datetime(d.index)
    full = pd.DataFrame(index=pd.bdate_range(d.index.min(), d.index.max())).join(d).fillna(0.0)
    usd_day = t.groupby(pd.to_datetime(t["entry_time"]).dt.tz_localize(None).dt.normalize())["usd"].sum()
    full_both = pd.DataFrame(dict(pnl=usd_day.reindex(full.index).fillna(0.0)))
    weeks = len(full) / 5
    groups = [("Estrategia 1 (ORB 5 min con puntaje)", t[t.strategy == "E1"], full)]
    if not args.sin_e2:
        groups += [("Estrategia 2 (Noise Area 10:00, mitad de riesgo)", t[t.strategy == "E2"], None),
                   ("Las dos juntas", t, full_both)]
    for title, g, dd in groups:
        if g.empty:
            print(f"\n== {title}: sin operaciones")
            continue
        streak = worst = 0
        for v in g["R"]:
            streak = streak + 1 if v <= 0 else 0
            worst = max(worst, streak)
        line = (f"\n== {title}: {len(g)} trades ({len(g) / weeks:.2f} por semana) · acierto {(g.R > 0).mean():.0%} · "
                f"R medio {g.R.mean():+.2f} · total ${g.usd.sum():,.0f} · peor racha {worst} pérdidas")
        if dd is not None:
            eq = dd["pnl"].cumsum()
            line += f" · caída máxima ${(eq - eq.cummax()).min():,.0f}"
        print(line)
        print(g.groupby("año").agg(trades=("R", "size"), acierto=("R", lambda x: f"{(x > 0).mean():.0%}"),
                                   R_medio=("R", lambda x: f"{x.mean():+.2f}"), usd=("usd", lambda x: f"{x.sum():,.0f}")).T.to_string())
    e1 = t[t.strategy == "E1"]
    sc = e1["tag"].str.split("=").str[1].astype(int)
    bins = pd.cut(sc, [-1, 59, 79, 100], labels=["< 60", "60-79", "80+"])
    print("\nE1 por puntaje:")
    print(e1.groupby(bins, observed=True).agg(trades=("pnl", "size"), acierto=("pnl", lambda x: f"{(x > 0).mean():.0%}"),
                                              R_medio=("R", lambda x: f"{x.mean():+.2f}")).to_string())
    print("E1 por mercado:", e1["market"].value_counts().to_dict(), "· salidas:", t["reason"].value_counts().to_dict())

    def show(label, fn):
        print(label)
        for f in FIRMS:
            h = fn(f)
            print(f"  {f:<20} aprueba {h['pass_rate']:.0%} · suspende {h['fail_rate']:.0%} · "
                  f"no termina en 1 año {h['timeout_rate']:.0%} · mediana {h['median_days_pass']:.0f} sesiones")

    print("\nCuentas de 50K (empezando cada día del histórico, plazo 1 año):")
    show(f"E1 con riesgo fijo de ${args.riesgo:,.0f}:", lambda f: historical_pass_rate(full, f))
    # riesgo por escalones según el colchón sobre el límite ($300 / $200 / $75), con contratos enteros
    sized = pd.DataFrame(dict(date=pd.to_datetime(t["entry_time"]).dt.tz_localize(None), R=t["R"],
                              mae_r=(t["mae"] / (t["entry"] - t["stop"]).abs()).clip(upper=0),
                              risk_pts=(t["entry"] - t["stop"]).abs(), point_value=pv,
                              mult=(t["strategy"] == "E2").map({True: E2_MULT, False: 1.0}),
                              min_cushion=(t["strategy"] == "E2").map({True: E2_MIN_CUSHION, False: 0.0})))
    s1 = sized[t["strategy"] == "E1"]
    show("E1 con riesgo por escalones ($300 con colchón >= $1.400, $200 desde $800, $75 por debajo):",
         lambda f: historical_pass_rate_sized(s1, f, escalones, days=full.index))
    if not args.sin_e2:
        fixed = sized.drop(columns="min_cushion")
        show(f"E1 + E2 con riesgo fijo (${args.riesgo:,.0f} y ${args.riesgo * E2_MULT:,.0f}, contratos enteros):",
             lambda f: historical_pass_rate_sized(fixed, f, lambda c, p: args.riesgo, days=full.index))
        show("E1 + E2 con escalones (E2 a la mitad y sólo con colchón >= $1.400):",
             lambda f: historical_pass_rate_sized(sized, f, escalones, days=full.index))
    print()
    for name, g in t.groupby("strategy"):
        salud(g["R"].to_numpy(), nombre=name)


def salud(r, ventana: int = 30, n_sims: int = 20000, seed: int = 0, nombre: str = "") -> None:
    """¿Los últimos trades se parecen al histórico? Compara el R medio de los últimos `ventana` trades con
    el de ventanas iguales sacadas al azar del histórico (si es peor que el 95 % de ellas, alerta)."""
    import numpy as np

    if len(r) < 2 * ventana:
        return
    rng = np.random.default_rng(seed)
    hist = r[:-ventana]
    sims = rng.choice(hist, size=(n_sims, ventana), replace=True).mean(axis=1)
    last = r[-ventana:].mean()
    pct = (sims <= last).mean()
    estado = "ALERTA: rinde peor que el 95 % de las ventanas históricas" if pct < 0.05 else \
        "atención: está en el 20 % más bajo" if pct < 0.20 else "normal"
    print(f"Salud {nombre or 'del sistema'}: últimos {ventana} trades R medio {last:+.2f} (histórico {hist.mean():+.2f}) -> "
          f"percentil {pct:.0%} · {estado}")


if __name__ == "__main__":
    main()
