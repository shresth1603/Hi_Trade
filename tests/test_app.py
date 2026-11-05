from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from hitrade.data import get_history
from hitrade.engine import demo_history

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def clear_cache():
    get_history.clear()
    yield
    get_history.clear()


def launch(entry="app.py"):
    app = AppTest.from_file(str(ROOT / entry), default_timeout=30).run()
    assert not app.exception
    return app


def test_scan_analyze_and_recalculate_without_network():
    with patch("hitrade.data.yf.download", side_effect=AssertionError("Demo used network")):
        app = launch()
        app.checkbox[0].uncheck().run()
        app.button(key="scan_button").click().run()
        assert not app.exception
        assert len(app.dataframe[0].value) == 10
        app.button(key="analyze_button").click().run()
        assert not app.exception
        assert len(app.get("plotly_chart")) == 1
        app.number_input(key="capital").set_value(1.0).run()
        assert (app.dataframe[0].value.Quantity == 0).all()
        assert next(m for m in app.metric if m.label == "Quantity within budget").value == "0"
        app.radio(key="source").set_value("Yahoo Finance").run()
        assert not app.dataframe
        assert not app.get("plotly_chart")


def test_legacy_entrypoint_and_empty_watchlist():
    app = launch("frountend.py")
    app.multiselect(key="watchlist").set_value([]).run()
    assert app.button(key="scan_button").disabled
    assert not app.exception


def test_provider_failure_is_visible_and_retry_works():
    app = launch()
    app.radio(key="source").set_value("Yahoo Finance").run()
    with patch("hitrade.data.yf.download", return_value=pd.DataFrame()):
        app.button(key="analyze_button").click().run()
        assert app.error
        assert not app.exception
        app.multiselect(key="watchlist").set_value(["TCS.NS"]).run()
        app.button(key="scan_button").click().run()
        assert any("No stocks could" in w.value for w in app.warning)
        assert not app.exception
    with patch("hitrade.data.yf.download", return_value=demo_history("TCS.NS")):
        app.button(key="analyze_button").click().run()
        assert not app.exception
        assert len(app.get("plotly_chart")) == 1


def test_partial_scan_failure_keeps_successes_and_refresh_clears_results():
    app = launch()
    app.radio(key="source").set_value("Yahoo Finance").run()
    app.multiselect(key="watchlist").set_value(["TCS.NS", "RELIANCE.NS"]).run()
    app.checkbox[0].uncheck().run()

    def download(ticker, **kwargs):
        if ticker == "TCS.NS":
            raise TimeoutError("Provider unavailable")
        return demo_history(ticker)

    with patch("hitrade.data.yf.download", side_effect=download):
        app.button(key="scan_button").click().run()
        assert not app.exception
        assert app.dataframe[0].value.Symbol.tolist() == ["RELIANCE.NS"]
        assert any("TCS.NS" in m.value for m in app.markdown)
    app.button(key="refresh").click().run()
    assert not app.dataframe
