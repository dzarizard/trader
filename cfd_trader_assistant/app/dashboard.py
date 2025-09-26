from __future__ import annotations

from pathlib import Path
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(page_title="CFD Trader Assistant", layout="wide")

st.title("CFD Trader Assistant")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Signals")
    st.info("No live state persisted in MVP. Run scans to emit alerts.")

with col2:
    st.subheader("Settings (read-only)")
    cfg_dir = Path(__file__).resolve().parents[2] / "config"
    for name in ["instruments.yaml", "rules.yaml", "account.yaml", "macro.yaml"]:
        p = cfg_dir / name
        if p.exists():
            st.code(p.read_text())

st.subheader("Sample Chart")
sample_csv = Path(__file__).resolve().parents[2] / "data" / "samples" / "nas100_5m_sample.csv"
if sample_csv.exists():
    df = pd.read_csv(sample_csv, parse_dates=["ts"])
    fig = go.Figure(data=[go.Candlestick(x=df["ts"], open=df["open"], high=df["high"], low=df["low"], close=df["close"])])
    st.plotly_chart(fig, use_container_width=True)
else:
    st.write("Provide sample CSVs in data/samples to preview charts.")

