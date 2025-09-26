from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List

import pandas as pd

from .utils import CONFIG_DIR, read_yaml


@dataclass
class MacroEvent:
    name: str
    ts: datetime


class MacroCalendar:
    def __init__(self) -> None:
        self.events: List[MacroEvent] = []
        cfg = read_yaml(CONFIG_DIR / "macro.yaml")
        for ev in cfg.get("important_events", []):
            for iso in ev.get("schedule", []):
                self.events.append(MacroEvent(ev["name"], pd.to_datetime(iso, utc=True).to_pydatetime()))

    def has_event_near(self, ts: datetime, minutes_before: int, minutes_after: int) -> bool:
        window_start = ts - timedelta(minutes=minutes_before)
        window_end = ts + timedelta(minutes=minutes_after)
        for ev in self.events:
            if window_start <= ev.ts <= window_end:
                return True
        return False

