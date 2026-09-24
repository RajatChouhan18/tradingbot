"""
txcore.visualization.chart_builder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Standalone, interactive HTML charting engine supporting:
  1. TradingView Lightweight Charts (v4.2.1) - Authentic TradingView UI,
     crosshair HUD inspector, quick zoom presets, S/R toggles, and clickable pattern audit table.
  2. Plotly (plotly.graph_objects) - Pure Python scientific dashboard backup.
Default engine is 'tradingview'. Charts are saved in the exports directory.
"""

import os
import json
import webbrowser
from datetime import datetime
from typing import Optional, List, Dict, Any
import pandas as pd
import plotly.graph_objects as go

from txcore.models.types import Signal, SetupResult, Direction
from txcore.analysis.candle import candle_parts, weak_bullish, weak_bearish
from txcore.analysis.levels import key_levels
from txcore.analysis.patterns import (
    bullish_engulfing,
    bearish_engulfing,
    piercing_line,
    dark_cloud_cover,
)

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_CHARTS_DIR = os.path.join(WORKSPACE_DIR, "exports", "charts")


def scan_df_for_patterns(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Scans candlestick DataFrame for historical patterns to populate the audit table.
    """
    setups: List[Dict[str, Any]] = []
    n = len(df)
    if n < 5:
        return setups

    for i in range(1, n):
        row = df.iloc[i]
        t = str(row["time"])
        ts = int(pd.to_datetime(row["time"]).timestamp())

        if bullish_engulfing(df, i):
            supp, _ = key_levels(df, i)
            setups.append({
                "pattern": "Bullish Engulfing",
                "direction": "CALL",
                "pattern_time": t,
                "pattern_timestamp": ts,
                "level": supp,
                "status": "PATTERN_ONLY",
                "reason": "Bullish candle engulfs prior bearish candle body.",
            })
        elif bearish_engulfing(df, i):
            _, res = key_levels(df, i)
            setups.append({
                "pattern": "Bearish Engulfing",
                "direction": "PUT",
                "pattern_time": t,
                "pattern_timestamp": ts,
                "level": res,
                "status": "PATTERN_ONLY",
                "reason": "Bearish candle engulfs prior bullish candle body.",
            })
        elif piercing_line(df, i):
            supp, _ = key_levels(df, i)
            setups.append({
                "pattern": "Piercing Line",
                "direction": "CALL",
                "pattern_time": t,
                "pattern_timestamp": ts,
                "level": supp,
                "status": "PATTERN_ONLY",
                "reason": "Bullish candle opens lower and closes past 50% midpoint.",
            })
        elif dark_cloud_cover(df, i):
            _, res = key_levels(df, i)
            setups.append({
                "pattern": "Dark Cloud Cover",
                "direction": "PUT",
                "pattern_time": t,
                "pattern_timestamp": ts,
                "level": res,
                "status": "PATTERN_ONLY",
                "reason": "Bearish candle opens higher and closes past 50% midpoint.",
            })

    return setups


def build_tradingview_chart_html(
    pair: str,
    df: pd.DataFrame,
    setups: Optional[List[Dict[str, Any]]] = None,
    signal: Optional[Signal] = None,
    highlight_setup: Optional[Dict[str, Any]] = None,
    support_level: Optional[float] = None,
    resistance_level: Optional[float] = None,
) -> str:
    """
    Generates a standalone, dark-themed HTML report powered by TradingView Lightweight Charts (v4.2.1).
    Visualizes exact candlestick data, pattern markers, retracement points, S/R levels,
    live cursor inspection HUD, and full pattern audit table.
    """
    if setups is None:
        setups = scan_df_for_patterns(df)
    else:
        setups = list(setups)

    # Incorporate active signal into setups and highlight
    if signal is not None:
        sig_ts = int(pd.to_datetime(signal.candle_time).timestamp())
        sig_setup = {
            "pattern": signal.pattern,
            "direction": signal.direction.value,
            "pattern_time": str(signal.candle_time),
            "pattern_timestamp": sig_ts,
            "level": signal.level,
            "status": "CONFIRMED_SIGNAL",
            "reason": signal.reason,
        }
        # Avoid duplicate row in audit table
        matched = False
        for s in setups:
            s_ts = int(s.get("pattern_timestamp") or pd.to_datetime(s.get("pattern_time")).timestamp())
            if s_ts == sig_ts and s.get("pattern") == signal.pattern:
                s["status"] = "CONFIRMED_SIGNAL"
                s["reason"] = signal.reason
                matched = True
                break
        if not matched:
            setups.append(sig_setup)

        if highlight_setup is None:
            highlight_setup = {
                "level": signal.level,
                "direction": signal.direction.value,
                "pattern": signal.pattern,
                "time": sig_ts,
            }

    n = len(df)
    is_jpy = "JPY" in pair.upper()
    precision = 3 if is_jpy else 5
    min_move = 0.001 if is_jpy else 0.00001

    candle_data = []
    analysis_map = {}
    support_series = []
    resistance_series = []
    last_timestamp = -1

    for i in range(n):
        row = df.iloc[i]
        t = int(pd.to_datetime(row["time"]).timestamp())
        if t <= last_timestamp:
            continue  # Ensure strict monotonic time progression for Lightweight Charts
        last_timestamp = t

        p = candle_parts(row)
        supp, res = key_levels(df, i) if i >= 20 else (float(row["low"]), float(row["high"]))
        wb = weak_bullish(row)
        wbear = weak_bearish(row)

        c_type = "Normal"
        if p.is_bullish:
            c_type = "Weak Bullish (Retracement)" if wb else "Strong Bullish"
        elif p.is_bearish:
            c_type = "Weak Bearish (Retracement)" if wbear else "Strong Bearish"

        max_wick = max(p.upper_wick, p.lower_wick)
        ratio = p.body / max(0.000001, max_wick)

        candle_data.append({
            "time": t,
            "open": round(float(row["open"]), precision),
            "high": round(float(row["high"]), precision),
            "low": round(float(row["low"]), precision),
            "close": round(float(row["close"]), precision),
        })

        analysis_map[t] = {
            "time_str": str(row["time"]),
            "open": f"{float(row['open']):.{precision}f}",
            "high": f"{float(row['high']):.{precision}f}",
            "low": f"{float(row['low']):.{precision}f}",
            "close": f"{float(row['close']):.{precision}f}",
            "body": f"{p.body:.{precision}f}",
            "upper_wick": f"{p.upper_wick:.{precision}f}",
            "lower_wick": f"{p.lower_wick:.{precision}f}",
            "ratio": f"{ratio:.2f}",
            "type": c_type,
            "bullish": p.is_bullish,
            "support": f"{supp:.{precision}f}",
            "resistance": f"{res:.{precision}f}",
        }

        support_series.append({"time": t, "value": round(supp, precision)})
        resistance_series.append({"time": t, "value": round(res, precision)})

    # Build markers for all setups
    markers = []
    seen_marker_times = set()
    for s in setups:
        p_t = int(s.get("pattern_timestamp") or pd.to_datetime(s.get("pattern_time")).timestamp())
        if p_t in seen_marker_times:
            continue
        seen_marker_times.add(p_t)

        is_signal = s.get("status") == "CONFIRMED_SIGNAL"
        p_name = s.get("pattern") or s.get("pattern_name", "Pattern")

        if s.get("direction") == "CALL":
            markers.append({
                "time": p_t,
                "position": "belowBar",
                "color": "#10b981" if is_signal else "#059669",
                "shape": "arrowUp",
                "text": f"🟢 {p_name}" + (" (SIGNAL)" if is_signal else ""),
            })
        else:
            markers.append({
                "time": p_t,
                "position": "aboveBar",
                "color": "#ef4444" if is_signal else "#dc2626",
                "shape": "arrowDown",
                "text": f"🔴 {p_name}" + (" (SIGNAL)" if is_signal else ""),
            })

    markers.sort(key=lambda m: m["time"])

    highlight_json = "null"
    if highlight_setup:
        highlight_json = json.dumps({
            "level": float(highlight_setup.get("level", 0.0)),
            "direction": highlight_setup.get("direction", "CALL"),
            "pattern": highlight_setup.get("pattern", ""),
            "time": highlight_setup.get("time"),
        })

    confirmed_count = sum(1 for s in setups if s.get("status") == "CONFIRMED_SIGNAL")
    latest_close = f"{float(candle_data[-1]['close']):.{precision}f}" if candle_data else "-"

    table_rows = []
    for idx, s in enumerate(setups, 1):
        status = s.get("status", "PATTERN_ONLY")
        p_name = s.get("pattern") or s.get("pattern_name", "Pattern")
        badge_cls = "badge-confirmed" if status == "CONFIRMED_SIGNAL" else "badge-pattern"
        dir_cls = "badge-call" if s.get("direction") == "CALL" else "badge-put"
        p_ts = int(s.get("pattern_timestamp") or pd.to_datetime(s.get("pattern_time")).timestamp())
        lvl = float(s.get("level", 0.0))
        table_rows.append(f"""
                <tr>
                    <td>{idx}</td>
                    <td>{s.get('pattern_time', '')}</td>
                    <td><b>{p_name}</b></td>
                    <td><span class="badge {dir_cls}">{s.get('direction', '')}</span></td>
                    <td>{lvl:.{precision}f}</td>
                    <td><span class="badge {badge_cls}">{status}</span></td>
                    <td style="color: var(--text-muted);">{s.get('reason', '')}</td>
                    <td><button onclick="zoomToTimestamp({p_ts})">🔍 Zoom</button></td>
                </tr>
        """)

    table_body = "".join(table_rows) if table_rows else """
                <tr>
                    <td colspan="8" style="text-align: center; color: var(--text-muted); padding: 20px;">
                        No price action patterns detected in the fetched historical window.
                    </td>
                </tr>
    """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TradingView Recreated Chart - {pair} (PDF Price Action)</title>
    <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        :root {{
            --bg-primary: #131722;
            --bg-secondary: #1e222d;
            --bg-card: #2a2e39;
            --text-primary: #d1d4dc;
            --text-muted: #787b86;
            --border-color: #363a45;
            --bullish: #26a69a;
            --bearish: #ef5350;
            --accent: #2962ff;
            --warning: #f59e0b;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        }}
        body {{
            background-color: var(--bg-primary);
            color: var(--text-primary);
            padding: 16px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-secondary);
            padding: 14px 20px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            margin-bottom: 12px;
            flex-wrap: wrap;
            gap: 12px;
        }}
        .title-group {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .pair-badge {{
            font-size: 20px;
            font-weight: 700;
            color: #fff;
        }}
        .tag {{
            background: rgba(41, 98, 255, 0.15);
            color: #2962ff;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            border: 1px solid rgba(41, 98, 255, 0.3);
        }}
        .stats-group {{
            display: flex;
            gap: 16px;
        }}
        .stat-item {{
            display: flex;
            flex-direction: column;
            align-items: flex-end;
        }}
        .stat-label {{
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
        }}
        .stat-value {{
            font-size: 14px;
            font-weight: 600;
        }}
        .toolbar {{
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }}
        button {{
            background: var(--bg-secondary);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        button:hover {{
            background: var(--bg-card);
            border-color: #505664;
        }}
        button.active {{
            background: var(--accent);
            color: #fff;
            border-color: var(--accent);
        }}
        #chart-container {{
            width: 100%;
            height: 520px;
            background: var(--bg-secondary);
            border-radius: 8px;
            border: 1px solid var(--border-color);
            position: relative;
        }}
        .chart-legend {{
            position: absolute;
            top: 12px;
            left: 14px;
            z-index: 10;
            pointer-events: none;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 12px;
            background: rgba(19, 23, 34, 0.88);
            padding: 8px 14px;
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            font-size: 13px;
            backdrop-filter: blur(6px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        }}
        .legend-pair {{
            font-weight: 700;
            color: #fff;
            margin-right: 4px;
        }}
        .legend-ohlc, .legend-extra {{
            display: flex;
            gap: 10px;
        }}
        .legend-ohlc span, .legend-extra span {{
            color: var(--text-muted);
        }}
        .leg-val {{
            font-weight: 600;
            color: var(--text-primary);
        }}
        .leg-val.bullish, .val.bullish {{ color: var(--bullish) !important; }}
        .leg-val.bearish, .val.bearish {{ color: var(--bearish) !important; }}
        .inspector-panel {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px 18px;
            margin-top: 12px;
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            font-size: 13px;
        }}
        .inspector-item {{
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}
        .inspector-item .lbl {{
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
        }}
        .inspector-item .val {{
            font-weight: 600;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: 600;
            margin: 20px 0 10px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .table-container {{
            background: var(--bg-secondary);
            border-radius: 8px;
            border: 1px solid var(--border-color);
            overflow-x: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            text-align: left;
        }}
        th {{
            background: var(--bg-card);
            color: var(--text-muted);
            padding: 10px 14px;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 11px;
            border-bottom: 1px solid var(--border-color);
        }}
        td {{
            padding: 10px 14px;
            border-bottom: 1px solid var(--border-color);
        }}
        tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }}
        .badge-call {{ background: rgba(38, 166, 154, 0.2); color: var(--bullish); }}
        .badge-put {{ background: rgba(239, 83, 80, 0.2); color: var(--bearish); }}
        .badge-confirmed {{ background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.4); }}
        .badge-pattern {{ background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.4); }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title-group">
            <span class="pair-badge">{pair}</span>
            <span class="tag">1-Minute</span>
            <span class="tag">TradingView Feed</span>
            <span class="tag">PDF Price Action</span>
        </div>
        <div class="stats-group">
            <div class="stat-item">
                <span class="stat-label">Total Bars</span>
                <span class="stat-value">{len(candle_data)}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Patterns Found</span>
                <span class="stat-value">{len(setups)}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Confirmed Signals</span>
                <span class="stat-value" style="color: #10b981;">{confirmed_count}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Latest Close</span>
                <span class="stat-value">{latest_close}</span>
            </div>
        </div>
    </div>

    <div class="toolbar">
        <button onclick="chart.timeScale().fitContent()">🔄 Fit All Candles</button>
        <button onclick="zoomRecent(30)">🔍 Zoom Last 30 Bars</button>
        <button onclick="zoomRecent(60)">🔍 Zoom Last 60 Bars</button>
        <button id="btn-sr" onclick="toggleSR()">📏 Toggle S/R Lines</button>
        <button id="btn-markers" onclick="toggleMarkers()">🎯 Toggle Markers</button>
    </div>

    <div id="chart-container">
        <div id="chart-legend" class="chart-legend">
            <span class="legend-pair">{pair} · 1m</span>
            <span class="legend-ohlc">
                <span>O: <span id="leg-open" class="leg-val">-</span></span>
                <span>H: <span id="leg-high" class="leg-val">-</span></span>
                <span>L: <span id="leg-low" class="leg-val">-</span></span>
                <span>C: <span id="leg-close" class="leg-val">-</span></span>
                <span id="leg-change" class="leg-val">-</span>
            </span>
            <span class="legend-extra">
                <span>Type: <span id="leg-type" class="leg-val">-</span></span>
                <span style="color: #10b981;">Supp: <span id="leg-supp" class="leg-val">-</span></span>
                <span style="color: #ef4444;">Res: <span id="leg-res" class="leg-val">-</span></span>
            </span>
        </div>
    </div>

    <div class="inspector-panel" id="inspector">
        <div class="inspector-item"><span class="lbl">Candle Time (UTC)</span><span class="val" id="ins-time">-</span></div>
        <div class="inspector-item"><span class="lbl">Open</span><span class="val" id="ins-open">-</span></div>
        <div class="inspector-item"><span class="lbl">High</span><span class="val" id="ins-high">-</span></div>
        <div class="inspector-item"><span class="lbl">Low</span><span class="val" id="ins-low">-</span></div>
        <div class="inspector-item"><span class="lbl">Close</span><span class="val" id="ins-close">-</span></div>
        <div class="inspector-item"><span class="lbl">Change</span><span class="val" id="ins-change">-</span></div>
        <div class="inspector-item"><span class="lbl">Body</span><span class="val" id="ins-body">-</span></div>
        <div class="inspector-item"><span class="lbl">Upper Wick</span><span class="val" id="ins-uw">-</span></div>
        <div class="inspector-item"><span class="lbl">Lower Wick</span><span class="val" id="ins-lw">-</span></div>
        <div class="inspector-item"><span class="lbl">Candle Type</span><span class="val" id="ins-type">-</span></div>
        <div class="inspector-item"><span class="lbl">20-Bar Support</span><span class="val" style="color: var(--bullish);" id="ins-supp">-</span></div>
        <div class="inspector-item"><span class="lbl">20-Bar Resistance</span><span class="val" style="color: var(--bearish);" id="ins-res">-</span></div>
    </div>

    <div class="section-title">
        📋 Pattern Analysis & Verification Audit Table
    </div>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Pattern Time (UTC)</th>
                    <th>Pattern Name</th>
                    <th>Direction</th>
                    <th>Key Level</th>
                    <th>Audit Status</th>
                    <th>Rule Verification Breakdown</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
{table_body}
            </tbody>
        </table>
    </div>

    <script>
        const candleData = {json.dumps(candle_data)};
        const markersData = {json.dumps(markers)};
        const analysisData = {json.dumps(analysis_map)};
        const supportSeriesData = {json.dumps(support_series)};
        const resistanceSeriesData = {json.dumps(resistance_series)};
        const highlightSetup = {highlight_json};

        const pricePrecision = {precision};
        const priceMinMove = {min_move};
        const priceFormatConfig = {{
            type: 'price',
            precision: pricePrecision,
            minMove: priceMinMove,
        }};

        const container = document.getElementById('chart-container');
        const chart = LightweightCharts.createChart(container, {{
            width: container.clientWidth,
            height: 520,
            layout: {{
                background: {{ color: '#131722' }},
                textColor: '#d1d4dc',
            }},
            localization: {{
                priceFormatter: (p) => Number(p).toFixed(pricePrecision),
            }},
            grid: {{
                vertLines: {{ color: '#1f2937' }},
                horzLines: {{ color: '#1f2937' }},
            }},
            crosshair: {{
                mode: LightweightCharts.CrosshairMode.Normal,
            }},
            rightPriceScale: {{
                borderColor: '#363a45',
            }},
            timeScale: {{
                borderColor: '#363a45',
                timeVisible: true,
                secondsVisible: false,
            }},
        }});

        window.addEventListener('resize', () => {{
            chart.applyOptions({{ width: container.clientWidth }});
        }});

        const candleSeries = chart.addCandlestickSeries({{
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
            priceFormat: priceFormatConfig,
        }});
        candleSeries.setData(candleData);
        candleSeries.setMarkers(markersData);

        const supportSeries = chart.addLineSeries({{
            color: '#10b981',
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            title: '20-Bar Support',
            priceFormat: priceFormatConfig,
        }});
        supportSeries.setData(supportSeriesData);

        const resistanceSeries = chart.addLineSeries({{
            color: '#ef4444',
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            title: '20-Bar Resistance',
            priceFormat: priceFormatConfig,
        }});
        resistanceSeries.setData(resistanceSeriesData);

        if (highlightSetup && highlightSetup.level) {{
            const isCall = highlightSetup.direction === 'CALL';
            const formattedLevel = Number(highlightSetup.level).toFixed(pricePrecision);
            candleSeries.createPriceLine({{
                price: highlightSetup.level,
                color: isCall ? '#10b981' : '#ef4444',
                lineWidth: 2,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                title: 'Key ' + (isCall ? 'Support' : 'Resistance') + ': ' + formattedLevel,
            }});
        }}

        let showSR = true;
        function toggleSR() {{
            showSR = !showSR;
            supportSeries.applyOptions({{ visible: showSR }});
            resistanceSeries.applyOptions({{ visible: showSR }});
            document.getElementById('btn-sr').classList.toggle('active', showSR);
        }}

        let showMarkers = true;
        function toggleMarkers() {{
            showMarkers = !showMarkers;
            candleSeries.setMarkers(showMarkers ? markersData : []);
            document.getElementById('btn-markers').classList.toggle('active', showMarkers);
        }}

        function zoomRecent(n) {{
            if (candleData.length <= n) {{
                chart.timeScale().fitContent();
                return;
            }}
            const from = candleData[candleData.length - n].time;
            const to = candleData[candleData.length - 1].time + 120;
            chart.timeScale().setVisibleRange({{ from, to }});
        }}

        function zoomToTimestamp(ts) {{
            chart.timeScale().setVisibleRange({{
                from: ts - (12 * 60),
                to: ts + (12 * 60),
            }});
        }}

        function formatPrice(val) {{
            return Number(val).toFixed(pricePrecision);
        }}

        function updateInspector(candle, data) {{
            if (!candle) return;
            const open = candle.open;
            const high = candle.high;
            const low = candle.low;
            const close = candle.close;
            const diff = close - open;
            const diffPct = open !== 0 ? (diff / open) * 100 : 0;
            const isBull = close >= open;
            const colorCls = isBull ? 'bullish' : 'bearish';
            const sign = diff >= 0 ? '+' : '';

            // Update In-Chart Legend (Top-Left overlay)
            document.getElementById('leg-open').innerText = formatPrice(open);
            document.getElementById('leg-high').innerText = formatPrice(high);
            document.getElementById('leg-low').innerText = formatPrice(low);
            document.getElementById('leg-close').innerText = formatPrice(close);
            
            const legChange = document.getElementById('leg-change');
            legChange.innerText = `${{sign}}${{formatPrice(diff)}} (${{sign}}${{diffPct.toFixed(2)}}%)`;
            legChange.className = 'leg-val ' + colorCls;

            const cType = data ? data.type : (isBull ? 'Bullish' : 'Bearish');
            const legType = document.getElementById('leg-type');
            legType.innerText = cType;
            legType.className = 'leg-val ' + colorCls;

            document.getElementById('leg-supp').innerText = data ? data.support : '-';
            document.getElementById('leg-res').innerText = data ? data.resistance : '-';

            // Update Bottom Inspector Panel
            const timeStr = data ? data.time_str : (new Date(candle.time * 1000).toISOString().replace('T', ' ').substring(0, 19) + ' UTC');
            document.getElementById('ins-time').innerText = timeStr;
            document.getElementById('ins-open').innerText = formatPrice(open);
            document.getElementById('ins-high').innerText = formatPrice(high);
            document.getElementById('ins-low').innerText = formatPrice(low);
            document.getElementById('ins-close').innerText = formatPrice(close);

            const insChange = document.getElementById('ins-change');
            insChange.innerText = `${{sign}}${{formatPrice(diff)}} (${{sign}}${{diffPct.toFixed(2)}}%)`;
            insChange.className = 'val ' + colorCls;

            const body = data ? data.body : formatPrice(Math.abs(diff));
            const uw = data ? data.upper_wick : formatPrice(high - Math.max(open, close));
            const lw = data ? data.lower_wick : formatPrice(Math.min(open, close) - low);

            document.getElementById('ins-body').innerText = body;
            document.getElementById('ins-uw').innerText = uw;
            document.getElementById('ins-lw').innerText = lw;

            const typeElem = document.getElementById('ins-type');
            typeElem.innerText = cType;
            typeElem.className = 'val ' + colorCls;

            document.getElementById('ins-supp').innerText = data ? data.support : '-';
            document.getElementById('ins-res').innerText = data ? data.resistance : '-';
        }}

        const latestCandle = candleData && candleData.length > 0 ? candleData[candleData.length - 1] : null;
        const latestAnalysis = latestCandle ? (analysisData[latestCandle.time] || analysisData[String(latestCandle.time)]) : null;

        if (latestCandle) {{
            updateInspector(latestCandle, latestAnalysis);
        }}

        chart.subscribeCrosshairMove(param => {{
            if (
                param === undefined ||
                param.point === undefined ||
                !param.time ||
                param.point.x < 0 ||
                param.point.x > container.clientWidth ||
                param.point.y < 0 ||
                param.point.y > container.clientHeight
            ) {{
                if (latestCandle) {{
                    updateInspector(latestCandle, latestAnalysis);
                }}
                return;
            }}

            const candle = param.seriesData ? param.seriesData.get(candleSeries) : null;
            if (!candle) return;

            const t = typeof candle.time === 'number' ? candle.time : (candle.time && candle.time.timestamp ? candle.time.timestamp : param.time);
            const data = analysisData[t] || analysisData[String(t)] || null;

            updateInspector(candle, data);
        }});

        container.addEventListener('mouseleave', () => {{
            if (latestCandle) {{
                updateInspector(latestCandle, latestAnalysis);
            }}
        }});

        if (highlightSetup && highlightSetup.time) {{
            zoomToTimestamp(highlightSetup.time);
        }} else {{
            zoomRecent(60);
        }}
    </script>
</body>
</html>
"""
    return html


def build_plotly_chart(
    df: pd.DataFrame,
    symbol: str,
    signal: Optional[Signal] = None,
    setup: Optional[SetupResult] = None,
    support_level: Optional[float] = None,
    resistance_level: Optional[float] = None,
    lookback_bars: int = 40,
) -> go.Figure:
    """Generates pure Python Plotly interactive chart figure."""
    recent = df.tail(lookback_bars).copy()
    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=recent["time"],
            open=recent["open"],
            high=recent["high"],
            low=recent["low"],
            close=recent["close"],
            name=symbol,
            increasing_line_color="#10b981",
            decreasing_line_color="#ef4444",
        )
    )

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

    title_suffix = ""
    if signal is not None:
        title_suffix = f" — [{signal.direction.value}] {signal.pattern}"
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
    return fig


