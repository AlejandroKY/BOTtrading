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


def add_second(trades: pd.DataFrame, daily: pd.DataFrame, second: BacktestResult, market: str = "NQ",
               name: str = "E2") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Suma los trades de una segunda estrategia (`second`, en `market`) a (trades, daily) de la primera.

    Un trade de la segunda se descarta si en ese momento hay una posición de la primera abierta en el mismo
    mercado y en sentido contrario (en una cuenta real se netearían). Columna `strategy`: E1 / `name`.
    """
    t1 = trades.assign(strategy=trades.get("strategy", "E1"))
    t2 = second.trades.assign(market=market, strategy=name)
    if not t1.empty and not t2.empty:
        same_mkt = t1[t1["market"] == market]
        clash = []
        for e_time, side in zip(t2["entry_time"], t2["side"]):
            open_ = same_mkt[(same_mkt["entry_time"] < e_time) & (same_mkt["exit_time"] > e_time)]
            clash.append(bool((open_["side"] != side).any()))
        t2 = t2[~pd.Series(clash, index=t2.index)]
    out = pd.concat([t1, t2]).sort_values("entry_time").reset_index(drop=True)
    d2 = t2.groupby(pd.to_datetime(t2["entry_time"]).dt.date)["pnl"].agg(["sum", "size"])
    days = daily.index.union(d2.index)
    d = daily.reindex(days).fillna(0.0)
    d["pnl"] = d["pnl"] + d2["sum"].reindex(days).fillna(0.0)
    d["trades"] = (d["trades"] + d2["size"].reindex(days).fillna(0)).astype(int)
    return out, d
