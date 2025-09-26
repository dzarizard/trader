from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import yaml


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"


def ensure_dirs() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def json_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(level)
    handler = logging.StreamHandler()

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
            payload = {
                "ts": datetime.now(tz=timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
            }
            if record.exc_info:
                payload["exc"] = self.formatException(record.exc_info)
            return json.dumps(payload)

    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger


def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def read_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@dataclass
class TelegramConfig:
    enabled: bool = False
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None


@dataclass
class SlackConfig:
    enabled: bool = False
    webhook_url: Optional[str] = None


@dataclass
class EmailConfig:
    enabled: bool = False
    smtp_url: Optional[str] = None
    from_addr: Optional[str] = None
    to_addr: Optional[str] = None


@dataclass
class AccountConfig:
    equity_ccy: str
    initial_equity: float
    telegram: TelegramConfig
    slack: SlackConfig
    email: EmailConfig


def load_account_config() -> AccountConfig:
    data = read_yaml(CONFIG_DIR / "account.yaml")
    tg = data.get("telegram", {})
    sl = data.get("slack", {})
    em = data.get("email", {})
    return AccountConfig(
        equity_ccy=data.get("equity_ccy", "USD"),
        initial_equity=float(data.get("initial_equity", 10000.0)),
        telegram=TelegramConfig(
            enabled=bool(tg.get("enabled", False)),
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", tg.get("bot_token")),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", tg.get("chat_id")),
        ),
        slack=SlackConfig(
            enabled=bool(sl.get("enabled", False)),
            webhook_url=sl.get("webhook_url"),
        ),
        email=EmailConfig(
            enabled=bool(em.get("enabled", False)),
            smtp_url=em.get("smtp_url"),
            from_addr=em.get("from"),
            to_addr=em.get("to"),
        ),
    )


def chunked(iterable: Iterable[Any], size: int) -> Iterable[list[Any]]:
    bucket: list[Any] = []
    for item in iterable:
        bucket.append(item)
        if len(bucket) >= size:
            yield bucket
            bucket = []
    if bucket:
        yield bucket

