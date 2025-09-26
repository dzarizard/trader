from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional

import typer

from .app.utils import get_logger, load_yaml, ensure_dirs
from .app.scheduler import run_intraday_loop_once, run_eod_once
from .app.backtest import run_backtest_preset


app = typer.Typer(add_completion=False, no_args_is_help=True)
logger = get_logger("cli")


@app.command()
def scan(mode: str = typer.Option("eod", help="intraday or eod")) -> None:
    """Run scanner once (EOD) or enter scheduled loop (intraday)."""
    cfg_dir = Path(__file__).resolve().parent.parent / "config"
    ensure_dirs([
        Path(__file__).resolve().parent.parent / "data" / "cache",
        Path(__file__).resolve().parent.parent / "data" / "reports",
    ])

    instruments = load_yaml(cfg_dir / "instruments.yaml")
    rules = load_yaml(cfg_dir / "rules.yaml")
    account = load_yaml(cfg_dir / "account.yaml")
    macro = load_yaml(cfg_dir / "macro.yaml")

    if mode.lower() == "intraday":
        logger.info({"msg": "Starting intraday loop"})
        run_intraday_loop_once(instruments, rules, account, macro)
    elif mode.lower() == "eod":
        logger.info({"msg": "Running EOD scan"})
        run_eod_once(instruments, rules, account, macro)
    else:
        raise typer.BadParameter("mode must be intraday or eod")


@app.command()
def backtest(preset: str = typer.Option("eod_spy_qqq", help="Preset name")) -> None:
    """Run backtest preset and write HTML/CSV report to data/reports."""
    run_backtest_preset(preset)


@app.command()
def dashboard() -> None:
    """Launch Streamlit dashboard."""
    os.execvp("streamlit", [
        "streamlit", "run", str(Path(__file__).resolve().parent / "app" / "dashboard.py")
    ])


if __name__ == "__main__":
    app()

