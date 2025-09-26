from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

import pandas as pd

from .utils import get_logger, Instrument, load_yaml, now_utc
from .providers.yahoo import YahooProvider
from .providers.stooq import StooqProvider
from .providers.broker_ws_stub import BrokerWebsocketProvider
from .signals import generate_signals
from .sizing import size_position
from .alerts import send_alert
from .macro import parse_macro_config, is_in_no_trade_window


logger = get_logger("scheduler")


def _provider_for(inst: Dict[str, Any]):
    name = inst.get("provider", "YahooProvider")
    if name == "YahooProvider":
        return YahooProvider()
    if name == "StooqProvider":
        return StooqProvider()
    if name == "BrokerWebsocketProvider":
        return BrokerWebsocketProvider()
    return YahooProvider()


def _fetch_bars(inst_cfg: Dict[str, Any], limit: int = 400):
    provider = _provider_for(inst_cfg)
    ysym = inst_cfg.get("yahoo_symbol") or inst_cfg.get("symbol")
    ltf = provider.get_ohlcv(ysym, inst_cfg.get("ltf_interval", "5m"), limit)
    htf = provider.get_ohlcv(ysym, inst_cfg.get("htf_interval", "1h"), limit)
    return htf, ltf


def run_intraday_loop_once(instruments: Dict[str, Any], rules: Dict[str, Any], account: Dict[str, Any], macro_cfg: Dict[str, Any]) -> None:
    """One pass intraday scan across instruments and send alerts if any."""
    events = parse_macro_config(macro_cfg)
    macro_enabled = bool(rules.get("filters", {}).get("macro", {}).get("enabled", True))
    before = int(rules.get("filters", {}).get("macro", {}).get("no_trade_minutes_before", 30))
    after = int(rules.get("filters", {}).get("macro", {}).get("no_trade_minutes_after", 30))

    state: Dict[str, Any] = {}
    now = now_utc()
    for inst in instruments.get("instruments", []):
        symbol = inst["symbol"]
        htf_df, ltf_df = _fetch_bars(inst)
        htf_df = htf_df.tail(400)
        ltf_df = ltf_df.tail(400)
        instrument = Instrument(**inst)
        macro_guard = macro_enabled and is_in_no_trade_window(now, events, before, after)
        sigs = generate_signals(htf_df, ltf_df, rules, macro_guard, symbol, instrument, now, state)
        for s in sigs:
            plan = size_position(s.entry, s.sl, account, instrument)
            extra = {"trigger": s.metrics.get("trigger"), "atr_pct": s.metrics.get("atr_pct", 0), "vol_mult": s.metrics.get("vol_mult", 0), "risk_amount": plan.risk_amount, "risk_pct": plan.risk_pct, "size_units": plan.size_units}
            send_alert(s, extra, account)
            logger.info({"signal": s.model_dump(), "plan": plan.model_dump()})


def run_eod_once(instruments: Dict[str, Any], rules: Dict[str, Any], account: Dict[str, Any], macro_cfg: Dict[str, Any]) -> None:
    run_intraday_loop_once(instruments, rules, account, macro_cfg)

