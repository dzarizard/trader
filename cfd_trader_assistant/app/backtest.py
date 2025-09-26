from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List

import pandas as pd

from .utils import get_logger, write_json, load_yaml, Instrument
from .providers.yahoo import YahooProvider
from .rules import evaluate_trend, evaluate_triggers, evaluate_quality
from .signals import should_time_stop


logger = get_logger("backtest")


def run_backtest_preset(preset: str) -> None:
    base = Path(__file__).resolve().parents[2]
    reports = base / "data" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    rules = load_yaml(base / "config" / "rules.yaml")
    instruments = load_yaml(base / "config" / "instruments.yaml")

    # Simple single-symbol daily backtest for SPY/QQQ as placeholder
    provider = YahooProvider()
    rows: List[Dict[str, Any]] = []
    for sym in ["SPY", "QQQ"]:
        df = provider.get_ohlcv(sym, "1d", 2500)
        df = df.dropna().reset_index(drop=True)
        equity = 1_0000.0
        position = 0
        entry = 0.0
        rr = float(rules.get("risk", {}).get("rr_ratio", 2.0))
        stop_mult = float(rules.get("risk", {}).get("stop_atr_mult", 1.5))
        bars_since = 0
        for i in range(250, len(df)):
            htf = df.iloc[: i + 1].copy()
            ltf = htf.copy()
            long_ok, short_ok = evaluate_trend(htf, rules)
            trg = evaluate_triggers(ltf, rules)
            q_ok, q_m = evaluate_quality(ltf, rules)
            price = float(ltf["close"].iloc[-1])
            atr = float((ltf["high"].astype(float) - ltf["low"].astype(float)).rolling(14).mean().iloc[-1])
            if position == 0 and q_ok:
                if long_ok and trg["long"]:
                    position = 1
                    entry = price
                    sl = entry - stop_mult * atr
                    tp = entry + rr * (entry - sl)
                    bars_since = 0
                    rows.append({"symbol": sym, "side": "LONG", "entry_time": htf["ts"].iloc[-1] if "ts" in htf else None, "entry": entry, "sl": sl, "tp": tp, "exit_time": None, "exit": None, "r": None, "reason": "entry"})
                elif short_ok and trg["short"]:
                    position = -1
                    entry = price
                    sl = entry + stop_mult * atr
                    tp = entry - rr * (sl - entry)
                    bars_since = 0
                    rows.append({"symbol": sym, "side": "SHORT", "entry_time": htf["ts"].iloc[-1] if "ts" in htf else None, "entry": entry, "sl": sl, "tp": tp, "exit_time": None, "exit": None, "r": None, "reason": "entry"})
            else:
                bars_since += 1
                # Manage exits
                last = rows[-1]
                if position == 1:
                    sl = last["sl"]
                    tp = last["tp"]
                    if price <= sl:
                        r = (sl - entry) / (entry - sl)
                        last.update({"exit": sl, "exit_time": htf["ts"].iloc[-1] if "ts" in htf else None, "r": r, "reason": "SL"})
                        position = 0
                    elif price >= tp:
                        r = (tp - entry) / (entry - sl)
                        last.update({"exit": tp, "exit_time": htf["ts"].iloc[-1] if "ts" in htf else None, "r": r, "reason": "TP"})
                        position = 0
                    elif should_time_stop(bars_since, rules):
                        last.update({"exit": price, "exit_time": htf["ts"].iloc[-1] if "ts" in htf else None, "r": (price - entry) / (entry - sl), "reason": "time"})
                        position = 0
                elif position == -1:
                    sl = last["sl"]
                    tp = last["tp"]
                    if price >= sl:
                        r = (entry - sl) / (sl - entry)
                        last.update({"exit": sl, "exit_time": htf["ts"].iloc[-1] if "ts" in htf else None, "r": r, "reason": "SL"})
                        position = 0
                    elif price <= tp:
                        r = (entry - tp) / (sl - entry)
                        last.update({"exit": tp, "exit_time": htf["ts"].iloc[-1] if "ts" in htf else None, "r": r, "reason": "TP"})
                        position = 0
                    elif should_time_stop(bars_since, rules):
                        last.update({"exit": price, "exit_time": htf["ts"].iloc[-1] if "ts" in htf else None, "r": (entry - price) / (sl - entry), "reason": "time"})
                        position = 0

    trades = [r for r in rows if r.get("exit") is not None]
    df_trades = pd.DataFrame(trades)
    df_trades.to_csv(reports / f"trades_{preset}.csv", index=False)
    summary = {
        "preset": preset,
        "num_trades": len(df_trades),
        "win_rate": float((df_trades["r"] > 0).mean()) if len(df_trades) else 0.0,
        "profit_factor": float(df_trades[df_trades["r"] > 0]["r"].sum() / max(1e-9, -df_trades[df_trades["r"] < 0]["r"].sum())) if len(df_trades) else 0.0,
    }
    write_json(reports / f"backtest_{preset}.json", summary)
    (reports / f"backtest_{preset}.html").write_text("<html><body><h1>Backtest Report</h1><pre>" + df_trades.to_string(index=False) + "</pre></body></html>")
    logger.info({"msg": "Backtest finished", "preset": preset, "summary": summary})

