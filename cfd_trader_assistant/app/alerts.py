from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from .utils import json_logger

logger = json_logger("alerts")


@dataclass
class AlertMessage:
    side: str
    symbol: str
    entry: float
    sl: float
    tp: float
    rr: float
    why: str
    atr_pct: Optional[float] = None
    vol_mult: Optional[float] = None
    risk_amount: Optional[float] = None
    risk_pct: Optional[float] = None
    size_units: Optional[float] = None

    def format_text(self) -> str:
        parts = [
            f"{self.side} {self.symbol} @ {self.entry:.4f}",
            f"SL: {self.sl:.4f}  TP: {self.tp:.4f}   RR: {self.rr:.2f}",
        ]
        qual = []
        if self.atr_pct is not None:
            qual.append(f"ATR%: {self.atr_pct*100:.2f}%")
        if self.vol_mult is not None:
            qual.append(f"Vol: {self.vol_mult:.2f}×")
        parts.append(" ".join(qual))
        risk = []
        if self.risk_amount is not None and self.risk_pct is not None:
            risk.append(f"Risk: {self.risk_amount:.2f} ({self.risk_pct:.2f}% kapitału)")
        if self.size_units is not None:
            risk.append(f"Size: {self.size_units:.4f}")
        if risk:
            parts.append("  ".join(risk))
        parts.append(self.why)
        return "\n".join(parts)


def send_telegram(text: str, bot_token: Optional[str], chat_id: Optional[str]) -> None:
    if not bot_token or not chat_id:
        logger.info({"channel": "telegram", "status": "disabled", "msg": text})
        return
    try:
        import requests

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        if resp.status_code != 200:
            logger.error({"channel": "telegram", "status": resp.status_code, "body": resp.text})
        else:
            logger.info({"channel": "telegram", "status": "sent"})
    except Exception as exc:
        logger.error({"channel": "telegram", "error": str(exc)})

