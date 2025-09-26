from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd


@dataclass
class RuleParams:
    sma_long: int
    sma_mid: int
    sma_fast: int
    donchian_period: int
    roc_lookback: int
    roc_min_long: float
    roc_max_short: float
    vol_mult: float
    atr_min_pct: float
    atr_max_pct: float


def trend_filter(htf: pd.DataFrame, params: RuleParams) -> Optional[str]:
    row = htf.iloc[-1]
    close = row["close"]
    sma200 = row.get("sma200")
    sma50 = row.get("sma50")
    sma20 = row.get("sma20")
    if pd.isna(sma200) or pd.isna(sma50) or pd.isna(sma20):
        return None
    if close > sma200 and sma20 > sma50:
        return "LONG"
    if close < sma200 and sma20 < sma50:
        return "SHORT"
    return None


def trigger_ltf(ltf: pd.DataFrame, side: str, params: RuleParams) -> Optional[str]:
    row = ltf.iloc[-1]
    if side == "LONG":
        if row["high"] > row.get("donchian_h", float("inf")):
            return "Breakout Donchian"
        if row.get("macd", 0) > row.get("macd_signal", 0) and row.get("macd", -1) > 0:
            return "MACD pro-trend"
        if row.get("roc10", 0) >= params.roc_min_long:
            return "ROC >= min"
    else:
        if row["low"] < row.get("donchian_l", float("-inf")):
            return "Breakdown Donchian"
        if row.get("macd", 0) < row.get("macd_signal", 0) and row.get("macd", 1) < 0:
            return "MACD pro-trend"
        if row.get("roc10", 0) <= params.roc_max_short:
            return "ROC <= max"
    return None


def quality_filter(ltf: pd.DataFrame, params: RuleParams) -> bool:
    row = ltf.iloc[-1]
    atr = row.get("atr14")
    close = row["close"]
    if pd.isna(atr) or close == 0:
        return False
    atr_pct = float(atr) / float(close)
    in_range = params.atr_min_pct <= atr_pct <= params.atr_max_pct
    if not in_range:
        return False
    vol = row.get("volume")
    vol_ma20 = row.get("vol_ma20")
    if pd.notna(vol) and pd.notna(vol_ma20) and vol_ma20 > 0:
        return float(vol) >= params.vol_mult * float(vol_ma20)
    return True