def create_interactive_chart(
    df: pd.DataFrame,
    symbol: str,
    signal: Optional[Signal] = None,
    setup: Optional[SetupResult] = None,
    support_level: Optional[float] = None,
    resistance_level: Optional[float] = None,
    output_dir: Optional[str] = None,
    lookback_bars: int = 180,
    engine: str = "tradingview",
    setups: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Renders an interactive HTML candlestick chart and saves it into the exports directory.
    
    Engines:
      - 'tradingview' (default): True TradingView Lightweight Charts (v4.2.1)
        with HUD inspector, quick zoom presets, S/R toggles, and pattern audit table.
      - 'plotly': Pure-Python data science candlestick chart.

    Saves both timestamped file and latest_{symbol}.html in exports/charts/.
    Returns the absolute path to the timestamped HTML file.
    """
    if output_dir is None:
        output_dir = DEFAULT_CHARTS_DIR
    os.makedirs(output_dir, exist_ok=True)

    clean_symbol = symbol.replace("/", "_").replace(":", "_")
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_file = os.path.join(output_dir, f"chart_{clean_symbol}_{timestamp_str}.html")
    latest_file = os.path.join(output_dir, f"latest_{clean_symbol}.html")

    recent = df.tail(lookback_bars).copy() if lookback_bars > 0 else df.copy()

    if engine.lower() == "plotly":
        fig = build_plotly_chart(
            recent,
            symbol=symbol,
            signal=signal,
            setup=setup,
            support_level=support_level,
            resistance_level=resistance_level,
            lookback_bars=min(len(recent), 40),
        )
        fig.write_html(timestamped_file, include_plotlyjs="cdn")
        fig.write_html(latest_file, include_plotlyjs="cdn")
    else:
        # Default: TradingView Lightweight Charts
        html_content = build_tradingview_chart_html(
            pair=symbol,
            df=recent,
            setups=setups,
            signal=signal,
            support_level=support_level,
            resistance_level=resistance_level,
        )
        with open(timestamped_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        with open(latest_file, "w", encoding="utf-8") as f:
            f.write(html_content)

    return timestamped_file


def recreate_tradingview_chart(
    pair: str,
    df: Optional[pd.DataFrame] = None,
    highlight_setup: Optional[Dict[str, Any]] = None,
    from_cache: bool = False,
    auto_open: bool = True,
    n_bars: int = 180,
    send_tg: bool = False,
) -> Optional[str]:
    """
    Recreates the TradingView chart for visual verification of patterns,
    candle types, retracements, and S/R key levels.
    Used by chart_recreator.py companion CLI.
    """
    from txcore.providers.tradingview import TradingViewProvider
    from config.settings import TRADINGVIEW_USERNAME, TRADINGVIEW_PASSWORD, PAIRS, TELEGRAM_BOT_TOKEN, CHAT_IDS
    from txcore.execution.telegram import TelegramNotifier

    if df is None or df.empty:
        provider = TradingViewProvider(
            username=TRADINGVIEW_USERNAME,
            password=TRADINGVIEW_PASSWORD,
            default_exchange="FX_IDC",
            pair_mappings=PAIRS,
        )
        print(f"📡 Fetching latest {n_bars} bars for {pair} from TradingView...")
        df = provider.get_candles(pair, timeframe="1m", lookback_bars=n_bars)

    if df is None or df.empty:
        print(f"❌ Cannot recreate chart for {pair}: No candlestick data available.")
        return None

    chart_path = create_interactive_chart(
        df,
        symbol=pair,
        lookback_bars=n_bars,
        engine="tradingview",
    )

    print(f"📊 [CHART CREATED] TradingView chart saved to: {chart_path}")

    if auto_open:
        try:
            webbrowser.open(f"file:///{os.path.abspath(chart_path)}")
            print("🌐 Opened chart in default web browser.")
        except Exception as e:
            print(f"⚠️ Could not open browser automatically: {e}")

    if send_tg and TELEGRAM_BOT_TOKEN:
        notifier = TelegramNotifier(bot_token=TELEGRAM_BOT_TOKEN, chat_ids=CHAT_IDS)
        notifier.send_document(chart_path, caption=f"📊 TradingView Recreated Chart: {pair} (1m)")

    return chart_path


def audit_pair_patterns(pair: str, df: Optional[pd.DataFrame] = None, from_cache: bool = False, n_bars: int = 180):
    """
    Audits and prints all detected price action patterns and their
    confirmation breakdown for a given pair.
    """
    from txcore.providers.tradingview import TradingViewProvider
    from config.settings import TRADINGVIEW_USERNAME, TRADINGVIEW_PASSWORD, PAIRS

    if df is None or df.empty:
        provider = TradingViewProvider(
            username=TRADINGVIEW_USERNAME,
            password=TRADINGVIEW_PASSWORD,
            default_exchange="FX_IDC",
            pair_mappings=PAIRS,
        )
        df = provider.get_candles(pair, timeframe="1m", lookback_bars=n_bars)

    if df is None or df.empty:
        print(f"No candle data available for {pair}.")
        return

    setups = scan_df_for_patterns(df)
    print("=" * 80)
    print(f"PRICE ACTION PATTERN AUDIT REPORT: {pair}")
    print(f"TOTAL BARS: {len(df)} | TOTAL SETUPS FOUND: {len(setups)}")
    print("=" * 80)
    if not setups:
        print(f"No patterns found in the last {n_bars} bars.")
        return

    for idx, s in enumerate(setups, 1):
        status_icon = "🟢" if s.get("direction") == "CALL" else "🔴"
        print(f"{idx}. {status_icon} [{s['status']}] {s['pattern']} ({s['direction']})")
        print(f"   Time:      {s['pattern_time']}")
        print(f"   Key Level: {float(s['level']):.5f}")
        print(f"   Reason:    {s['reason']}\n")


def run_test_signal(pair: str = "GBP/USD"):
    """
    Generates a test signal for verification, renders chart, and tests dispatch.
    """
    from config.settings import TELEGRAM_BOT_TOKEN, CHAT_IDS
    from txcore.execution.telegram import TelegramNotifier
    from txcore.providers.tradingview import TradingViewProvider
    from config.settings import TRADINGVIEW_USERNAME, TRADINGVIEW_PASSWORD, PAIRS

    provider = TradingViewProvider(
        username=TRADINGVIEW_USERNAME,
        password=TRADINGVIEW_PASSWORD,
        default_exchange="FX_IDC",
        pair_mappings=PAIRS,
    )
    df = provider.get_candles(pair, timeframe="1m", lookback_bars=60)
    if df is None or len(df) < 5:
        print(f"Could not fetch test candles for {pair}.")
        return

    last_row = df.iloc[-1]
    test_sig = Signal(
        pair=pair,
        direction=Direction.CALL,
        pattern="Bullish Engulfing",
        level=float(last_row["low"]),
        price=float(last_row["close"]),
        candle_time=pd.to_datetime(last_row["time"]),
        reason="[TEST SIGNAL] End-to-end verification signal.",
    )

    chart_path = create_interactive_chart(
        df,
        symbol=pair,
        signal=test_sig,
        engine="tradingview",
    )
    print(f"✅ Generated test chart: {chart_path}")

    notifier = TelegramNotifier(bot_token=TELEGRAM_BOT_TOKEN, chat_ids=CHAT_IDS)
    alert_text = test_sig.to_alert_message(version_tag="TEST - TRADINGVIEW CHART")
    notifier.send(alert_text, signal=test_sig, chart_path=chart_path)
