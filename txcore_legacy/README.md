# txcore_legacy: Archived Reference Codebase

This directory contains the pristine, uncorrupted legacy implementation of `txcore` preserved as a permanent reference library for the **AuraTrade** modular modernization.

## Directory Index
- `analysis/`: Classical indicator math (EMA, SMA, RSI, ATR, VWAP), S/R level calculations, and candlestick pattern detectors.
- `audit/`: Legacy audit logging, signal deduplication, and file generation.
- `execution/`: Telegram notification dispatch and order execution skeletons.
- `filters/`: Market hours checks and volatility filters.
- `models/`: Original dataclasses, signal models, and candle types.
- `providers/`: Provider implementations (TradingView lightweight, Yahoo Finance, NSE public sessions, Zerodha).
- `strategies/`: Predefined strategy engines including the PDF Price Action Strategy.
- `visualization/`: Matplotlib / mplfinance chart plotting pipelines.
- Root scripts: `algotrade.py`, `pipeline.py`, `database.py`.

> **Note**: Do not edit files in this directory. All active modular development occurs in `txcore/`.
