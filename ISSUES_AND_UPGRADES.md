# HiTrade issues and upgrades

Reviewed 2026-11-05. Scope: convert the existing single-script prototype into a usable local research MVP. No broker integration, production deployment or trained predictive model is implied.

## Issues fixed

1. **Startup failure:** the script requested `EQUITY_L.csv`, while the repository contains `EQUITY_L (1).csv`. Resolve the actual bundled file relative to the module, independent of working directory; validate its schema and EQ symbols.
2. **Duplicate Streamlit widget IDs:** capital and risk controls were repeated without keys. Use one keyed settings panel shared by scanner and analyzer.
3. **Unaffordable quantities:** risk-only sizing could exceed available cash. Cap whole-share quantity by both capital and risk; reject NaN, infinity, zero ATR and invalid stops.
4. **Misleading stock segments:** alphabetical slices were called bluechip/midcap, and the penny-stock condition mismatched its label. Replace these with an explicit user watchlist, limited to 25 symbols per scan.
5. **Silent data failures:** a bare exception handler hid failures. Validate OHLC history and report individual symbol errors, including empty/short/invalid data. Preserve successful results when other symbols fail.
6. **Unbounded cache and disappearing results:** cache now has a 15-minute TTL and 256-entry cap. Store results in session state, recalculate sizing on settings changes, and hide results when their source or selected symbols change. Add explicit refresh.
7. **Unsupported AI and safety claims:** replace `STRONG BUY`, AI language, guaranteed-loss claims and `Safe Qty` with descriptive trend and planned-risk labels. Explain that an EMA condition is not a prediction.
8. **No reliable demo:** add deterministic synthetic history, clearly marked in the UI and exports. Real-provider errors never trigger silent demo fallback.
9. **Heavy unrelated dependencies:** replace the large environment dump, including unused TensorFlow, with five direct runtime dependencies in UTF-8. Keep test dependencies separate.
10. **No onboarding or regression checks:** add setup instructions, meaningful numerical/data/UI tests and a CI workflow. Retain the legacy launcher.
11. **Disabled web protections:** remove devcontainer flags disabling CORS/XSRF, use Python 3.12 and a straightforward install command.
12. **Placeholder Academy:** add explanations of the implemented indicators, sizing formula and data limitations.

## High-impact improvements applied

Separate pure calculations from provider access and the interface so failures can be reproduced without network calls. Add budget-constrained sizing, defensive OHLC normalization, provider timeouts, bounded scans, partial-failure reporting, source/date-aware CSV exports and a complete offline workflow. These directly improve correctness, startup reliability and usability without adding an unnecessary ML stack.

## Remaining upgrades, in priority order

1. **Validated market data:** refresh the NSE stock universe from an authoritative, licensed feed; track symbol changes, delistings and exchange sessions. Current data uses a bundled snapshot and Yahoo daily adjusted candles. Analyzer warns when the latest candle exceeds seven calendar days; this is not a trading-calendar check. Scanner shows candle dates but does not enforce freshness.
2. **Strategy evaluation before predictive claims:** define an objective and implement chronological, walk-forward evaluation including transaction costs, slippage, corporate actions and a benchmark. Avoid fitting/testing on the same periods. No profitability or accuracy claim is supported by the current repository.
3. **Portfolio-level limits:** current rows each use the full capital/risk settings independently. Add aggregate exposure, correlated-position limits, fees and cash reservation before treating several rows as one portfolio.
4. **Scale data acquisition:** scans are deliberately limited to 25 sequential requests. A service with many users needs batched fetching, rate-limit-aware retries, shared storage, provider observability and cancellation. A 10-second request timeout is not a strict total scan deadline.
5. **Durable watchlists and paper trading:** current state lasts only for the Streamlit session. Add storage and paper-order lifecycle before any broker connectivity. Multi-user hosting also needs authentication and tenant isolation.
6. **Dependency reproducibility:** direct dependencies are pinned; transitive versions are resolved at installation. Maintain a tested lock/constraints file for the deployment platform and scheduled update checks.
7. **ML only with relevant data:** `aws_ml_task.ipynb` is Uber booking analysis and requires an absent dataset. It was preserved, not repurposed as a trading model. A future model needs a defined forecast target, relevant features, leakage controls and out-of-sample evaluation.

## Verification

Executed locally on Windows with Python 3.12.14:

- `python -m pytest -q`: **23 passed**. Includes 500 randomized sizing cases plus Streamlit AppTest interactions for scanner, analyzer, settings recalculation, source switching, refresh, empty watchlist, legacy launcher, partial failures and retry.
- `python -m pip check`: **No broken requirements found**.
- `python scripts/check_live.py`: **128 validated RELIANCE.NS daily candles**, latest date **2026-11-05**, retrieved from Yahoo Finance. This checks availability at verification time only.
- Streamlit server started at `http://127.0.0.1:8501`; `/_stcore/health` returned **ok**.
- `git diff --check`: passed, with only Windows line-ending conversion notices.

The UI checks use Streamlit's simulated AppTest runtime, not a browser screenshot review. CI configuration was added but GitHub-hosted CI has not been run. No trading-performance validation, production load testing or deployment was performed. Changes are local in the workspace; they have not been pushed to GitHub.
