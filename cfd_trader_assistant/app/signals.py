from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import pandas as pd

from .indicators import compute_indicators
from .rules import RuleParams, trend_filter, trigger_ltf, quality_filter
from .utils import CACHE_DIR, json_logger, now_utc, read_json, write_json


logger = json_logger("signals")


@dataclass
class Signal:
    id: str
    time: datetime
    side: str
    symbol: str
    entry: float
    sl: float
    tp: float
    rr: float
    why: str
    metrics: Dict[str, float]


def _cooldown_ok(symbol: str, cooldown_minutes: int, now_ts: datetime) -> bool:
    path = CACHE_DIR / f"cooldown_{symbol}.json"
    last = read_json(path, default={})
    last_ts_iso = last.get("last_signal_ts")
    if last_ts_iso:
        last_ts = pd.to_datetime(last_ts_iso, utc=True).to_pydatetime()
        if now_ts - last_ts < timedelta(minutes=cooldown_minutes):
            return False
    return True


def _mark_signal(symbol: str, now_ts: datetime) -> None:
    path = CACHE_DIR / f"cooldown_{symbol}.json"
    write_json(path, {"last_signal_ts": now_ts.isoformat()})


def _apply_indicators(df: pd.DataFrame) -> pd.DataFrame:
    ind = compute_indicators(df)
    for k, v in ind.items():
        df[k] = v
    return df


def generate_signals(
    symbol: str,
    htf_df: pd.DataFrame,
    ltf_df: pd.DataFrame,
    rules_cfg: Dict,
    macro_guard: Optional[callable],
) -> List[Signal]:
    now_ts = now_utc()
    htf_df = _apply_indicators(htf_df.copy())
    ltf_df = _apply_indicators(ltf_df.copy())

    params = RuleParams(
        sma_long=rules_cfg["trend"]["sma_long"],
        sma_mid=rules_cfg["trend"]["sma_mid"],
        sma_fast=rules_cfg["trend"]["sma_fast"],
        donchian_period=rules_cfg["entry"]["donchian_period"],
        roc_lookback=rules_cfg["entry"]["roc_lookback"],
        roc_min_long=rules_cfg["entry"]["roc_min_long"],
        roc_max_short=rules_cfg["entry"]["roc_max_short"],
        vol_mult=rules_cfg["quality"]["vol_mult"],
        atr_min_pct=rules_cfg["quality"]["atr_min_pct"],
        atr_max_pct=rules_cfg["quality"]["atr_max_pct"],
    )

    side = trend_filter(htf_df, params)
    if side is None:
        return []

    trigger = trigger_ltf(ltf_df, side, params)
    if trigger is None:
        return []

    if not quality_filter(ltf_df, params):
        return []

    cooldown_minutes = int(rules_cfg.get("cooldowns", {}).get("per_symbol_minutes", 30))
    if not _cooldown_ok(symbol, cooldown_minutes, now_ts):
        return []

    if macro_guard and macro_guard(now_ts) is False:
        return []

    row = ltf_df.iloc[-1]
    atr = float(row["atr14"]) if pd.notna(row.get("atr14")) else 0.0
    entry = float(row["close"])  # market/close as proxy
    stop_mult = float(rules_cfg["risk"]["stop_atr_mult"])
    rr_ratio = float(rules_cfg["risk"]["rr_ratio"])
    sl = entry - stop_mult * atr if side == "LONG" else entry + stop_mult * atr
    sl_dist = abs(entry - sl)
    tp = entry + rr_ratio * sl_dist if side == "LONG" else entry - rr_ratio * sl_dist
    rr = rr_ratio

    atr_pct = atr / entry if entry else 0.0
    vol_mult = None
    if pd.notna(row.get("vol_ma20")) and row.get("vol_ma20"):
        vol_mult = float(row.get("volume", 0) / row.get("vol_ma20"))

    why = f"Trend(HTF) OK; {trigger}; ATR {atr_pct*100:.2f}%"
    if vol_mult is not None:
        why += f"; Vol {vol_mult:.2f}×"

    sig = Signal(
        id=f"{symbol}-{int(now_ts.timestamp())}",
        time=now_ts,
        side=side,
        symbol=symbol,
        entry=entry,
        sl=sl,
        tp=tp,
        rr=rr,
        why=why,
        metrics={"atr_pct": atr_pct, "vol_mult": vol_mult or 0.0},
    )

    _mark_signal(symbol, now_ts)
    logger.info({"signal": asdict(sig)})
    return [sig]

