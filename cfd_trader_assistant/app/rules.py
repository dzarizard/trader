from __future__ import annotations

from typing import Dict, Any, Tuple

import pandas as pd


def evaluate_trend(htf_df: pd.DataFrame, rules: Dict[str, Any]) -> Tuple[bool, bool]:
    sma_fast = int(rules["trend"].get("sma_fast", 20))
    sma_mid = int(rules["trend"].get("sma_mid", 50))
    sma_long = int(rules["trend"].get("sma_long", 200))

    close = htf_df["close"].astype(float)
    sma20 = close.rolling(sma_fast).mean()
    sma50 = close.rolling(sma_mid).mean()
    sma200 = close.rolling(sma_long).mean()

    last = -1
    long_ok = close.iloc[last] > sma200.iloc[last] and sma20.iloc[last] > sma50.iloc[last]
    short_ok = close.iloc[last] < sma200.iloc[last] and sma20.iloc[last] < sma50.iloc[last]
    return bool(long_ok), bool(short_ok)


def evaluate_triggers(ltf_df: pd.DataFrame, rules: Dict[str, Any]) -> Dict[str, bool]:
    e = rules.get("entry", {})
    don_per = int(e.get("donchian_period", 20))
    roc_lb = int(e.get("roc_lookback", 10))
    roc_min_long = float(e.get("roc_min_long", 0.003))
    roc_max_short = float(e.get("roc_max_short", -0.003))

    ltf = ltf_df.copy()
    close = ltf["close"].astype(float)
    high = ltf["high"].astype(float)
    low = ltf["low"].astype(float)
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    signal = macd.ewm(span=9, adjust=False).mean()
    don_high = high.rolling(don_per).max()
    don_low = low.rolling(don_per).min()
    roc = close.pct_change(roc_lb)

    i = -1
    long_trig = (
        (high.iloc[i] > don_high.iloc[i])
        or (macd.iloc[i] > signal.iloc[i] and macd.iloc[i] > 0)
        or (roc.iloc[i] >= roc_min_long)
    )
    short_trig = (
        (low.iloc[i] < don_low.iloc[i])
        or (macd.iloc[i] < signal.iloc[i] and macd.iloc[i] < 0)
        or (roc.iloc[i] <= roc_max_short)
    )
    return {"long": bool(long_trig), "short": bool(short_trig)}


def evaluate_quality(ltf_df: pd.DataFrame, rules: Dict[str, Any]) -> Tuple[bool, Dict[str, float]]:
    q = rules.get("quality", {})
    atr_min = float(q.get("atr_min_pct", 0.003))
    atr_max = float(q.get("atr_max_pct", 0.03))
    vol_mult = float(q.get("vol_mult", 1.2))

    ltf = ltf_df.copy()
    close = ltf["close"].astype(float)
    high = ltf["high"].astype(float)
    low = ltf["low"].astype(float)
    tr = (high - low).abs().rolling(14).mean()
    atr_pct = (tr / close).iloc[-1]

    vol_ok = True
    if "volume" in ltf.columns and ltf["volume"].notna().any():
        vol_ma = ltf["volume"].rolling(20).mean()
        vol_ok = ltf["volume"].iloc[-1] >= vol_mult * (vol_ma.iloc[-1] or 0.0)

    atr_ok = (atr_pct >= atr_min) and (atr_pct <= atr_max)
    return bool(atr_ok and vol_ok), {"atr_pct": float(atr_pct), "vol_mult": float(vol_mult)}

