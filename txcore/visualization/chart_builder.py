"""
txcore.visualization.chart_builder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Generates standalone, interactive HTML candlestick charts using Plotly.
Visualizes candles, dynamic Support/Resistance lines, pattern annotations, and entry triggers.
"""

import os
from datetime import datetime
from typing import Optional
import pandas as pd
import plotly.graph_objects as go
from txcore.models.types import Signal, SetupResult


WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_CHARTS_DIR = os.path.join(WORKSPACE_DIR, "exports", "charts")


def create_interactive_chart(
    df: pd.DataFrame,
    symbol: str,
    signal: Optional[Signal] = None,
    setup: Optional[SetupResult] = None,
    support_level: Optional[float] = None,
    resistance_level: Optional[float] = None,
    output_dir: Optional[str] = None,
    lookback_bars: int = 40,
) -> str:
    """
    Renders an interactive HTML candlestick chart and saves it to disk.
    Returns the absolute path to the generated HTML file.
    """
    if output_dir is None:
        output_dir = DEFAULT_CHARTS_DIR
    os.makedirs(output_dir, exist_ok=True)

    # Use the most recent N bars for clean visualization
    recent = df.tail(lookback_bars).copy()

    fig = go.Figure()

    # 1. Candlestick trace
    fig.add_trace(
        go.Candlestick(
            x=recent["time"],
            open=recent["open"],
            high=recent["high"],
            low=recent["low"],
            close=recent["close"],
            name=symbol,
            increasing_line_color="#10b981",  # Emerald Green
            decreasing_line_color="#ef4444",  # Crimson Red
        )
    )

    # 2. Add Support Level
    if support_level is not None:
        fig.add_hline(
            y=support_level,
            line_dash="dash",
            line_color="#10b981",
            line_width=1.5,
            annotation_text=f"Support: {support_level:.5f}",
            annotation_position="bottom right",
            annotation_font_color="#10b981",
        )

    # 3. Add Resistance Level
    if resistance_level is not None:
        fig.add_hline(
            y=resistance_level,
            line_dash="dash",
            line_color="#ef4444",
            line_width=1.5,
            annotation_text=f"Resistance: {resistance_level:.5f}",
            annotation_position="top right",
            annotation_font_color="#ef4444",
        )

    # 4. Add Signal / Setup Annotations
    title_suffix = ""
    if signal is not None:
        title_suffix = f" — [{signal.direction.value}] {signal.pattern}"
        # Marker on the last bar
        entry_bar = recent.iloc[-1]
        fig.add_annotation(
            x=entry_bar["time"],
            y=entry_bar["close"],
            text=f"🚨 SIGNAL: {signal.direction.value}<br>{signal.pattern}",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor="#f59e0b",
            ax=0,
            ay=-45 if signal.direction.value == "CALL" else 45,
            bgcolor="#1e293b",
            bordercolor="#f59e0b",
            borderwidth=1.5,
            font=dict(color="#ffffff", size=11),
        )

    # Layout styling (Dark / Terminal theme)
    fig.update_layout(
        title=f"<b>{symbol}</b> (1-Minute) Price Action Analysis{title_suffix}",
        title_font=dict(size=16, color="#f8fafc"),
        template="plotly_dark",
        plot_bgcolor="#0f172a",
        paper_bgcolor="#020617",
        xaxis=dict(
            rangeslider=dict(visible=False),
            gridcolor="#1e293b",
            showgrid=True,
        ),
        yaxis=dict(
            gridcolor="#1e293b",
            showgrid=True,
            side="right",
        ),
        margin=dict(l=20, r=60, t=50, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    clean_symbol = symbol.replace("/", "_").replace(":", "_")
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{clean_symbol}_{timestamp_str}.html"
    filepath = os.path.join(output_dir, filename)

    fig.write_html(filepath, include_plotlyjs="cdn")
    return filepath
