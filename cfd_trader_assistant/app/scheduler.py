from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, List

import pandas as pd
import schedule

from .alerts import AlertMessage, send_telegram
from .macro import MacroCalendar
from .providers.base import DataProvider
from .providers.yahoo import YahooProvider
from .providers.stooq import StooqProvider
from .signals import generate_signals
from .sizing import size_position
from .utils import CONFIG_DIR, json_logger, load_account_config, read_yaml
from .indicators import compute_indicators


logger = json_logger("scheduler")


def _instantiate_provider(name: str) -> DataProvider:
    if name == "YahooProvider":
        return YahooProvider()
    if name == "StooqProvider":
        return StooqProvider()
    raise ValueError(f"Unknown provider {name}")


def _load_instruments() -> List[Dict]:
    cfg = read_yaml(CONFIG_DIR / "instruments.yaml")
    return cfg.get("instruments", [])


def _load_rules() -> Dict:
    return read_yaml(CONFIG_DIR / "rules.yaml")


def scan_once(mode: str) -> None:
    account = load_account_config()
    instruments = _load_instruments()
    rules = _load_rules()
    macro_cfg = rules.get("filters", {}).get("macro", {"enabled": False})
    cal = MacroCalendar() if macro_cfg.get("enabled", False) else None

    for inst in instruments:
        symbol = inst["symbol"]
        provider_name = inst.get("provider", "YahooProvider")
        provider = _instantiate_provider(provider_name)
        yahoo_symbol = inst.get("yahoo_symbol", symbol)
        stooq_symbol = inst.get("stooq_symbol", symbol)

        if mode == "eod":
            htf_interval = ltf_interval = "1d"
            limit = 400
        else:
            htf_interval = inst.get("htf_interval", "1h")
            ltf_interval = inst.get("ltf_interval", "5m")
            limit = 500

        def fetch(sym: str, interval: str, limit: int) -> pd.DataFrame:
            if isinstance(provider, YahooProvider):
                return provider.get_ohlcv(yahoo_symbol, interval, limit)
            if isinstance(provider, StooqProvider):
                return provider.get_ohlcv(stooq_symbol, interval, limit)
            return provider.get_ohlcv(sym, interval, limit)

        htf_df = fetch(symbol, htf_interval, 400)
        ltf_df = fetch(symbol, ltf_interval, 200)
        if htf_df.empty or ltf_df.empty:
            logger.error({"symbol": symbol, "error": "empty data"})
            continue

        def macro_guard(now_ts: datetime) -> bool:
            if not cal:
                return True
            before = int(macro_cfg.get("no_trade_minutes_before", 30))
            after = int(macro_cfg.get("no_trade_minutes_after", 30))
            return not cal.has_event_near(now_ts, before, after)

        sigs = generate_signals(symbol, htf_df, ltf_df, rules, macro_guard)
        for sig in sigs:
            plan = size_position(
                entry=sig.entry,
                sl=sig.sl,
                account_equity=account.initial_equity,
                risk_per_trade_pct=rules["risk"]["risk_per_trade_pct"],
                instrument=inst,
            )
            msg = AlertMessage(
                side=sig.side,
                symbol=sig.symbol,
                entry=sig.entry,
                sl=sig.sl,
                tp=sig.tp,
                rr=sig.rr,
                why=sig.why,
                atr_pct=sig.metrics.get("atr_pct"),
                vol_mult=sig.metrics.get("vol_mult"),
                risk_amount=plan.risk_amount,
                risk_pct=plan.risk_pct,
                size_units=plan.size_units,
            )
            send_telegram(msg.format_text(), account.telegram.bot_token, account.telegram.chat_id)


def run_scanner_once(mode: str) -> None:
    scan_once(mode)


def run_scheduler(mode: str) -> None:
    if mode == "eod":
        schedule.every().day.at("22:05").do(scan_once, mode=mode)
    else:
        schedule.every(5).minutes.do(scan_once, mode=mode)
    logger.info({"scheduler": mode, "status": "started"})
    while True:
        schedule.run_pending()
        schedule.idle_seconds()

