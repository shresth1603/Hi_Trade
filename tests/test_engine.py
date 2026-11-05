import numpy as np
import pandas as pd
import pytest

from hitrade.engine import DataError, add_indicators, demo_history, load_symbols, size_position


def test_symbol_path_is_independent_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    symbols = load_symbols()
    assert "RELIANCE.NS" in symbols
    assert symbols == sorted(set(symbols))


def test_position_is_limited_by_cash_and_risk():
    cash_limited = size_position(1000, 1, 25000, 2)
    assert cash_limited.quantity == 25
    assert cash_limited.cost == 25000
    risk_limited = size_position(100, 10, 25000, 2)
    assert risk_limited.quantity == 25
    assert risk_limited.planned_risk == 500
    assert size_position(30000, 10, 25000, 2).quantity == 0


@pytest.mark.parametrize("args", [
    (100, 0, 25000, 2), (100, float("nan"), 25000, 2),
    (100, float("inf"), 25000, 2), (100, 60, 25000, 2),
    (100, 10, -1, 2), (100, 10, 25000, 0), (100, 10, 25000, 101),
])
def test_invalid_sizing_inputs(args):
    with pytest.raises(ValueError):
        size_position(*args)


def test_sizing_invariants_across_many_inputs():
    rng = np.random.default_rng(42)
    for _ in range(500):
        price = rng.uniform(10, 10000)
        atr = rng.uniform(0.01, price / 3)
        capital = rng.uniform(1, 1e6)
        risk = rng.uniform(0.1, 5)
        position = size_position(price, atr, capital, risk)
        assert position.cost <= capital + 1e-8
        assert position.planned_risk <= position.risk_budget + 1e-8
        assert position.quantity >= 0


def test_indicator_math_and_no_future_leakage():
    raw = pd.DataFrame({"Open": 100., "High": 102., "Low": 98., "Close": 100.},
                       index=pd.bdate_range("2025-01-01", periods=40))
    frame = add_indicators(raw)
    assert frame.ATR.iloc[-1] == 4
    assert frame.EMA_9.iloc[-1] == 100
    changed = raw.copy()
    changed.iloc[-1] = [150, 152, 148, 150]
    after = add_indicators(changed)
    pd.testing.assert_frame_equal(frame.iloc[:-1], after.iloc[:-1])


@pytest.mark.parametrize("reverse", [False, True])
def test_provider_multiindex_layouts(reverse):
    raw = demo_history("TEST.NS")
    provider = pd.concat({"TEST.NS": raw}, axis=1)
    if reverse:
        provider = provider.swaplevel(axis=1)
    pd.testing.assert_frame_equal(add_indicators(provider, "TEST.NS"), add_indicators(raw))


@pytest.mark.parametrize("kind", ["empty", "short", "missing", "nan", "infinite", "bad_candle"])
def test_bad_market_data_is_rejected(kind):
    raw = demo_history("TEST.NS")
    if kind == "empty":
        raw = raw.iloc[:0]
    elif kind == "short":
        raw = raw.iloc[:10]
    elif kind == "missing":
        raw = raw.drop(columns="High")
    elif kind == "nan":
        raw.iloc[-1, 0] = np.nan
    elif kind == "infinite":
        raw.iloc[-1, 0] = np.inf
    else:
        raw.iloc[-1, raw.columns.get_loc("Low")] = 1e9
    with pytest.raises(DataError):
        add_indicators(raw)
