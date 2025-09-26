from __future__ import annotations

import os
from typing import Dict, Any

import requests

from .utils import Signal


def _format_alert(signal: Signal, extra: Dict[str, Any]) -> str:
    return (
        f"{signal.side} {signal.symbol} @ {signal.entry:.4f}\n"
        f"SL: {signal.sl:.4f}  TP: {signal.tp:.4f}   RR: {signal.rr:.2f}\n"
        f"Trend(HTF): ok  Trigger(LTF): {extra.get('trigger','?')}  "
        f"ATR%: {100*extra.get('atr_pct',0):.2f}%  Vol: {extra.get('vol_mult','-')}×\n"
        f"Risk: {extra.get('risk_amount','$0'):.2f} ({extra.get('risk_pct',0):.2f}% kapitału)  "
        f"Size: {extra.get('size_units',0):.3f} {signal.why}"
    )


def send_telegram(message: str, cfg: Dict[str, Any]) -> None:
    if not cfg.get("enabled", False):
        return
    token = cfg.get("bot_token") or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = cfg.get("chat_id") or os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
    except Exception:
        pass


def send_alert(signal: Signal, extra: Dict[str, Any], channel_cfg: Dict[str, Any]) -> None:
    msg = _format_alert(signal, extra)
    tg = channel_cfg.get("telegram", {})
    send_telegram(msg, tg)

