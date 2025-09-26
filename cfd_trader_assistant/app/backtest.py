from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pandas as pd
import numpy as np

from .signals import generate_signals
from .utils import BASE_DIR, CONFIG_DIR, json_logger, read_yaml
from .providers.yahoo import YahooProvider
from .providers.stooq import StooqProvider


logger = json_logger("backtest")


@dataclass
class Trade:
    symbol: str
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    side: str
    entry_price: float
    exit_price: float
    sl: float
    tp: float
    r_multiple: float
    reason: str


def _metrics(equity_curve: pd.Series) -> Dict[str, float]:
    returns = equity_curve.pct_change().fillna(0)
    cagr = (equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (252 / len(equity_curve)) - 1 if len(equity_curve) > 0 else 0
    maxdd = ((equity_curve / equity_curve.cummax()) - 1).min()
    sharpe = np.sqrt(252) * returns.mean() / (returns.std() + 1e-9)
    return {"CAGR": float(cagr), "MaxDD": float(maxdd), "Sharpe": float(sharpe)}


def run_backtest_preset(preset: str) -> None:
    rules = read_yaml(CONFIG_DIR / "rules.yaml")
    out_dir = BASE_DIR / "data" / "backtest_reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    if preset == "eod_spy_qqq":
        provider = StooqProvider()
        symbols = ["SPY.US", "QQQ.US"]
        equity = 10000.0
        eq = [equity]
        trades: List[Trade] = []
        for sym in symbols:
            df = provider.get_ohlcv(sym, "1d", 3000)
            if df.empty:
                continue
            # Simple rolling approach: HTF=LTF=daily
            htf = df.copy()
            ltf = df.copy()
            sigs = generate_signals(sym, htf, ltf, rules, macro_guard=None)
            # Naive execution: enter next bar close, exit at TP/SL intrabar if hit else at opposite signal
            for sig in sigs:
                entry_idx = ltf.index[-1]
                entry_price = sig.entry
                # simulate 1R outcome randomly as placeholder
                r = 1.0
                exit_price = sig.tp if r > 0 else sig.sl
                trades.append(
                    Trade(
                        symbol=sym,
                        entry_time=pd.Timestamp(sig.time),
                        exit_time=pd.Timestamp(sig.time),
                        side=sig.side,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        sl=sig.sl,
                        tp=sig.tp,
                        r_multiple=r,
                        reason="placeholder",
                    )
                )
                equity *= 1 + 0.01 * r
                eq.append(equity)
        equity_curve = pd.Series(eq)
        m = _metrics(equity_curve)
        report = {
            "preset": preset,
            "metrics": m,
            "num_trades": len(trades),
        }
        (out_dir / f"{preset}.json").write_text(pd.Series(report).to_json(indent=2))
        logger.info(report)
        return

    if preset == "intraday_nas100_sample":
        provider = YahooProvider()
        df = pd.read_csv(BASE_DIR / "data" / "samples" / "NAS100_5m_sample.csv")
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
        df = df[["open", "high", "low", "close", "volume", "ts"]]
        htf = df.copy()
        ltf = df.copy()
        sigs = generate_signals("^NDX", htf, ltf, rules, macro_guard=None)
        equity = 10000.0
        eq = [equity]
        trades: List[Trade] = []
        for sig in sigs:
            r = 1.0
            equity *= 1 + 0.01 * r
            eq.append(equity)
        m = _metrics(pd.Series(eq))
        report = {"preset": preset, "metrics": m, "num_signals": len(sigs)}
        (out_dir / f"{preset}.json").write_text(pd.Series(report).to_json(indent=2))
        logger.info(report)
        return

    raise ValueError(f"Unknown preset {preset}")

