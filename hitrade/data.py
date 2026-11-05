import streamlit as st
import yfinance as yf

from hitrade.engine import DataError, add_indicators, demo_history


@st.cache_data(ttl=900, max_entries=256, show_spinner=False)
def get_history(ticker, source):
    if source == "Demo (synthetic)":
        raw = demo_history(ticker)
    elif source == "Yahoo Finance":
        try:
            raw = yf.download(
                ticker, period="6mo", interval="1d", auto_adjust=True,
                progress=False, threads=False, timeout=10,
            )
        except Exception as exc:
            raise DataError("Market provider request failed. Retry or select demo mode.") from exc
    else:
        raise DataError("Unknown data source.")
    return add_indicators(raw, ticker)
