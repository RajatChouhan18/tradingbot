"""
tests.test_visualization
~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for interactive TradingView Lightweight Charts (default) and Plotly (backup).
"""

import os
from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest

from txcore.models.types import Signal, Direction, SignalStatus
from txcore.visualization.chart_builder import (
    create_interactive_chart,
    build_tradingview_chart_html,
    build_plotly_chart,
)

t0 = datetime(2026, 9, 24, 0, 0, tzinfo=timezone.utc)


def generate_mock_df(n_bars: int = 30, base_price: float = 1.1000):
    bars = []
    for i in range(n_bars):
        bars.append({
            "time": t0 + timedelta(minutes=i),
            "open": base_price + i * 0.0005,
            "high": base_price + i * 0.0005 + 0.0010,
            "low": base_price + i * 0.0005 - 0.0005,
            "close": base_price + i * 0.0005 + 0.0005,
        })
    return pd.DataFrame(bars)


class TestTradingViewChart:
    def test_default_tradingview_chart_generation(self, tmp_path):
        df = generate_mock_df(30, 1.1000)
        sig = Signal(
            pair="EUR/USD",
            direction=Direction.CALL,
            pattern="Bullish Engulfing",
            level=1.1050,
            price=1.1120,
            candle_time=df.iloc[-2]["time"],
            reason="Support rejection bounce",
            status=SignalStatus.APPROVED,
        )

        chart_file = create_interactive_chart(
            df,
            symbol="EUR/USD",
            signal=sig,
            support_level=1.1050,
            output_dir=str(tmp_path),
            engine="tradingview",
        )

        assert os.path.exists(chart_file)
        assert os.path.getsize(chart_file) > 2000

        # Also verifies latest_EUR_USD.html exists
        latest_file = os.path.join(str(tmp_path), "latest_EUR_USD.html")
        assert os.path.exists(latest_file)

        with open(chart_file, "r", encoding="utf-8") as f:
            html = f.read()

        # Verify TradingView Lightweight Charts elements
        assert "lightweight-charts@4.2.1" in html
        assert "EUR/USD" in html
        assert "Bullish Engulfing" in html
        assert "chart-legend" in html
        assert "inspector" in html
        assert "Pattern Analysis & Verification Audit Table" in html
        assert "badge-confirmed" in html

    def test_jpy_precision_formatting(self):
        df = generate_mock_df(25, 160.500)
        html = build_tradingview_chart_html(
            pair="EUR/JPY",
            df=df,
        )
        assert "EUR/JPY" in html
        assert "pricePrecision = 3" in html
        assert "priceMinMove = 0.001" in html

    def test_plotly_engine_backup(self, tmp_path):
        df = generate_mock_df(25, 1.1000)
        sig = Signal(
            pair="GBP/USD",
            direction=Direction.PUT,
            pattern="Dark Cloud Cover",
            level=1.3000,
            price=1.2950,
            candle_time=df.iloc[-1]["time"],
            reason="Resistance level rejection",
        )

        chart_file = create_interactive_chart(
            df,
            symbol="GBP/USD",
            signal=sig,
            resistance_level=1.3000,
            output_dir=str(tmp_path),
            engine="plotly",
        )

        assert os.path.exists(chart_file)
        with open(chart_file, "r", encoding="utf-8") as f:
            html = f.read()
        assert "plotly" in html.lower()
        assert "GBP" in html
        assert "USD" in html


class TestChartCLI:
    def test_cli_parser_defaults(self):
        from txcore.visualization.chart_cli import build_cli_parser
        parser = build_cli_parser()
        args = parser.parse_args(["--pair", "USD/CAD", "--bars", "120", "--no-open"])
        assert args.pair == "USD/CAD"
        assert args.bars == 120
        assert args.no_open is True
        assert args.send_telegram is False

    def test_run_chart_cli_list_pairs(self, capsys):
        from txcore.visualization.chart_cli import run_chart_cli
        exit_code = run_chart_cli(["--list-pairs"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "EUR/USD" in captured.out
        assert "USD/JPY" in captured.out

    def test_run_chart_cli_audit_mock(self):
        from unittest.mock import patch
        from txcore.visualization.chart_cli import run_chart_cli

        with patch("txcore.visualization.chart_cli.audit_pair_patterns") as mock_audit:
            exit_code = run_chart_cli(["--audit", "EUR/USD", "--bars", "50"])
            assert exit_code == 0
            mock_audit.assert_called_once_with("EUR/USD", from_cache=False, n_bars=50)

    def test_run_chart_cli_recreate_mock(self):
        from unittest.mock import patch
        from txcore.visualization.chart_cli import run_chart_cli

        with patch("txcore.visualization.chart_cli.recreate_tradingview_chart", return_value="exports/charts/mock.html") as mock_rec:
            exit_code = run_chart_cli(["--pair", "EURUSD", "--no-open"])
            assert exit_code == 0
            mock_rec.assert_called_once_with(
                pair="EUR/USD",
                from_cache=False,
                auto_open=False,
                n_bars=180,
                send_tg=False,
            )

