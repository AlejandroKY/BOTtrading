"""Combinar dos mercados con un solo trade por día (p.ej. NQ primero y ES de respaldo)."""

from __future__ import annotations

import pandas as pd

from .engine import BacktestResult


def combine_first(primary: BacktestResult, backup: BacktestResult, names=("NQ", "ES")) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Toma los trades de `primary` y, los días sin trade ahí, los de `backup`.

    Devuelve (trades, daily) con el mismo formato que BacktestResult (daily: pnl, trades, min_eq, max_eq,
    max_dd por fecha), listo para propfirm.historical_pass_rate. Funciona porque cada mercado opera
    como máximo una vez por día y el resultado de un mercado no depende del otro.
    """
    ta = primary.trades.assign(market=names[0])
    tb = backup.trades.assign(market=names[1])
    da, db = primary.daily, backup.daily
    a_days = set(pd.to_datetime(ta["entry_time"]).dt.date)
    tb = tb[~pd.to_datetime(tb["entry_time"]).dt.date.isin(a_days)]
    trades = pd.concat([ta, tb]).sort_values("entry_time").reset_index(drop=True)
    days = da.index.union(db.index)
    daily = da.reindex(days).copy()
    use_b = [d not in a_days and d in db.index and db.at[d, "trades"] > 0 for d in days]
    daily.loc[use_b] = db.reindex(days).loc[use_b]
    daily = daily.fillna(0.0)
    daily["trades"] = daily["trades"].astype(int)
    return trades, daily
