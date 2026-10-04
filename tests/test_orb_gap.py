import numpy as np
import pandas as pd
import pytest

from futbot.contracts import get_contract
from futbot.data import daily_bars, rma
from futbot.engine import run_backtest
from futbot.metrics import r_multiples, r_summary
from futbot.strategies import ORBZarattini
from helpers import flat_session

MNQ = get_contract("MNQ")


def test_rma_matches_wilder_definition():
    s = pd.Series([1.0, 2, 3, 4, 5, 6])
    out = rma(s, 3)
    assert np.isnan(out.iloc[1])
    assert out.iloc[2] == pytest.approx(2.0)  # arranca con la media simple de los 3 primeros
    assert out.iloc[3] == pytest.approx((2.0 * 2 + 4) / 3)
    assert out.iloc[5] == pytest.approx(((((2.0 * 2 + 4) / 3) * 2 + 5) / 3 * 2 + 6) / 3)


def _history(n_days=15, price=4000.0):
    days = pd.bdate_range("2024-01-02", periods=n_days)
    frames = [flat_session(d.strftime("%Y-%m-%d"), "09:30", 390, price, step=0.0, rng=5.0) for d in days]
    return frames, days


def test_daily_bars_gap_and_atr():
    frames, days = _history()
    test_day = (days[-1] + pd.offsets.BDay(1)).strftime("%Y-%m-%d")
    frames.append(flat_session(test_day, "09:30", 390, 4005.0, step=0.01, rng=0.5))
    d = daily_bars(pd.concat(frames))
    last = d.iloc[-1]
    assert last["prev_rth_close"] == pytest.approx(4000.0)
    assert last["atr_prev"] == pytest.approx(10.0)  # rango diario constante de 10 puntos
    assert last["gap_atr"] == pytest.approx(0.5)


def test_prev_rth_close_skips_sessions_without_cash_hours():
    frames, days = _history()
    holiday = (days[-1] + pd.offsets.BDay(1))
    # sesión sin horario cash (sólo overnight), como un feriado con mercado abierto parcialmente
    frames.append(flat_session(holiday.strftime("%Y-%m-%d"), "03:00", 30, 4000.0))
    nxt = (holiday + pd.offsets.BDay(1)).strftime("%Y-%m-%d")
    frames.append(flat_session(nxt, "09:30", 60, 4004.0))
    d = daily_bars(pd.concat(frames))
    assert d.iloc[-1]["prev_rth_close"] == pytest.approx(4000.0)


def _orb(**kw):
    params = dict(window_start="09:30", window_end="11:30", or_minutes=5, target_r=10.0, min_gap_atr=0.3)
    params.update(kw)
    return ORBZarattini(**params)


def test_gap_filter_trades_big_gaps_and_skips_small_ones():
    frames, days = _history()
    big = (days[-1] + pd.offsets.BDay(1))
    frames.append(flat_session(big.strftime("%Y-%m-%d"), "09:30", 390, 4005.0, step=0.01, rng=1.0))
    small = (big + pd.offsets.BDay(1)).strftime("%Y-%m-%d")
    last_close = frames[-1]["close"].iloc[-1]
    frames.append(flat_session(small, "09:30", 390, last_close + 1.0, step=0.01, rng=1.0))
    res = run_backtest(pd.concat(frames), MNQ, _orb())
    assert len(res.trades) == 1
    t = res.trades.iloc[0]
    assert t.entry_time.date() == big.date() and t.side == 1
    assert t.exit_time.strftime("%H:%M") == "11:29" and t.reason == "session_end"
    without_filter = run_backtest(pd.concat(frames), MNQ, _orb(min_gap_atr=0.0))
    assert len(without_filter.trades) > 1


def test_risk_based_sizing_and_skip():
    frames, days = _history()
    big = (days[-1] + pd.offsets.BDay(1)).strftime("%Y-%m-%d")
    frames.append(flat_session(big, "09:30", 390, 4005.0, step=0.01, rng=1.0))
    data = pd.concat(frames)
    sized = run_backtest(data, MNQ, _orb(risk_usd=20.0)).trades.iloc[0]
    risk_per_contract = abs(4005.0 + 4 * 0.01 + 0.01 - sized.stop) * MNQ.point_value  # cierre 09:34 - stop
    assert sized.qty == int(20.0 // risk_per_contract)
    assert run_backtest(data, MNQ, _orb(risk_usd=1.0)).trades.empty  # ni 1 contrato cabe


def test_r_multiples_and_summary():
    trades = pd.DataFrame(dict(entry=[100.0, 100.0, 100.0], stop=[99.0, 99.0, 98.0], qty=[1, 2, 1],
                               pnl=[4.0, -4.0, 10.0]))
    r = r_multiples(trades, point_value=2.0)
    assert list(r.round(3)) == [2.0, -1.0, 2.5]
    s = r_summary(r)
    assert s["win_rate"] == pytest.approx(2 / 3) and s["exp_r"] == pytest.approx(3.5 / 3)
    assert s["pf_r"] == pytest.approx(4.5)
