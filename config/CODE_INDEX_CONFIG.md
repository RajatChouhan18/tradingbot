# TxBot Code Index: Configuration Module (`config`)

> **Module Identifier**: `config`  
> **Index Suffix**: `CONFIG`  
> **Source Directory**: [`config/`](file:///e:/Txbot/config)  
> **Role**: Unified environment configuration, exchange calendars, credentials, asset watchlists (Forex & Indian Markets), and system constants.

---

## 1. Module Overview & Responsibilities

The `config` package provides centralized, environment-aware configuration across all modules. It guarantees that credentials, API rate limits, exchange calendars, and instrument watchlists are decoupled from core algorithmic code.

### Key Responsibilities
- **Environment Management**: Loads keys securely from `.env` via `python-dotenv`.
- **Forex Configuration**: 19 major and cross currency pairs with exchange mappings (`FX_IDC`) and currency tokenization for news filtering.
- **Indian Market Settings**:
  - Operational session hours: Pre-market (`09:00-09:15`), Normal (`09:15-15:30`), Post-market (`15:30-16:00`) in `Asia/Kolkata` timezone.
  - Comprehensive index definitions: `NIFTY`, `BANKNIFTY`, `FINNIFTY`, `MIDCPNIFTY`, `NIFTYIT`, etc.
  - Indian equity universe: Standard NIFTY 50 and bluechip tickers (`RELIANCE`, `TCS`, `HDFCBANK`, `INFY`, etc.).
- **Telegram Dispatches**: Resolves single or multiple comma-separated chat IDs from `CHAT_IDS` and `TELEGRAM_BOT_TOKEN`.

---

## 2. File Index & Exported Symbols

| File | Primary Constants & Functions | Key Responsibility |
|---|---|---|
| [`settings.py`](file:///e:/Txbot/config/settings.py) | `TELEGRAM_BOT_TOKEN`, `CHAT_IDS`, `PAIRS`, `PAIR_CURRENCIES`, `INDIAN_INDEXES`, `INDIAN_STOCKS`, `INDIAN_NORMAL_MARKET_OPEN`, `INDIAN_NORMAL_MARKET_CLOSE`, `INDIAN_MARKET_TIMEZONE`, `FINNHUB_API_KEY`, `SCAN_INTERVAL_SECONDS` | Master configuration variables and watchlists. |
| [`__init__.py`](file:///e:/Txbot/config/__init__.py) | Exports all primary settings | Re-exports all variables for clean top-level imports (`from config import settings`). |

---

## 3. Configuration Reference Table

| Variable Name | Default / Type | Purpose & Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | `str` (from `.env`) | Telegram Bot API token for dispatching signal alerts. |
| `CHAT_IDS` | `List[str]` (from `CHAT_IDS` or `CHAT_ID`) | Target Telegram chat IDs (supports single ID or comma-delimited list). |
| `FINNHUB_API_KEY` | `str` (from `.env`) | API key for macroeconomic forex news event filtering. |
| `SCAN_INTERVAL_SECONDS` | `int` (default: `60`) | Polling cycle frequency in seconds for live continuous scanning. |
| `PAIR_REQUEST_DELAY` | `float` (default: `0.8`) | Pacing delay between sequential API requests to avoid rate limits. |
| `INDIAN_MARKET_TIMEZONE`| `"Asia/Kolkata"` | Standard time authority for Indian exchange sessions. |
| `INDIAN_NORMAL_MARKET_OPEN` | `(9, 15)` | Indian market regular trading open time (09:15 AM IST). |
| `INDIAN_NORMAL_MARKET_CLOSE`| `(15, 30)` | Indian market regular trading close time (03:30 PM IST). |
| `PAIRS` | `Dict[str, Dict[str, str]]` | 19 Forex pairs mapped to TradingView symbol and exchange (`FX_IDC`). |
| `INDIAN_INDEXES` | `Dict[str, Dict[str, str]]` | Indian index dictionary (`NIFTY`, `BANKNIFTY`, `FINNIFTY`, etc.). |
| `INDIAN_STOCKS` | `Dict[str, Dict[str, str]]` | Top Indian equity universe with exchange and industry metadata. |

---

## 4. Token-Saving AI Guide

- When checking exchange trading hours, import `INDIAN_NORMAL_MARKET_OPEN` and `INDIAN_NORMAL_MARKET_CLOSE` from `config.settings`.
- Do not hardcode Telegram tokens or symbol maps; always import them from `config.settings`.
