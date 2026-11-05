import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from hitrade.data import get_history
from hitrade.engine import DEFAULT_WATCHLIST, DataError, load_symbols, summarize


def price_chart(frame):
    fig = go.Figure(go.Candlestick(
        x=frame.index, open=frame.Open, high=frame.High, low=frame.Low, close=frame.Close,
        increasing_line_color="#00d49a", decreasing_line_color="#ff5577", name="Price",
    ))
    for column, color in [("EMA_9", "#00d49a"), ("EMA_21", "#ffb454")]:
        fig.add_scatter(x=frame.index, y=frame[column], name=column.replace("_", " "),
                        line={"color": color, "width": 1.5})
    fig.update_layout(height=460, xaxis_rangeslider_visible=False,
                      margin={"l": 0, "r": 0, "t": 20, "b": 0}, yaxis_title="INR")
    return fig


def main():
    st.set_page_config(page_title="HiTrade | Market workspace", page_icon="📈", layout="wide")
    st.title("HiTrade")
    st.caption("NSE equity research · EMA trends · Volatility-based position sizing")
    try:
        symbols = load_symbols()
    except DataError as exc:
        st.error(str(exc))
        st.stop()

    with st.sidebar:
        st.header("Workspace settings")
        source = st.radio("Data source", ["Demo (synthetic)", "Yahoo Finance"], key="source")
        capital = st.number_input("Capital (INR)", min_value=1.0, max_value=1e10,
                                  value=25000.0, step=1000.0, key="capital")
        risk = st.slider("Risk per position (%)", 0.1, 5.0, 2.0, 0.1, key="risk")
        st.metric("Risk budget per position", f"INR {capital * risk / 100:,.2f}")
        if st.button("Refresh data", key="refresh"):
            get_history.clear()
            st.session_state.pop("scan", None)
            st.session_state.pop("analysis", None)
        st.caption("Each position uses this budget independently. Results are not a portfolio allocation.")

    if source == "Demo (synthetic)":
        st.warning("DEMO MODE — generated prices dated 2025-12-31. These are not market quotes.")
    else:
        st.info("Yahoo Finance daily adjusted candles; data may be delayed or incomplete. Cache expires after 15 minutes.")
    st.caption("Rule-based research, not a trained AI model or an order service. Planned stop risk excludes gaps, slippage and fees; losses can exceed it.")

    scanner, analyzer, academy = st.tabs(["Scanner", "Analyzer", "Academy"])
    with scanner:
        st.subheader("Scan your watchlist")
        st.caption("Choose up to 25 stocks from the bundled EQ stock list. The starting watchlist is illustrative, not an index membership list.")
        selected = st.multiselect("Stocks", symbols,
                                  default=[s for s in DEFAULT_WATCHLIST if s in symbols],
                                  max_selections=25, key="watchlist")
        bullish_only = st.checkbox("Only bullish trends with an affordable quantity", value=True)
        scan_key = (source, tuple(selected))
        if st.button("Run scan", type="primary", disabled=not selected, key="scan_button"):
            frames, errors = {}, {}
            progress = st.progress(0, text="Loading daily history…")
            for index, ticker in enumerate(selected):
                try:
                    frames[ticker] = get_history(ticker, source)
                except DataError as exc:
                    errors[ticker] = str(exc)
                progress.progress((index + 1) / len(selected), text=f"Checked {ticker}")
            progress.empty()
            st.session_state.scan = (scan_key, frames, errors)

        saved = st.session_state.get("scan")
        if saved and saved[0] == scan_key:
            rows, errors = [], dict(saved[2])
            for ticker, frame in saved[1].items():
                try:
                    rows.append(summarize(ticker, frame, capital, risk))
                except ValueError as exc:
                    errors[ticker] = str(exc)
            st.caption(f"{len(rows)} analyzed · {len(errors)} unavailable · Source: {source}")
            if rows:
                results = pd.DataFrame(rows)
                if bullish_only:
                    results = results[(results.Trend == "Bullish") & (results.Quantity > 0)]
                if results.empty:
                    st.info("No stocks match this filter. Clear the bullish filter to inspect all analyzed stocks.")
                else:
                    st.dataframe(results, hide_index=True, width="stretch")
                    exported = results.assign(Source=source)
                    st.download_button("Download scan CSV", exported.to_csv(index=False).encode("utf-8"),
                                       "hitrade-scan.csv", "text/csv", key="export")
            else:
                st.warning("No stocks could be analyzed. Review the failures below or use demo mode.")
            if errors:
                with st.expander("Unavailable stocks", expanded=not rows):
                    for ticker, reason in errors.items():
                        st.write(f"{ticker}: {reason}")
        else:
            st.info("Run a scan to view results for this watchlist and data source.")

    with analyzer:
        ticker = st.selectbox("Stock", symbols,
                              index=symbols.index("RELIANCE.NS") if "RELIANCE.NS" in symbols else 0,
                              key="analyzer_stock")
        analysis_key = (source, ticker)
        if st.button("Analyze stock", key="analyze_button"):
            st.session_state.pop("analysis", None)
            with st.spinner("Loading price history…"):
                try:
                    st.session_state.analysis = (analysis_key, get_history(ticker, source))
                except DataError as exc:
                    st.error(str(exc))
        analysis = st.session_state.get("analysis")
        if analysis and analysis[0] == analysis_key:
            frame = analysis[1]
            st.caption(f"{ticker} · {source} · Latest candle: {frame.index[-1]:%Y-%m-%d}")
            if source == "Yahoo Finance" and (pd.Timestamp.now(tz="UTC") - frame.index[-1]).days > 7:
                st.warning("The latest available candle is over 7 days old. Treat this analysis as stale.")
            try:
                result = summarize(ticker, frame, capital, risk)
                c1, c2, c3 = st.columns(3)
                c1.metric("Last close", f"INR {result['Price (INR)']:,.2f}")
                c2.metric("Illustrative stop (2 × ATR)", f"INR {result['Stop (INR)']:,.2f}")
                c3.metric("Quantity within budget", result["Quantity"])
                st.write(f"Trend: **{result['Trend']}** · Position cost: **INR {result['Cost (INR)']:,.2f}** · Planned stop risk: **INR {result['Planned risk (INR)']:,.2f}**")
                if result["Quantity"] == 0:
                    st.info("The capital or risk budget cannot accommodate one share.")
                st.caption("Quantity = min(floor(risk budget / (2 × ATR)), floor(capital / price)). No leverage is assumed.")
            except ValueError as exc:
                st.warning(str(exc))
            st.plotly_chart(price_chart(frame), width="stretch")

    with academy:
        st.subheader("Understand the model")
        with st.expander("1 · Trend signals", expanded=True):
            st.write("An exponential moving average weights recent closes more heavily. HiTrade labels a trend bullish when EMA 9 is above EMA 21. This is a trend condition, not necessarily a new crossover or a forecast.")
        with st.expander("2 · Volatility and position sizing"):
            st.write("True range is the largest of high minus low, absolute high minus previous close, and absolute low minus previous close. ATR here is a 14-session simple average. The illustrative long-position stop is two ATR below the last close.")
            st.write("Both the risk budget and available capital limit quantity. Each result is independent. A stop is a planning price and does not guarantee an execution price.")
        with st.expander("3 · Data and limitations"):
            st.write("The bundled stock universe is a snapshot and can include renamed or delisted symbols. Yahoo Finance supplies adjusted daily history, not exchange-grade live quotes. Demo mode is deterministic synthetic data. No strategy performance or predictive accuracy has been established.")


if __name__ == "__main__":
    main()
