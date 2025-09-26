from __future__ import annotations

from typing import Dict, Any

from .utils import PositionPlan, Instrument


def size_position(signal_price_entry: float, sl_price: float, account: Dict[str, Any], instrument: Instrument) -> PositionPlan:
    equity = float(account.get("initial_equity", 10000))
    risk_pct = float(account.get("risk", {}).get("risk_per_trade_pct", account.get("risk_per_trade_pct", 0.008)))
    risk_amount = equity * risk_pct

    distance = abs(signal_price_entry - sl_price)

    if instrument.kind == "fx":
        value_per_point = float(instrument.pip_value or 10.0) / 0.0001
    else:
        value_per_point = float(instrument.point_value or 1.0)

    size_units = 0.0
    if distance > 0 and value_per_point > 0:
        size_units = risk_amount / (distance * value_per_point)

    return PositionPlan(
        size_units=float(size_units),
        risk_amount=float(risk_amount),
        risk_pct=float(100.0 * risk_pct),
        value_per_point=float(value_per_point),
    )

