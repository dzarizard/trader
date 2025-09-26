from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import orjson
import pandas as pd
import yaml
from pydantic import BaseModel, Field


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ensure_dirs(paths: Iterable[Path]) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler()

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
            payload = {
                "level": record.levelname,
                "name": record.name,
                "time": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
                "message": record.getMessage(),
            }
            if record.exc_info:
                payload["exc_info"] = self.formatException(record.exc_info)
            return orjson.dumps(payload).decode()

    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(orjson.dumps(data))


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return orjson.loads(path.read_bytes())


class Instrument(BaseModel):
    symbol: str
    provider: str
    yahoo_symbol: Optional[str] = None
    kind: str
    point_value: Optional[float] = None
    pip_value: Optional[float] = None
    min_step: float
    ltf_interval: str
    htf_interval: str


class Signal(BaseModel):
    id: str
    time: datetime
    side: str  # LONG or SHORT
    symbol: str
    entry: float
    sl: float
    tp: float
    rr: float
    why: str
    metrics: Dict[str, Any] = Field(default_factory=dict)


class PositionPlan(BaseModel):
    size_units: float
    risk_amount: float
    risk_pct: float
    value_per_point: float


def floor_to_step(price: float, step: float) -> float:
    return (price // step) * step


def ceil_to_step(price: float, step: float) -> float:
    return ((price + step - 1e-12) // step) * step

