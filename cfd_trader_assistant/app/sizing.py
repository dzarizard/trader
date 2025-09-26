from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class PositionPlan:
    size_units: float
    risk_amount: float
    risk_pct: float
    value_per_point: float


def size_position(
    entry: float,
    sl: float,
    account_equity: float,
    risk_per_trade_pct: float,
    instrument: Dict,
) -> PositionPlan:
    risk_amount = account_equity * risk_per_trade_pct
    sl_dist = abs(entry - sl)
    kind = instrument.get("kind", "index")
    value_per_point = float(instrument.get("point_value", instrument.get("pip_value", 1.0)))
    min_step = float(instrument.get("min_step", 1))
    points = max(sl_dist / min_step, 1e-9)
    cost_per_unit = points * value_per_point
    size_units = max(risk_amount / cost_per_unit, 0.0)
    return PositionPlan(
        size_units=size_units,
        risk_amount=risk_amount,
        risk_pct=risk_per_trade_pct * 100.0,
        value_per_point=value_per_point,
    )

