import pandas as pd
import pytest

from futbot.contracts import get_contract
from futbot.engine import run_backtest
from futbot.strategies import GapFill, LastHalfHour, NoiseArea, ORBZarattini, RangeBreakout, TimeOfDay
from helpers import bars, flat_session

MES = get_contract("MES")


def test_orb_zarattini_long_hits_10r_target():
    day = "2024-03-05"
    df = pd.concat([
        flat_session(day, "09:30", 5, 100.0, step=0.25),  # 1ª vela de 5 min alcista
        flat_session(day, "09:35", 60, 101.25, step=0.5),
    ])
    res = run_backtest(df, MES, ORBZarattini())
    t = res.trades.iloc[0]
    assert t.side == 1
    assert t.entry_time.strftime("%H:%M") == "09:35"
    assert t.stop == pytest.approx(99.75)  # mínimo de la vela de apertura
    assert t.reason == "target"
    assert t.r == pytest.approx(10.0)


def test_orb_zarattini_skips_doji_and_short_on_bearish():
    day = "2024-03-05"
    bear = pd.concat([flat_session(day, "09:30", 5, 100.0, step=-0.25), flat_session(day, "09:35", 30, 98.75)])
    res = run_backtest(bear, MES, ORBZarattini())
    assert res.trades.iloc[0].side == -1
    doji = flat_session(day, "09:30", 40, 100.0, step=0.0)
    assert run_backtest(doji, MES, ORBZarattini()).trades.empty


def test_gap_fill_short_on_gap_up_reaches_previous_close():
    d1 = bars("2024-03-04", [("09:30", 4000, 4001, 3999, 4000), ("15:59", 4000, 4001, 3999, 4000)])
    d2 = pd.concat([
        flat_session("2024-03-05", "09:30", 30, 4012.0, step=-0.5),  # gap +0,3 % que se va cerrando
        flat_session("2024-03-05", "10:00", 30, 3997.0, step=0.0),
    ])
    res = run_backtest(pd.concat([d1, d2]), MES, GapFill())
    t = res.trades.iloc[0]
    assert t.side == -1
    assert t.entry == pytest.approx(4011.75)  # open 4012 - 1 tick
    assert t.reason == "target" and t.exit == pytest.approx(4000.0)


def test_gap_fill_ignores_big_gaps():
    d1 = bars("2024-03-04", [("15:59", 4000, 4001, 3999, 4000)])
    d2 = flat_session("2024-03-05", "09:30", 30, 4060.0)  # +1,5 %: fuera de rango
    assert run_backtest(pd.concat([d1, d2]), MES, GapFill()).trades.empty


def test_last_half_hour_goes_with_the_day():
    d1 = bars("2024-03-04", [("15:59", 4000, 4001, 3999, 4000)])
    d2 = flat_session("2024-03-05", "09:30", 390, 4000.0, step=0.1)
    res = run_backtest(pd.concat([d1, d2]), MES, LastHalfHour())
    t = res.trades.iloc[0]
    assert t.side == 1
    assert t.entry_time.strftime("%H:%M") == "15:30"
    assert t.exit_time.strftime("%H:%M") == "15:59"


def test_noise_area_needs_history_then_follows_breakout():
    days = pd.bdate_range("2024-02-01", periods=15)
    quiet = [flat_session(d.strftime("%Y-%m-%d"), "09:30", 390, 4000.0, step=0.0) for d in days]
    trend_day = (days[-1] + pd.offsets.BDay(1)).strftime("%Y-%m-%d")
    trend = flat_session(trend_day, "09:30", 390, 4000.0, step=0.25)
    res = run_backtest(pd.concat(quiet + [trend]), MES, NoiseArea())
    assert len(res.trades) == 1
    t = res.trades.iloc[0]
    assert t.side == 1
    assert t.entry_time.strftime("%Y-%m-%d %H:%M") == f"{trend_day} 10:00"
    assert t.reason == "session_end"


def test_range_breakout_long_with_target():
    day = "2024-03-05"
    df = pd.concat([
        flat_session(day, "09:30", 30, 4000.0, step=0.0, rng=5.0),
        flat_session(day, "10:00", 120, 4000.0, step=1.0),
    ])
    strat = RangeBreakout(range_start="09:30", range_end="10:00", trade_end="12:00", target_r=1.5)
    res = run_backtest(df, MES, strat)
    assert len(res.trades) == 1
    t = res.trades.iloc[0]
    assert t.side == 1 and t.entry == pytest.approx(4005.5)
    assert t.stop == pytest.approx(3994.75)
    assert t.reason == "target"


def test_time_of_day_short_session():
    df = flat_session("2024-03-05", "08:20", 310, 2000.0, step=-0.1)
    res = run_backtest(df, get_contract("MGC"), TimeOfDay())
    t = res.trades.iloc[0]
    assert t.side == -1 and t.entry_time.strftime("%H:%M") == "08:20" and t.pnl > 0


def test_unknown_param_rejected():
    with pytest.raises(ValueError):
        GapFill(foo=1)
