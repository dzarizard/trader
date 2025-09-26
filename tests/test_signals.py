from datetime import datetime, timezone

import pandas as pd

from cfd_trader_assistant.app.signals import generate_signals
from cfd_trader_assistant.app.utils import Instrument


def make_df(n=250, start=100.0, step=0.1):
    close = [start + i * step for i in range(n)]
    high = [c + 0.2 for c in close]
    low = [c - 0.2 for c in close]
    vol = [1000 for _ in close]
    return pd.DataFrame({"ts": pd.date_range("2024-01-01", periods=n, tz="UTC"), "open": close, "high": high, "low": low, "close": close, "volume": vol})


def test_generate_signal_long():
    htf = make_df()
    ltf = make_df()
    rules = {
        "trend": {"sma_fast": 20, "sma_mid": 50, "sma_long": 200},
        "entry": {"donchian_period": 20, "roc_lookback": 10, "roc_min_long": 0.001, "roc_max_short": -0.001},
        "quality": {"atr_min_pct": 0.0001, "atr_max_pct": 0.5, "vol_mult": 0.5},
        "risk": {"stop_atr_mult": 1.0, "rr_ratio": 2.0},
        "cooldowns": {"per_symbol_minutes": 30},
        "filters": {"macro": {"enabled": False}},
    }
    inst = Instrument(symbol="NAS100", provider="YahooProvider", kind="index", point_value=1.0, min_step=1, ltf_interval="5m", htf_interval="1h")
    now = datetime.now(timezone.utc)
    state = {}
    sigs = generate_signals(htf, ltf, rules, macro_guard=False, symbol="NAS100", instrument=inst, now=now, state=state)
    assert len(sigs) >= 1
