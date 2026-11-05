# HiTrade

A runnable Streamlit research MVP for NSE equities: watchlist scanning, candlestick charts, EMA trends, ATR-based position sizing and CSV export. It uses transparent rules; it does not contain a trained AI model or place orders.

## Run locally

Use Python 3.11 or 3.12. On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

On macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

Open http://localhost:8501. The existing `frountend.py` entry point remains supported. GitHub Codespaces can use the included devcontainer; CORS and XSRF protections remain enabled.

## Try the workflow

1. Keep **Demo (synthetic)** selected for an offline walkthrough. All synthetic candles have fixed historical dates and are explicitly labeled.
2. Choose capital and risk in the sidebar; select up to 25 stocks and click **Run scan**.
3. Clear the bullish filter to see all successfully analyzed stocks. Download the results as CSV, including their source and candle dates.
4. Open **Analyzer**, select a stock and click **Analyze stock** for the price chart and position calculation.
5. Change capital or risk to recalculate existing results without downloading prices again.
6. Select **Yahoo Finance** and run a new scan/analysis for provider data. Internet access is required; failures are displayed and never replaced silently with synthetic data.

**Refresh data** clears cached history and displayed results. Successful histories expire from the cache after 15 minutes. Changing source, watchlist or analyzer symbol hides mismatched results.

## Model

- Bullish condition: EMA 9 exceeds EMA 21, using `adjust=False` on daily adjusted closes. This is not necessarily a fresh crossover.
- ATR: 14-session simple average of true range.
- Illustrative long stop: last close minus two ATR.
- Quantity: the smaller of `floor(risk_budget / (2 * ATR))` and `floor(capital / last_close)`.
- Invalid history, insufficient candles, non-positive ATR and non-positive stops are rejected.

Each row is an independent position illustration, not a combined portfolio. Gaps, fees and slippage can cause losses above the planned stop risk. The model has no demonstrated predictive accuracy or profitability.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

Tests cover capital/risk constraints, invalid data, indicator math, provider response layouts, offline UI interactions, provider failures, retry, partial results and state invalidation. They do not require Yahoo access. GitHub Actions is configured for Python 3.11 and 3.12.

Optional real-provider smoke check: `python scripts/check_live.py` using the virtual environment's Python. It requires internet access and prints the number and latest date of validated RELIANCE.NS candles.

## Files and scope

- `app.py`: Streamlit interface; `frountend.py`: legacy launcher.
- `hitrade/engine.py`: validation, indicators, sizing and demo generation.
- `hitrade/data.py`: cached Yahoo/demo data access.
- `EQUITY_L (1).csv`: bundled stock snapshot, filtered to EQ series; not a verified current listing or index membership source.
- `aws_ml_task.ipynb`: preserved original Uber-analysis notebook, unrelated to HiTrade. Its Colab/data-analysis dependencies are not part of this app's requirements.
- [ISSUES_AND_UPGRADES.md](ISSUES_AND_UPGRADES.md): findings, fixes and remaining priorities.

Provider and testing API references: [yfinance download](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html) and [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).
