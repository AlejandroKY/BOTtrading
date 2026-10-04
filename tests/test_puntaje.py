import pandas as pd
import pytest

from futbot.contracts import get_contract
from futbot.engine import BacktestResult, run_backtest
from futbot.portfolio import combine_first
from futbot.strategies import ORBPuntaje
from futbot.strategies.puntaje import puntaje
from helpers import Scripted, bars, flat_session

MNQ = get_contract("MNQ")


def test_puntaje_components():
    # compra: cierra sobre el máximo overnight (30), cuerpo 80 % (25), gap 0,6 ATR (20), abre sobre el máximo de ayer (15)
    s, parts = puntaje(1, 100.0, 110.0, 100.0, 108.0, 0.6, 105.0, 90.0, 99.0, 95.0, monday=True)
    assert parts == pytest.approx(dict(overnight=30, cuerpo=25, gap=20, fuera_ayer=15, lunes=10))
    assert s == 100
    s, parts = puntaje(1, 100.0, 110.0, 100.0, 104.0, 0.15, 105.0, 90.0, 101.0, 95.0, monday=False)
    assert parts["overnight"] == 0 and parts["gap"] == 0 and parts["fuera_ayer"] == 0
    assert s == 5  # cuerpo 40 % -> 25 x 0,2
    # venta: se miran el mínimo overnight y el mínimo de ayer
    s, parts = puntaje(-1, 100.0, 100.5, 90.0, 91.0, 0.375, 105.0, 92.0, 105.0, 100.5, monday=False)
    assert parts["overnight"] == 30 and parts["fuera_ayer"] == 15 and parts["gap"] == pytest.approx(10)


def _partial_day(day="2024-03-05"):
    """Entra a 100 con stop en 98 (2 puntos): sube a +2R (104) y vuelve a la entrada."""
    rows = [("09:30", 100.0, 100.25, 99.75, 100.0), ("09:31", 100.0, 104.5, 100.0, 104.0),
            ("09:32", 104.0, 104.25, 99.5, 99.75), ("09:33", 99.75, 100.0, 99.5, 99.75)]
    return bars(day, rows)


def test_engine_partial_then_breakeven():
    def enter(ctx):
        ctx.buy(2, stop=98.0, target_r=10.0, partial_r=2.0, partial_qty=1, be_after_partial=True)
    res = run_backtest(_partial_day(), MNQ, Scripted(actions={0: enter}), slippage_ticks=0, stop_slippage_ticks=0,
                       commission_rt=0.0)
    t = res.trades.iloc[0]
    assert t.qty == 2 and t.partial == pytest.approx(104.0)
    assert t.reason == "stop_be" and t.exit == pytest.approx(100.0)
    assert t.points == pytest.approx((4.0 + 0.0) / 2)  # 1 contrato +4 puntos, el otro en la entrada
    assert t.stop == pytest.approx(98.0)  # se registra el stop inicial (R correcto)
    assert t.pnl == pytest.approx(4.0 * MNQ.point_value)


def test_engine_without_partial_with_one_contract():
    def enter(ctx):
        ctx.buy(1, stop=98.0, target_r=10.0, partial_r=2.0, partial_qty=1, be_after_partial=True)
    t = run_backtest(_partial_day(), MNQ, Scripted(actions={0: enter}), slippage_ticks=0, stop_slippage_ticks=0,
                     commission_rt=0.0).trades.iloc[0]
    # con 1 contrato no hay parcial ni breakeven: el stop sigue en 98 y sale por tiempo
    assert pd.isna(t.partial) and t.reason == "session_end" and t.exit == pytest.approx(99.75)


def _history(n_days=15, price=4000.0):
    days = pd.bdate_range("2024-01-02", periods=n_days)
    frames = [flat_session(d.strftime("%Y-%m-%d"), "09:30", 390, price, step=0.0, rng=5.0) for d in days]
    return frames, (days[-1] + pd.offsets.BDay(1)).strftime("%Y-%m-%d")


