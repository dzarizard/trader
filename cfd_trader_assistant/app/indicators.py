from __future__ import annotations

import pandas as pd
import numpy as np
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.volatility import AverageTrueRange, DonchianChannel
from ta.momentum import ROCIndicator


def compute_indicators(df: pd.DataFrame) -> dict[str, pd.Series]:
    out: dict[str, pd.Series] = {}
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"] if "volume" in df.columns else pd.Series(index=df.index, dtype=float)

    out["sma20"] = SMAIndicator(close, window=20).sma_indicator()
    out["sma50"] = SMAIndicator(close, window=50).sma_indicator()
    out["sma200"] = SMAIndicator(close, window=200).sma_indicator()

    macd = MACD(close)
    out["macd"] = macd.macd()
    out["macd_signal"] = macd.macd_signal()

    atr = AverageTrueRange(high=high, low=low, close=close, window=14)
    out["atr14"] = atr.average_true_range()

    don = DonchianChannel(high=high, low=low, close=close, window=20)
    out["don_high"] = don.donchian_channel_hband()
    out["don_low"] = don.donchian_channel_lband()

    roc = ROCIndicator(close, window=10)
    out["roc10"] = roc.roc() / 100.0

    out["vol"] = vol.astype(float)
    out["vol_ma20"] = vol.astype(float).rolling(20).mean()

    return out

