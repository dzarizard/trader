import pandas as pd

from cfd_trader_assistant.app.indicators import compute_indicators


def test_compute_indicators_basic():
    df = pd.DataFrame({
        "open": [1,2,3,4,5,6,7,8,9,10],
        "high": [1,2,3,4,5,6,7,8,9,10],
        "low": [1,2,3,4,5,6,7,8,9,10],
        "close": [1,2,3,4,5,6,7,8,9,10],
        "volume": [100]*10,
    })
    ind = compute_indicators(df)
    assert "sma20" in ind and "atr14" in ind and "don_high" in ind
