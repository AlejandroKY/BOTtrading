"""Línea de comandos: python -m futbot <comando> ...

Ejemplos:
  python -m futbot list
  python -m futbot backtest --recipe nq_orb5
  python -m futbot backtest --strategy range_breakout --symbol MCL --csv data/raw/CL_1m.csv --tz UTC \\
         --param range_start=09:00 --param range_end=09:15 --param window_start=09:00 --param window_end=14:30
  python -m futbot prop --recipe es_gap_fill --firm topstep_50k
  python -m futbot stats --recipe nq_orb5_gap --symbol NQ      # números de referencia para el Pine Script
  python -m futbot report --out docs/RESULTADOS_BACKTEST.md
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

import pandas as pd

from .contracts import get_contract
from .data import load_csv, load_futuresharks
from .engine import run_backtest
from .metrics import format_summary, r_multiples, r_summary
from .propfirm import PROP_FIRMS, best_size, scan_sizes
from .recipes import RECIPES
from .strategies import STRATEGIES, make_strategy


def _parse_params(items: list[str]) -> dict:
    out = {}
    for it in items or []:
        k, _, v = it.partition("=")
        try:
            out[k] = ast.literal_eval(v)
        except (ValueError, SyntaxError):
            out[k] = v  # strings como 09:30
    return out


def _load(args, symbol: str) -> pd.DataFrame:
    if args.csv:
        return load_csv(args.csv, tz=args.tz, fmt=args.fmt, use_cache=True)
    return load_futuresharks(symbol, root=args.futuresharks_dir)


def _build(args):
    if args.recipe:
        r = RECIPES[args.recipe]
        params = {**r.params, **_parse_params(args.param)}
        return r.strategy, args.symbol or r.symbol, params
    if not (args.strategy and args.symbol):
        sys.exit("Indica --recipe o bien --strategy y --symbol")
    return args.strategy, args.symbol, _parse_params(args.param)


def _run(args):
    strat_name, symbol, params = _build(args)
    data = _load(args, symbol)
    strat = make_strategy(strat_name, **params)
    return run_backtest(data, get_contract(symbol), strat, slippage_ticks=args.slippage,
                        stop_slippage_ticks=args.stop_slippage, commission_rt=args.commission, daily_loss_limit=args.dll,
                        start=args.start, end=args.end)


def cmd_list(_args) -> None:
    print("Estrategias:")
    for name, cls in STRATEGIES.items():
        print(f"  {name:16s} {cls.description}")
    print("\nRecetas (estrategia + mercado):")
    for rid, r in RECIPES.items():
        print(f"  {rid:14s} {r.title}  [{r.source}]")
    print("\nProp firms (presets 50K):")
    for name, r in PROP_FIRMS.items():
        print(f"  {name:22s} {r.notes}")


def cmd_backtest(args) -> None:
    res = _run(args)
    print(format_summary(res.summary()))
    print("\nPor año:")
    print(res.yearly().to_string(float_format=lambda x: f"{x:,.2f}"))
    if args.save:
        out = Path(args.save)
        out.mkdir(parents=True, exist_ok=True)
        tag = args.recipe or f"{res.strategy}_{res.contract.symbol}"
        res.trades.to_csv(out / f"{tag}_trades.csv", index=False)
        res.daily.to_csv(out / f"{tag}_daily.csv")
        print(f"\nGuardado en {out}/")


def cmd_prop(args) -> None:
    res = _run(args)
    print(format_summary(res.summary()))
    sizes = range(args.min_size, args.max_size + 1)
    mpc = 1 if res.contract.symbol.startswith("M") else 10
    firms = args.firm or ["topstep_50k"]
    for firm in firms:
        table = scan_sizes(res.daily, firm, sizes, method=args.method, micros_per_contract=mpc)
        print(f"\n== {firm} ({args.method}) — {PROP_FIRMS[firm].notes}")
        print(table.to_string(float_format=lambda x: f"{x:.3f}"))
        b = best_size(table)
        if b is not None:
            row = table.loc[b]
            print(f"Mejor tamaño: {b} x {res.contract.symbol} -> aprueba {row.pass_rate:.1%}, "
                  f"suspende {row.fail_rate:.1%}, mediana {row.median_days_pass:.0f} sesiones hasta aprobar")


def cmd_stats(args) -> None:
    """Estadísticas en R (lo que muestra el Pine Script), netas y brutas, por dirección y por año."""
    strat_name, symbol, params = _build(args)
    data = _load(args, symbol)
    c = get_contract(symbol).with_costs(args.commission)
    runs = {
        "neto": run_backtest(data, c, make_strategy(strat_name, **params), slippage_ticks=args.slippage,
                             stop_slippage_ticks=args.stop_slippage, start=args.start, end=args.end),
        "bruto": run_backtest(data, c.with_costs(0.0), make_strategy(strat_name, **params), slippage_ticks=0,
                              stop_slippage_ticks=0, start=args.start, end=args.end),
    }
    t = runs["neto"].trades
    if t.empty or t["stop"].isna().all():
        sys.exit("Sin trades con stop: no hay R que medir.")
    years = max(daily_years(runs["neto"].daily), 1e-9)
    rows = []
    for kind, res in runs.items():
        tr = res.trades
        r = r_multiples(tr, c.point_value)
        for lab, mask in (("ambas", tr["side"] != 0), ("compras", tr["side"] > 0), ("ventas", tr["side"] < 0)):
            rows.append({"costos": kind, "dirección": lab, **r_summary(r[mask])})
    table = pd.DataFrame(rows)
    print(f"{strat_name} en {symbol}: {len(t)} trades en {years:.1f} años ({len(t) / years:.0f} por año)")
    print(table.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    r_net = r_multiples(t, c.point_value)
    by_year = pd.DataFrame({"año": pd.to_datetime(t["entry_time"]).dt.year, "r": r_net})
    print("\nPor año (neto):")
    print(by_year.groupby("año")["r"].agg(trades="size", acierto=lambda x: (x > 0).mean(), r_medio="mean")
          .to_string(float_format=lambda x: f"{x:.3f}"))
    risk_pts = (t["entry"] - t["stop"]).abs()
    cost_pts = c.commission_rt / c.point_value + (args.slippage + args.stop_slippage) * c.tick_size
    gross = r_summary(r_multiples(runs["bruto"].trades, c.point_value))
    print(f"\nRiesgo mediano por trade: {risk_pts.median():.2f} puntos; costo ≈ {cost_pts:.2f} puntos "
          f"= {cost_pts / risk_pts.median():.3f} R por trade con ese riesgo.")
    net = r_summary(r_net)
    print(f"Compáralo con el panel del Pine ('En este gráfico' / 'Backtest 2019-26'): acierto "
          f"{100 * net['win_rate']:.0f} %, R medio neto {net['exp_r']:+.2f} (bruto {gross['exp_r']:+.2f}).")


def daily_years(daily: pd.DataFrame) -> float:
    if daily.empty:
        return 0.0
    first, last = pd.Timestamp(daily.index[0]), pd.Timestamp(daily.index[-1])
    return (last - first).days / 365.25


def cmd_report(args) -> None:
    from .report import build_report

    build_report(Path(args.out), recipes=args.recipes, futuresharks_dir=args.futuresharks_dir,
                 start=args.start, end=args.end)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="futbot", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="lista estrategias, recetas y prop firms").set_defaults(fn=cmd_list)

    def common(p):
        p.add_argument("--recipe", choices=sorted(RECIPES))
        p.add_argument("--strategy", choices=sorted(STRATEGIES))
        p.add_argument("--symbol", help="contrato: ES, MES, NQ, MNQ, GC, MGC, CL, MCL, ZN, 6E, M6E...")
        p.add_argument("--param", action="append", help="parámetro de la estrategia, p.ej. target_r=2")
        p.add_argument("--csv", help="CSV propio de 1 minuto (acepta comodines)")
        p.add_argument("--tz", default="UTC", help="zona horaria del CSV si viene sin zona (por defecto UTC)")
        p.add_argument("--fmt", default="auto", choices=["auto", "ninjatrader"])
        p.add_argument("--futuresharks-dir", help="ruta al clon de FutureSharks/financial-data")
        p.add_argument("--start")
        p.add_argument("--end")
        p.add_argument("--slippage", type=float, default=0.5, help="ticks de slippage por lado en órdenes market")
        p.add_argument("--stop-slippage", type=float, default=1.0, help="ticks de slippage por lado en órdenes stop")
        p.add_argument("--commission", type=float, help="comisión ida+vuelta por contrato (USD)")
        p.add_argument("--dll", type=float, help="límite de pérdida diaria del bot (USD)")

    b = sub.add_parser("backtest", help="backtest de una receta o estrategia")
    common(b)
    b.add_argument("--save", help="carpeta donde guardar trades y P&L diario (CSV)")
    b.set_defaults(fn=cmd_backtest)

    p = sub.add_parser("prop", help="probabilidad de aprobar evaluaciones de prop firms por tamaño")
    common(p)
    p.add_argument("--firm", action="append", choices=sorted(PROP_FIRMS))
    p.add_argument("--method", default="historical", choices=["historical", "bootstrap"])
    p.add_argument("--min-size", type=int, default=1)
    p.add_argument("--max-size", type=int, default=20)
    p.set_defaults(fn=cmd_prop)

    st = sub.add_parser("stats", help="estadísticas en R (para el Pine Script), netas y brutas")
    common(st)
    st.set_defaults(fn=cmd_stats)

    r = sub.add_parser("report", help="corre todas las recetas y escribe un informe Markdown")
    r.add_argument("--out", default="docs/RESULTADOS_BACKTEST.md")
    r.add_argument("--recipes", nargs="*", help="subconjunto de recetas (por defecto todas)")
    r.add_argument("--futuresharks-dir")
    r.add_argument("--start")
    r.add_argument("--end")
    r.set_defaults(fn=cmd_report)

    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
