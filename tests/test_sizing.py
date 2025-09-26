from cfd_trader_assistant.app.sizing import size_position
from cfd_trader_assistant.app.utils import Instrument


def test_size_index():
    account = {"initial_equity": 10000, "risk_per_trade_pct": 0.01}
    inst = Instrument(symbol="NAS100", provider="YahooProvider", kind="index", point_value=1.0, min_step=1, ltf_interval="5m", htf_interval="1h")
    plan = size_position(100.0, 95.0, account, inst)
    assert plan.size_units > 0


def test_size_fx():
    account = {"initial_equity": 10000, "risk_per_trade_pct": 0.01}
    inst = Instrument(symbol="EURUSD", provider="YahooProvider", kind="fx", pip_value=10.0, min_step=0.0001, ltf_interval="5m", htf_interval="1h")
    plan = size_position(1.1000, 1.0950, account, inst)
    assert plan.size_units > 0
