from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any


@dataclass
class MacroEvent:
    name: str
    when: datetime


def parse_macro_config(cfg: Dict[str, Any]) -> List[MacroEvent]:
    events: List[MacroEvent] = []
    for e in cfg.get("important_events", []):
        name = e.get("name", "")
        for iso in e.get("schedule", []):
            try:
                when = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            except Exception:
                continue
            events.append(MacroEvent(name=name, when=when.astimezone(timezone.utc)))
    return events


def is_in_no_trade_window(now: datetime, events: List[MacroEvent], before_min: int, after_min: int) -> bool:
    start_delta = timedelta(minutes=before_min)
    end_delta = timedelta(minutes=after_min)
    for ev in events:
        if ev.when - start_delta <= now <= ev.when + end_delta:
            return True
    return False

