import numpy as np
import pandas as pd
import pytest

from futbot.propfirm import (FAIL, INCOMPLETE, PASS, TIMEOUT, PropRules, bootstrap_pass_rate,
                             historical_pass_rate, run_evaluation, scan_sizes)


def days(rows):
    """rows: (pnl, min_eq, max_eq, max_dd[, trades])"""
    return np.array([(r + (1,))[:5] if len(r) == 4 else r for r in rows], dtype=float)


EOD = PropRules("t", drawdown="eod", trail_lock=0.0)


def test_eod_trailing_locks_at_start_balance_then_fails():
    d = days([(1000, 0, 1000, 0), (1000, 0, 1000, 0), (-1500, -1500, 0, 1500), (-600, -600, 0, 600)])
    status, n, _ = run_evaluation(d, PropRules("t", profit_target=10_000, trail_lock=0.0))
    assert (status, n) == (FAIL, 4)  # el umbral subió a 50.000 tras el día 2


def test_eod_trailing_ignores_intraday_peak():
    # sube +1.900 intradía pero cierra en 0: con EOD el umbral no se mueve
    d = days([(0, -100, 1900, 2000), (-1500, -1500, 0, 1500)])
    status, _, _ = run_evaluation(d, PropRules("t", profit_target=10_000))
    assert status == INCOMPLETE


def test_intraday_trailing_fails_on_giveback():
    d = days([(0, -100, 1900, 2000)])
    status, _, _ = run_evaluation(d, PropRules("t", drawdown="intraday", profit_target=10_000, trail_lock=None))
    assert status == FAIL


def test_consistency_rule_requires_more_profit():
    rules = PropRules("t", consistency=0.5)
    d = days([(2000, 0, 2000, 0), (1000, 0, 1000, 0), (1000, 0, 1000, 0)])
    status, n, profit = run_evaluation(d, rules)
    assert (status, n, profit) == (PASS, 3, 4000)  # con $3.000 el mejor día (2.000) era > 50 %


def test_soft_daily_loss_limit_caps_the_day():
    rules = PropRules("t", daily_loss_limit=1000, profit_target=10_000)
    d = days([(-1800, -1800, 0, 1800), (500, 0, 500, 0)])
    status, n, profit = run_evaluation(d, rules)
    assert status == INCOMPLETE and profit == -500


def test_hard_daily_loss_limit_fails():
    rules = PropRules("t", daily_loss_limit=1000, dll_fails=True)
    status, _, _ = run_evaluation(days([(-1200, -1200, 0, 1200)]), rules)
    assert status == FAIL


def test_timeout_and_scale():
    rules = PropRules("t", max_days=3)
    d = days([(500, 0, 500, 0)] * 5)
    assert run_evaluation(d, rules)[0] == TIMEOUT
    assert run_evaluation(d, rules, scale=2)[:2] == (PASS, 3)


def test_days_without_trades_do_not_count_as_trading_days():
    rules = PropRules("t", min_days=2)
    d = days([(3000, 0, 3000, 0), (0, 0, 0, 0, 0), (100, 0, 100, 0)])
    assert run_evaluation(d, rules)[:2] == (PASS, 3)


def test_pass_rate_helpers():
    idx = pd.date_range("2020-01-01", periods=300, freq="B").date
    rng = np.random.default_rng(1)
    pnl = rng.normal(60, 300, len(idx))
    daily = pd.DataFrame(dict(pnl=pnl, min_eq=np.minimum(pnl, 0) - 50, max_eq=np.maximum(pnl, 0) + 50,
                              max_dd=np.abs(pnl) + 100, trades=1), index=idx)
    h = historical_pass_rate(daily, "topstep_50k")
    b = bootstrap_pass_rate(daily, "topstep_50k", n_sims=200)
    for r in (h, b):
        assert 0 <= r["pass_rate"] <= 1 and r["pass_rate"] + r["fail_rate"] + r["timeout_rate"] == pytest.approx(1)
    table = scan_sizes(daily, "topstep_50k", [1, 2, 3])
    assert list(table.index) == [1, 2, 3]
