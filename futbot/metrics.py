"""Métricas de rendimiento a partir de los trades y del P&L diario de un backtest."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _max_drawdown(pnl: pd.Series) -> float:
    equity = np.concatenate([[0.0], pnl.cumsum().to_numpy()])
    return float((np.maximum.accumulate(equity) - equity).max())


def trade_stats(trades: pd.DataFrame) -> dict:
    n = len(trades)
    if n == 0:
        return dict(trades=0, win_rate=np.nan, profit_factor=np.nan, avg_trade=np.nan, avg_win=np.nan,
                    avg_loss=np.nan, payoff=np.nan, avg_r=np.nan, max_consec_losses=0)
    pnl = trades["pnl"].to_numpy()
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    gross_win, gross_loss = wins.sum(), -losses.sum()
    streak = best = 0
    for x in pnl:
        streak = streak + 1 if x <= 0 else 0
        best = max(best, streak)
    avg_win = wins.mean() if len(wins) else 0.0
    avg_loss = losses.mean() if len(losses) else 0.0
    return dict(
        trades=n,
        win_rate=len(wins) / n,
        profit_factor=(gross_win / gross_loss) if gross_loss > 0 else math.inf,
        avg_trade=pnl.mean(),
        avg_win=avg_win,
        avg_loss=avg_loss,
        payoff=(avg_win / -avg_loss) if avg_loss < 0 else math.inf,
        avg_r=float(np.nanmean(trades["r"])) if trades["r"].notna().any() else np.nan,
        max_consec_losses=best,
    )


def daily_stats(daily: pd.DataFrame) -> dict:
    if daily.empty:
        return dict(days=0, trading_days=0, net=0.0, net_per_year=0.0, sharpe=np.nan, max_dd=0.0,
                    pct_pos_days=np.nan, best_day=0.0, worst_day=0.0, best_day_share=np.nan, years=0.0)
    pnl = daily["pnl"]
    traded = daily[daily["trades"] > 0]
    first, last = pd.Timestamp(daily.index[0]), pd.Timestamp(daily.index[-1])
    years = max((last - first).days / 365.25, 1 / 365.25)
    net = float(pnl.sum())
    std = pnl.std()
    return dict(
        days=len(daily),
        trading_days=len(traded),
        net=net,
        net_per_year=net / years,
        sharpe=(pnl.mean() / std * math.sqrt(252)) if std > 0 else np.nan,
        max_dd=_max_drawdown(pnl),
        pct_pos_days=(traded["pnl"] > 0).mean() if len(traded) else np.nan,
        best_day=float(pnl.max()),
        worst_day=float(pnl.min()),
        best_day_share=(float(pnl.max()) / net) if net > 0 else np.nan,
        years=years,
    )


def summarize(result) -> dict:
    out = dict(strategy=result.strategy, symbol=result.contract.symbol)
    out.update(trade_stats(result.trades))
    out.update(daily_stats(result.daily))
    return out


def yearly_table(result) -> pd.DataFrame:
    daily = result.daily.copy()
    daily.index = pd.to_datetime(daily.index)
    trades = result.trades.copy()
    rows = []
    for year, d in daily.groupby(daily.index.year):
        t = trades[pd.to_datetime(trades["exit_time"]).dt.year == year] if len(trades) else trades
        ts = trade_stats(t)
        rows.append(dict(year=year, net=d["pnl"].sum(), trades=ts["trades"], win_rate=ts["win_rate"],
                         profit_factor=ts["profit_factor"], max_dd=_max_drawdown(d["pnl"])))
    return pd.DataFrame(rows).set_index("year")


def format_summary(s: dict) -> str:
    def f(x, pct=False, money=False, dec=2):
        if x is None or (isinstance(x, float) and (math.isnan(x))):
            return "n/a"
        if isinstance(x, float) and math.isinf(x):
            return "inf"
        if pct:
            return f"{100 * x:.1f}%"
        if money:
            return f"${x:,.0f}"
        return f"{x:.{dec}f}"

    lines = [
        f"Estrategia: {s['strategy']}  |  Contrato: {s['symbol']}  |  Años: {s['years']:.1f}",
        f"Trades: {s['trades']}  |  Win rate: {f(s['win_rate'], pct=True)}  |  Profit factor: {f(s['profit_factor'])}"
        f"  |  Payoff: {f(s['payoff'])}  |  R medio: {f(s['avg_r'])}",
        f"Neto: {f(s['net'], money=True)} ({f(s['net_per_year'], money=True)}/año)  |  Trade medio: {f(s['avg_trade'], money=True)}"
        f"  |  Sharpe (diario): {f(s['sharpe'])}",
        f"Max drawdown: {f(s['max_dd'], money=True)}  |  Mejor día: {f(s['best_day'], money=True)}"
        f"  |  Peor día: {f(s['worst_day'], money=True)}  |  % días positivos: {f(s['pct_pos_days'], pct=True)}",
        f"Pérdidas consecutivas máx.: {s['max_consec_losses']}  |  Días con trades: {s['trading_days']}/{s['days']}",
    ]
    return "\n".join(lines)


def r_multiples(trades: pd.DataFrame, point_value: float) -> pd.Series:
    """Resultado de cada trade en R (múltiplos del riesgo inicial), por contrato y neto de costos."""
    risk = (trades["entry"] - trades["stop"]).abs() * point_value * trades["qty"]
    return trades["pnl"] / risk


def r_summary(r: pd.Series) -> dict:
    r = r.dropna()
    if r.empty:
        return dict(trades=0, win_rate=np.nan, avg_win_r=np.nan, avg_loss_r=np.nan, exp_r=np.nan, pf_r=np.nan)
    w = r > 0
    losses = -r[~w].sum()
    return dict(trades=len(r), win_rate=w.mean(), avg_win_r=r[w].mean() if w.any() else np.nan,
                avg_loss_r=r[~w].mean() if (~w).any() else np.nan, exp_r=r.mean(),
                pf_r=(r[w].sum() / losses) if losses > 0 else math.inf)
