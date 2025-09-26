from __future__ import annotations

import pandas as pd
import numpy as np
from ta.trend import SMAIndicator, MACD
from ta.volatility import AverageTrueRange, DonchianChannel


def compute_sma(series: pd.Series, window: int) -> pd.Series:
    return SMAIndicator(series, window=window, fillna=False).sma_indicator()


def compute_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    atr = AverageTrueRange(
        high=df["high"], low=df["low"], close=df["close"], window=window, fillna=False
    ).average_true_range()
    return atr


def compute_donchian(df: pd.DataFrame, window: int = 20) -> tuple[pd.Series, pd.Series]:
    dc = DonchianChannel(high=df["high"], low=df["low"], close=df["close"], window=window, fillna=False)
    return dc.donchian_channel_hband(), dc.donchian_channel_lband()


def compute_macd(series: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    macd = MACD(series, fillna=False)
    return macd.macd(), macd.macd_signal(), macd.macd_diff()


def compute_roc(series: pd.Series, lookback: int = 10) -> pd.Series:
    return series.pct_change(lookback)


def compute_volume_mean(volume: pd.Series, window: int = 20) -> pd.Series:
    return volume.rolling(window=window, min_periods=window).mean()


def compute_indicators(df: pd.DataFrame) -> dict[str, pd.Series]:
    out: dict[str, pd.Series] = {}
    out["sma20"] = compute_sma(df["close"], 20)
    out["sma50"] = compute_sma(df["close"], 50)
    out["sma200"] = compute_sma(df["close"], 200)
    out["atr14"] = compute_atr(df, 14)
    dc_h, dc_l = compute_donchian(df, 20)
    out["donchian_h"] = dc_h
    out["donchian_l"] = dc_l
    macd_line, macd_signal, macd_diff = compute_macd(df["close"])
    out["macd"] = macd_line
    out["macd_signal"] = macd_signal
    out["macd_hist"] = macd_diff
    out["roc10"] = compute_roc(df["close"], 10)
    if "volume" in df.columns:
        out["vol_ma20"] = compute_volume_mean(df["volume"], 20)
    return out

