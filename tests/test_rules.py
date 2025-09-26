import pandas as pd

from cfd_trader_assistant.app.rules import evaluate_trend, evaluate_triggers, evaluate_quality


def make_df(n=250, start=100.0, step=0.1):
    close = [start + i * step for i in range(n)]
    high = [c + 0.2 for c in close]
    low = [c - 0.2 for c in close]
    vol = [1000 for _ in close]
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": vol})


def test_trend_long():
    df = make_df()
    rules = {"trend": {"sma_fast": 20, "sma_mid": 50, "sma_long": 200}}
    long_ok, short_ok = evaluate_trend(df, rules)
    assert long_ok and not short_ok


def test_triggers_long():
    df = make_df()
    rules = {"entry": {"donchian_period": 20, "roc_lookback": 10, "roc_min_long": 0.001, "roc_max_short": -0.001}}
    trig = evaluate_triggers(df, rules)
    assert trig["long"]


def test_quality():
    df = make_df()
    rules = {"quality": {"atr_min_pct": 0.0001, "atr_max_pct": 0.1, "vol_mult": 0.5}}
    ok, m = evaluate_quality(df, rules)
    assert ok and 0 < m["atr_pct"] < 0.1
