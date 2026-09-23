"""
tests.test_visualization
~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for interactive Plotly HTML chart generation.
"""

import os
from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest

from txcore.models.types import Signal, Direction, SignalStatus
from txcore.visualization.chart_builder import create_interactive_chart

t0 = datetime(2026, 9, 24, 0, 0, tzinfo=timezone.utc)


def test_create_interactive_chart(tmp_path):
    bars = []
    for i in range(25):
        bars.append({
            "time": t0 + timedelta(minutes=i),
            "open": 1.1000 + i * 0.0005,
            "high": 1.1010 + i * 0.0005,
            "low": 1.0995 + i * 0.0005,
            "close": 1.1005 + i * 0.0005,
        })
    df = pd.DataFrame(bars)

    sig = Signal(
        pair="EUR/USD",
        direction=Direction.CALL,
        pattern="Bullish Engulfing",
        level=1.1050,
        price=1.1120,
        candle_time=df.iloc[-2]["time"],
        reason="Test pattern signal",
        status=SignalStatus.APPROVED,
    )

    chart_file = create_interactive_chart(
        df,
        symbol="EUR/USD",
        signal=sig,
        support_level=1.1050,
        output_dir=str(tmp_path),
    )

    assert os.path.exists(chart_file)
    assert os.path.getsize(chart_file) > 1000  # Should be non-trivial HTML
    with open(chart_file, "r", encoding="utf-8") as f:
        html = f.read()
        assert "EUR" in html
        assert "USD" in html
        assert "plotly" in html.lower()
