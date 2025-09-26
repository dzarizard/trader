from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objs as go
import streamlit as st

from .utils import BASE_DIR, CONFIG_DIR, read_yaml


st.set_page_config(page_title="CFD Trader Assistant", layout="wide")

st.title("CFD Trader Assistant")

tabs = st.tabs(["Signals", "Settings", "Performance"])

with tabs[0]:
    st.subheader("Active / Recent Signals")
    cache_dir = BASE_DIR / "data" / "cache"
    cooldown_files = list(cache_dir.glob("cooldown_*.json"))
    rows = []
    for f in cooldown_files:
        try:
            data = json.loads(f.read_text())
            symbol = f.stem.replace("cooldown_", "")
            rows.append({"symbol": symbol, **data})
        except Exception:
            pass
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df)
    else:
        st.info("No recent signals yet.")

    st.subheader("Chart")
    # Placeholder sample chart
    sample = BASE_DIR / "data" / "samples" / "NAS100_5m_sample.csv"
    if sample.exists():
        sdf = pd.read_csv(sample)
        sdf["ts"] = pd.to_datetime(sdf["ts"])
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=sdf["ts"], open=sdf["open"], high=sdf["high"], low=sdf["low"], close=sdf["close"], name="NAS100"
        ))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No sample data available for chart.")

with tabs[1]:
    st.subheader("Config Values (.yaml)")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### instruments.yaml")
        st.code((CONFIG_DIR / "instruments.yaml").read_text(), language="yaml")
    with col2:
        st.markdown("### rules.yaml")
        st.code((CONFIG_DIR / "rules.yaml").read_text(), language="yaml")
    with col3:
        st.markdown("### account.yaml")
        st.code((CONFIG_DIR / "account.yaml").read_text(), language="yaml")

with tabs[2]:
    st.subheader("Backtest Snapshots")
    reports_dir = BASE_DIR / "data" / "backtest_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    files = list(reports_dir.glob("*.json"))
    if not files:
        st.info("Run backtests to populate performance snapshots.")
    for f in files:
        st.code(f.read_text(), language="json")

