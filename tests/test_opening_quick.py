import numpy as np
import pandas as pd
import pytest

from futbot.contracts import get_contract
from futbot.data import back_adjust, daily_bars, load_csv
from futbot.engine import run_backtest
from futbot.recipes import RECIPES
from futbot.strategies import OpeningQuick, make_strategy
from helpers import bars, flat_session

MNQ = get_contract("MNQ")
RAPIDA = RECIPES["nq_orb5_rapida"].params


def _history(n_days=15, price=4000.0):
    """Sesiones planas con rango diario de 10 puntos: ATR(14) = 10."""
    days = pd.bdate_range("2024-01-02", periods=n_days)
    frames = [flat_session(d.strftime("%Y-%m-%d"), "09:30", 390, price, step=0.0, rng=5.0) for d in days]
    nxt = (days[-1] + pd.offsets.BDay(1)).strftime("%Y-%m-%d")
    return frames, nxt


def _bull_day(day, after=4007.0, minutes=60):
    """Gap de +5 (0,5 ATR) y 1ª vela de 5 min alcista: máximo 4007,50, mínimo 4004,75 (11 ticks)."""
    first = bars(day, [("09:30", 4005.00, 4006.00, 4004.75, 4005.75), ("09:31", 4005.75, 4006.50, 4005.50, 4006.25),
                       ("09:32", 4006.25, 4007.50, 4006.00, 4006.50), ("09:33", 4006.50, 4007.00, 4006.25, 4006.75),
                       ("09:34", 4006.75, 4007.25, 4006.50, 4007.00)])
    return pd.concat([first, flat_session(day, "09:35", minutes, after, step=0.0, rng=0.25)])


def _run(data, **kw):
    params = dict(RAPIDA, min_risk_pts=0.0)  # el día sintético tiene un stop de 1 punto
    params.update(kw)
    return run_backtest(data, MNQ, OpeningQuick(**params), slippage_ticks=0, stop_slippage_ticks=0, commission_rt=0.0)


def test_long_on_gap_day_stop_mid_rounded_away_and_time_exit():
    frames, day = _history()
    res = _run(pd.concat(frames + [_bull_day(day, minutes=120)]))
    assert len(res.trades) == 1
    t = res.trades.iloc[0]
    assert t.side == 1 and t.entry_time.strftime("%H:%M") == "09:35" and t.entry == pytest.approx(4007.0)
    assert t.stop == pytest.approx(4006.0)  # mitad 4006,125 -> se aleja de la entrada (hacia abajo)
    assert t.target == pytest.approx(4007.0 + 10 * 1.0)
    assert t.reason == "session_end" and t.exit_time.strftime("%H:%M") == "10:34"  # cierra la vela de las 10:35


def test_stop_hit_is_minus_one_r():
    frames, day = _history()
    drop = bars(day, [("09:38", 4006.75, 4007.00, 4005.75, 4006.00)])  # toca el stop dentro de la vela
    data = pd.concat(frames + [_bull_day(day, minutes=3), drop, flat_session(day, "09:39", 30, 4006.0)])
    t = _run(data).trades.iloc[0]
    assert t.reason == "stop" and t.exit == pytest.approx(4006.0)
    assert t.points / abs(t.entry - t.stop) == pytest.approx(-1.0)


def test_short_on_bearish_candle_rounds_stop_up():
    frames, day = _history()
    first = bars(day, [("09:30", 3995.00, 3995.25, 3994.00, 3994.25), ("09:31", 3994.25, 3994.50, 3993.50, 3993.75),
                       ("09:32", 3993.75, 3994.00, 3992.50, 3993.25), ("09:33", 3993.25, 3993.50, 3992.75, 3993.00),
                       ("09:34", 3993.00, 3993.25, 3992.75, 3993.00)])
    data = pd.concat(frames + [first, flat_session(day, "09:35", 60, 3993.0, step=0.0, rng=0.25)])
    t = _run(data).trades.iloc[0]
    assert t.side == -1
    assert t.stop == pytest.approx(3994.0)  # mitad 3993,875 -> hacia arriba (lejos de la entrada)


def test_no_trade_on_small_gap_or_close_behind_mid():
    frames, day = _history()
    small = _bull_day(day)
    small[["open", "high", "low", "close"]] -= 4.5  # gap de +0,5 punto = 0,05 ATR
    assert _run(pd.concat(frames + [small])).trades.empty
    weak = bars(day, [("09:30", 4005.00, 4010.00, 4004.75, 4009.00), ("09:31", 4009.00, 4009.25, 4005.25, 4005.50),
                      ("09:32", 4005.50, 4005.75, 4005.25, 4005.50), ("09:33", 4005.50, 4005.75, 4005.25, 4005.50),
                      ("09:34", 4005.50, 4005.75, 4005.25, 4005.50)])  # alcista, pero cierra bajo la mitad
    assert _run(pd.concat(frames + [weak, flat_session(day, "09:35", 60, 4005.5)])).trades.empty


def test_risk_based_size():
    frames, day = _history()
    data = pd.concat(frames + [_bull_day(day)])
    assert _run(data, risk_usd=20.0).trades.iloc[0].qty == 10  # riesgo 1 punto x $2 = $2 por contrato
    assert _run(data, risk_usd=1.0).trades.empty


def test_min_risk_skips_tight_stops():
    frames, day = _history()
    data = pd.concat(frames + [_bull_day(day)])  # stop a 1 punto de la entrada
    assert _run(data, min_risk_pts=0.0).trades.shape[0] == 1
    assert _run(data, min_risk_pts=1.25).trades.empty


def test_recipe_builds():
    assert RECIPES["nq_orb5_rapida"].strategy == "opening_quick"
    s = make_strategy("opening_quick", **RAPIDA)
    assert s.p["window_end"] == "10:35" and s.p["stop_mode"] == "mid" and s.p["min_gap_atr"] == 0.3


def _rolled(day_a="2024-03-11", day_b="2024-03-12"):
    """Contrato viejo a 4000; el nuevo cotiza 100 puntos más caro (roll a medianoche UTC)."""
    a = flat_session(day_a, "09:30", 390, 4000.0, step=0.0, rng=5.0).assign(instrument_id=1)
    b = flat_session(day_b, "09:30", 390, 4100.0, step=0.0, rng=5.0).assign(instrument_id=2)
    return pd.concat([a, b])


def test_back_adjust_removes_roll_jump():
    df = back_adjust(_rolled())
    assert "instrument_id" not in df.columns
    assert df["close"].iloc[0] == pytest.approx(4100.0)  # la historia vieja sube 100
    assert df["close"].iloc[-1] == pytest.approx(4100.0)  # el contrato vigente no se toca
    d = daily_bars(df)
    assert d["rth_open"].iloc[-1] - d["prev_rth_close"].iloc[-1] == pytest.approx(0.0)  # sin ajuste: gap falso de 100


def test_load_csv_adjusts_rolls_when_instrument_id_present(tmp_path):
    raw = _rolled().reset_index().rename(columns={"index": "time"})
    raw["time"] = raw["time"].dt.tz_convert("UTC")
    path = tmp_path / "NQ_1m_2024.parquet"
    raw.to_parquet(path, index=False)
    df = load_csv(str(path))
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert np.allclose(df["close"].to_numpy(), 4100.0)
