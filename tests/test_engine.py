import pandas as pd
import pytest

from futbot.contracts import get_contract
from futbot.engine import run_backtest, sm
from helpers import Scripted, bars

MES = get_contract("MES")  # tick 0.25 = $1.25 -> $5/punto, comisión $1.40 ida y vuelta


def run(df, **params):
    kw = {k: params.pop(k) for k in list(params) if k in ("daily_loss_limit", "slippage_ticks", "stop_slippage_ticks")}
    return run_backtest(df, MES, Scripted(**params), **kw)


BASE = [
    ("09:30", 100.00, 100.50, 99.50, 100.00),
    ("09:31", 100.25, 101.00, 100.00, 100.75),
    ("09:32", 100.75, 101.50, 100.50, 101.00),
]


def test_session_minutes():
    assert sm("18:00") == 0
    assert sm("09:30") == 15 * 60 + 30
    assert sm("17:59") == 1439


def test_market_order_fills_next_open_and_closes_at_session_end():
    res = run(bars("2024-03-05", BASE), actions={0: lambda c: c.buy(1)})
    t = res.trades.iloc[0]
    assert t.entry == pytest.approx(100.50)  # open 100.25 + 1 tick de slippage
    assert t.exit == pytest.approx(100.75)  # close 101.00 - 1 tick
    assert t.reason == "session_end"
    assert t.pnl == pytest.approx(0.25 * 5 - 1.40)
    assert res.daily.iloc[0].pnl == pytest.approx(t.pnl)


def test_stop_has_priority_when_stop_and_target_in_same_bar():
    rows = BASE[:2] + [("09:32", 100.75, 102.00, 99.00, 101.00)]
    res = run(bars("2024-03-05", rows), actions={0: lambda c: c.buy(1, stop_offset=1.0, target_offset=1.0)})
    t = res.trades.iloc[0]
    assert t.reason == "stop"
    assert t.exit == pytest.approx(99.25)  # stop 99.50 - 1 tick


def test_target_needs_one_tick_of_penetration():
    touch = BASE[:2] + [("09:32", 100.75, 101.50, 100.50, 101.00), ("09:33", 101.00, 101.25, 100.75, 101.00)]
    res = run(bars("2024-03-05", touch), actions={0: lambda c: c.buy(1, stop_offset=1.0, target_offset=1.0)})
    assert res.trades.iloc[0].reason == "session_end"  # sólo tocó 101.50, no lo atravesó
    through = BASE[:2] + [("09:32", 100.75, 101.75, 100.50, 101.00)]
    res = run(bars("2024-03-05", through), actions={0: lambda c: c.buy(1, stop_offset=1.0, target_offset=1.0)})
    t = res.trades.iloc[0]
    assert t.reason == "target" and t.exit == pytest.approx(101.50)


def test_oco_stop_entries_cancel_each_other():
    rows = [
        ("09:30", 100.00, 100.50, 99.50, 100.00),
        ("09:31", 100.00, 101.25, 99.75, 101.00),
        ("09:32", 101.00, 101.25, 98.00, 98.50),
    ]
    act = {0: lambda c: (c.buy_stop(101.0, 1, oco="x"), c.sell_stop(99.0, 1, oco="x"))}
    res = run(bars("2024-03-05", rows), actions=act)
    assert len(res.trades) == 1
    t = res.trades.iloc[0]
    assert t.side == 1 and t.entry == pytest.approx(101.25)


def test_gap_through_stop_fills_at_open():
    rows = BASE[:2] + [("09:32", 99.00, 99.25, 98.50, 99.00)]
    res = run(bars("2024-03-05", rows), actions={0: lambda c: c.buy(1, stop_offset=1.0)})
    t = res.trades.iloc[0]
    assert t.reason == "stop" and t.exit == pytest.approx(98.75)


def test_stop_on_wrong_side_skips_trade():
    res = run(bars("2024-03-05", BASE), actions={0: lambda c: c.buy(1, stop=101.0)})
    assert res.trades.empty


def test_daily_loss_limit_liquidates_and_halts():
    rows = BASE[:2] + [("09:32", 100.75, 100.75, 98.00, 98.50), ("09:33", 98.50, 99.00, 98.00, 98.75),
                       ("09:34", 98.75, 99.00, 98.50, 98.75)]
    acts = {0: lambda c: c.buy(1), 3: lambda c: c.buy(1)}
    res = run(bars("2024-03-05", rows), actions=acts, daily_loss_limit=10.0)
    assert len(res.trades) == 1  # la segunda entrada se ignora: el bot está parado por hoy
    t = res.trades.iloc[0]
    assert t.reason == "daily_loss_limit"
    assert t.exit == pytest.approx(98.25)  # 100.50 - 10$/5$ por punto = 98.50, menos 1 tick
    assert res.daily.iloc[0].min_eq == pytest.approx(t.pnl)  # incluye slippage y comisión


def test_daily_loss_limit_respects_gaps():
    rows = BASE[:2] + [("09:32", 97.00, 97.50, 96.50, 97.25)]  # abre por debajo del nivel del límite
    res = run(bars("2024-03-05", rows), actions={0: lambda c: c.buy(1)}, daily_loss_limit=10.0)
    t = res.trades.iloc[0]
    assert t.reason == "daily_loss_limit"
    assert t.exit == pytest.approx(96.75)  # open 97.00 - 0,5 tick, redondeado en contra


def test_no_overnight_positions_and_window_filter():
    d1 = bars("2024-03-05", BASE + [("16:30", 101, 101, 101, 101)])  # fuera de ventana
    d2 = bars("2024-03-06", BASE)
    res = run(pd.concat([d1, d2]), actions={0: lambda c: c.buy(1)})
    assert len(res.trades) == 2
    assert list(res.trades.reason) == ["session_end", "session_end"]
    assert len(res.daily) == 2
    assert res.trades.exit_time.iloc[0].strftime("%H:%M") == "09:32"


def test_reversal_with_flatten_and_new_entry():
    rows = BASE + [("09:33", 101.00, 101.25, 100.25, 100.50), ("09:34", 100.50, 100.75, 100.00, 100.25)]
    acts = {0: lambda c: c.buy(1), 2: lambda c: (c.flatten("rev"), c.sell(1))}
    res = run(bars("2024-03-05", rows), actions=acts)
    assert list(res.trades.side) == [1, -1]
    assert res.trades.iloc[0].reason == "rev"
    assert res.trades.iloc[1].entry == pytest.approx(100.75)  # open 101.00 - 1 tick


def test_intraday_drawdown_tracking():
    rows = BASE[:2] + [("09:32", 100.75, 103.00, 100.50, 102.50), ("09:33", 102.50, 102.50, 99.50, 100.00)]
    res = run(bars("2024-03-05", rows), actions={0: lambda c: c.buy(1)})
    day = res.daily.iloc[0]
    assert day.max_eq == pytest.approx((103.00 - 100.50) * 5)
    assert day.max_dd >= (103.00 - 99.50) * 5 - 1e-9