def test_orb_puntaje_trades_high_score_and_skips_low():
    frames, day = _history()
    # gap de +25 (2,5 ATR), vela alcista fuerte que cierra sobre el máximo overnight y abre sobre el máximo de ayer
    first = bars(day, [("09:30", 4025.0, 4026.0, 4024.75, 4025.75), ("09:31", 4025.75, 4027.0, 4025.5, 4026.75),
                       ("09:32", 4026.75, 4028.0, 4026.5, 4027.75), ("09:33", 4027.75, 4029.0, 4027.5, 4028.75),
                       ("09:34", 4028.75, 4033.0, 4028.5, 4032.75)])
    data = pd.concat(frames + [first, flat_session(day, "09:35", 60, 4033.0, step=0.0, rng=0.25)])
    s = ORBPuntaje(min_risk_pts=1.0)
    t = run_backtest(data, MNQ, s, slippage_ticks=0, stop_slippage_ticks=0, commission_rt=0.0).trades
    assert len(t) == 1 and t.iloc[0].side == 1
    score = int(t.iloc[0].tag.split("=")[1])
    assert score >= 60 and s.scores[pd.Timestamp(day).date()][0] == score
    none = run_backtest(data, MNQ, ORBPuntaje(min_risk_pts=1.0, min_score=101), slippage_ticks=0,
                        stop_slippage_ticks=0, commission_rt=0.0).trades
    assert none.empty


def _res(dates, pnls):
    trades = pd.DataFrame(dict(entry_time=pd.to_datetime(dates).tz_localize("America/New_York"), pnl=pnls,
                               entry=1.0, stop=0.0, qty=1))
    daily = pd.DataFrame(dict(pnl=pnls, trades=1, min_eq=0.0, max_eq=0.0, max_dd=0.0),
                         index=pd.Index(pd.to_datetime(dates).date))
    return BacktestResult("x", {}, MNQ, trades, daily)


def test_combine_first_uses_backup_only_without_primary():
    nq = _res(["2024-03-04 09:35", "2024-03-06 09:35"], [100.0, -50.0])
    es = _res(["2024-03-04 09:35", "2024-03-05 09:35"], [999.0, 30.0])
    trades, daily = combine_first(nq, es)
    assert list(trades.market) == ["NQ", "ES", "NQ"]
    assert list(daily.pnl) == [100.0, 30.0, -50.0]


def test_escalones_and_sized_pass_rate():
    from futbot.propfirm import escalones, historical_pass_rate_sized
    assert escalones(2000) == 300 and escalones(1400) == 300 and escalones(1000) == 200 and escalones(500) == 100
    days = pd.bdate_range("2024-01-01", periods=40)
    # +1R todos los días con 10 puntos de stop en MNQ ($20 por contrato): $300 -> 15 contratos -> +$300 por día
    trades = pd.DataFrame(dict(date=days, R=1.0, mae_r=-0.5, risk_pts=10.0, point_value=2.0))
    h = historical_pass_rate_sized(trades, "lucid_flex_50k", escalones, days=days, horizon=20)
    assert h["pass_rate"] == 1.0 and h["median_days_pass"] == 10  # $3.000 en 10 días
    # pérdidas seguidas: el riesgo baja a $200 y a $100 y la cuenta resiste más que con $300 fijo
    losing = trades.assign(R=-1.0, mae_r=-1.0)
    fixed = historical_pass_rate_sized(losing, "lucid_flex_50k", lambda c, p: 300.0, days=days, horizon=20)
    steps = historical_pass_rate_sized(losing, "lucid_flex_50k", escalones, days=days, horizon=20)
    assert fixed["fail_rate"] == 1.0 and fixed["median_days_fail"] == 7  # $300 x 7 > $2.000
    assert steps["median_days_fail"] > fixed["median_days_fail"]


def test_skip_fomc_days():
    from futbot.calendario import fomc_dates
    assert pd.Timestamp("2026-10-28").date() in fomc_dates() and pd.Timestamp("2027-12-08").date() in fomc_dates()
    frames, _ = _history()
    day = "2024-01-31"  # anuncio de la Fed
    first = bars(day, [("09:30", 4025.0, 4026.0, 4024.75, 4025.75), ("09:31", 4025.75, 4027.0, 4025.5, 4026.75),
                       ("09:32", 4026.75, 4028.0, 4026.5, 4027.75), ("09:33", 4027.75, 4029.0, 4027.5, 4028.75),
                       ("09:34", 4028.75, 4033.0, 4028.5, 4032.75)])
    frames = [f for f in frames if f.index[0].date() < pd.Timestamp(day).date()]
    data = pd.concat(frames + [first, flat_session(day, "09:35", 60, 4033.0, step=0.0, rng=0.25)])
    kw = dict(slippage_ticks=0, stop_slippage_ticks=0, commission_rt=0.0)
    assert len(run_backtest(data, MNQ, ORBPuntaje(min_risk_pts=1.0), **kw).trades) == 1
    assert run_backtest(data, MNQ, ORBPuntaje(min_risk_pts=1.0, skip_fomc=True), **kw).trades.empty
