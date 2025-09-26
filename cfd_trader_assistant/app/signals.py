from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

import pandas as pd

from .rules import evaluate_trend, evaluate_triggers, evaluate_quality
from .utils import Signal, Instrument, floor_to_step, ceil_to_step


def _signal_id(symbol: str, side: str, ts: datetime, price: float) -> str:
    raw = f"{symbol}-{side}-{int(ts.timestamp())}-{price:.5f}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _cooldown_ok(symbol: str, side: str, last_sent: Dict[str, Any], minutes: int, now: datetime) -> bool:
    key = f"{symbol}:{side}"
    ts = last_sent.get(key)
    if not ts:
        return True
    return (now - ts) >= timedelta(minutes=minutes)


def generate_signals(
    htf_df: pd.DataFrame,
    ltf_df: pd.DataFrame,
    rules: Dict[str, Any],
    macro_guard: bool,
    symbol: str,
    instrument: Instrument,
    now: datetime,
    state: Dict[str, Any],
) -> List[Signal]:
    signals: List[Signal] = []
    trend_long, trend_short = evaluate_trend(htf_df, rules)
    if not (trend_long or trend_short):
        return signals

    triggers = evaluate_triggers(ltf_df, rules)
    quality_ok, quality_metrics = evaluate_quality(ltf_df, rules)
    if not quality_ok:
        return signals

    cooldown_min = int(rules.get("cooldowns", {}).get("per_symbol_minutes", 30))
    last_sent = state.setdefault("last_sent", {})

    # Entry price is last close
    entry = float(ltf_df["close"].iloc[-1])
    atr = float((ltf_df["high"].astype(float) - ltf_df["low"].astype(float)).rolling(14).mean().iloc[-1])
    stop_mult = float(rules.get("risk", {}).get("stop_atr_mult", 1.5))
    rr = float(rules.get("risk", {}).get("rr_ratio", 2.0))

    # LONG
    if trend_long and triggers["long"] and _cooldown_ok(symbol, "LONG", last_sent, cooldown_min, now) and not macro_guard:
        sl = entry - stop_mult * atr
        if instrument.min_step:
            sl = floor_to_step(sl, instrument.min_step)
        tp = entry + rr * (entry - sl)
        sig = Signal(
            id=_signal_id(symbol, "LONG", now, entry),
            time=now,
            side="LONG",
            symbol=symbol,
            entry=entry,
            sl=sl,
            tp=tp,
            rr=rr,
            why=f"Trend(HTF) OK; {build_why(triggers)}; ATR {100*quality_metrics['atr_pct']:.2f}%; Vol {quality_metrics['vol_mult']}×",
            metrics={"trigger": which_trigger(triggers), **quality_metrics},
        )
        last_sent[f"{symbol}:LONG"] = now
        signals.append(sig)

    # SHORT
    if trend_short and triggers["short"] and _cooldown_ok(symbol, "SHORT", last_sent, cooldown_min, now) and not macro_guard:
        sl = entry + stop_mult * atr
        if instrument.min_step:
            sl = ceil_to_step(sl, instrument.min_step)
        tp = entry - rr * (sl - entry)
        sig = Signal(
            id=_signal_id(symbol, "SHORT", now, entry),
            time=now,
            side="SHORT",
            symbol=symbol,
            entry=entry,
            sl=sl,
            tp=tp,
            rr=rr,
            why=f"Trend(HTF) OK; {build_why(triggers)}; ATR {100*quality_metrics['atr_pct']:.2f}%; Vol {quality_metrics['vol_mult']}×",
            metrics={"trigger": which_trigger(triggers), **quality_metrics},
        )
        last_sent[f"{symbol}:SHORT"] = now
        signals.append(sig)

    return signals


def which_trigger(triggers: Dict[str, bool]) -> str:
    if triggers.get("long"):
        return "pro-trend"
    if triggers.get("short"):
        return "pro-trend"
    return "-"


def build_why(triggers: Dict[str, bool]) -> str:
    parts = []
    if triggers.get("long"):
        parts.append("Trigger: LONG")
    if triggers.get("short"):
        parts.append("Trigger: SHORT")
    return "; ".join(parts) or "Trigger: -"


def should_time_stop(bars_since_entry: int, rules: Dict[str, Any]) -> bool:
    limit = int(rules.get("risk", {}).get("time_stop_bars", 12))
    return bars_since_entry > limit

