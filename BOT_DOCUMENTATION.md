# PDF Price Action Trading Bot Documentation

**Version:** 1.0.0 & 2.0.0  
**Source Strategy:** *BO Price Action Book by Ishaq's Binary Academy*  
**V1 Implementation File:** [`pdf_price_action_bot_v1.py`](file:///e:/Txbot/pdf_price_action_bot_v1.py) (Original 5s Polling Engine)  
**V2 Implementation File:** [`pdf_price_action_bot_v2.py`](file:///e:/Txbot/pdf_price_action_bot_v2.py) (Candle-Sync + Multi-Provider Feed)  
**Target Market:** Forex (19 Pairs) / Binary Options (1-minute expiry)  
**Supported Providers:** Finnhub, Twelve Data, OANDA REST API, MetaTrader 5 (MT5)  
**Alert Channel:** Telegram Bot API  

---

## 1. Overview & Strategy Philosophy

The **PDF Price Action Trading Bot** is a programmatic implementation of pure price-action trading rules. It is specifically designed to eliminate technical indicator lag:

- **No Indicators:** No Moving Averages, RSI, MACD, Stochastic, or Bollinger Bands.
- **Pure Price Action:** Decisions are based exclusively on candlestick geometry (body-to-wick ratios), trend structure (higher-highs/lower-lows), dynamic Support & Resistance levels, and multi-candle patterns.
- **Mandatory Retracement & Level Rejection:** Signals are never issued on pattern breakout alone. The bot enforces a strict "wait for retracement" rule, verifying whether the retracing candle touches and rejects a key level before issuing a signal.
- **News Safety Filter:** High-impact forex news acts strictly as a circuit breaker (filter). News events never trigger trade directions; they only inhibit signals when market volatility is unpredictable.

---

## 2. Monitored Assets

The bot continuously monitors **19 currency pairs** using OANDA symbols on Finnhub:

| Currency Pair | Finnhub / OANDA Symbol | Monitored Currencies |
| :--- | :--- | :--- |
| **EUR/JPY** | `OANDA:EUR_JPY` | EUR, JPY |
| **CAD/JPY** | `OANDA:CAD_JPY` | CAD, JPY |
| **EUR/USD** | `OANDA:EUR_USD` | EUR, USD |
| **USD/JPY** | `OANDA:USD_JPY` | USD, JPY |
| **AUD/JPY** | `OANDA:AUD_JPY` | AUD, JPY |
| **AUD/USD** | `OANDA:AUD_USD` | AUD, USD |
| **AUD/CAD** | `OANDA:AUD_CAD` | AUD, CAD |
| **GBP/USD** | `OANDA:GBP_USD` | GBP, USD |
| **GBP/AUD** | `OANDA:GBP_AUD` | GBP, AUD |
| **GBP/CAD** | `OANDA:GBP_CAD` | GBP, CAD |
| **GBP/CHF** | `OANDA:GBP_CHF` | GBP, CHF |
| **GBP/JPY** | `OANDA:GBP_JPY` | GBP, JPY |
| **USD/CAD** | `OANDA:USD_CAD` | USD, CAD |
| **USD/CHF** | `OANDA:USD_CHF` | USD, CHF |
| **EUR/GBP** | `OANDA:EUR_GBP` | EUR, GBP |
| **CHF/JPY** | `OANDA:CHF_JPY` | CHF, JPY |
| **EUR/AUD** | `OANDA:EUR_AUD` | EUR, AUD |
| **EUR/CAD** | `OANDA:EUR_CAD` | EUR, CAD |
| **EUR/CHF** | `OANDA:EUR_CHF` | EUR, CHF |

---

## 3. System Architecture & Workflow

```
[Main Loop (Every 5s)]
         │
         ▼
[Loop through 19 Pairs]
         │
         ▼
[Fetch 180 min of 1-min Candles] ──> (Drop incomplete/forming candle)
         │
         ▼
[Scan Last 8 Bars for Core Pattern]
  ├── Bullish Engulfing
  ├── Bearish Engulfing
  ├── Piercing Line (Requires prior downtrend)
  └── Dark Cloud Cover (Requires prior uptrend)
         │
         ▼
[Verify Retracement & Key Level Rejection]
  ├── Level: 20-bar rolling High (Resistance) / Low (Support)
  ├── 1st Retracement Candle: Level touch + close rejection
  └── 2nd Retracement Candle: Fallback check if 1st broke level
         │
         ▼
[Validate Entry Readiness] ──> Has required entry candle fully closed?
         │
         ▼
[Macro News Safety Check] ──> Finnhub Forex News in last 10 minutes
  ├── Contains pair currency?
  └── Matches high-impact keywords (CPI, Rate, Fed, FOMC, etc.)?
         │
    ┌────┴────────────────────────┐
    ▼                             ▼
[BLOCKED by News]          [SIGNAL APPROVED]
 (Logged to console)              │
                                  ▼
                         [Check sent_keys Deduplication]
                                  │
                                  ▼
                         [Send Telegram Alert]
```

---

## 4. Price Action Strategy Logic

### A. Candle Reading Mechanics
Candles are analyzed geometrically:
- $\text{Body} = | \text{Close} - \text{Open} |$
- $\text{Upper Wick} = \text{High} - \max(\text{Open}, \text{Close})$
- $\text{Lower Wick} = \min(\text{Open}, \text{Close}) - \text{Low}$
- **Weak Candle:** Body $\le 1.5 \times \max(\text{Upper Wick}, \text{Lower Wick})$ (indicates exhaustion/indecision).

### B. Dynamic Support & Resistance
- **Support:** Minimum low across the past 20 completed candles.
- **Resistance:** Maximum high across the past 20 completed candles.
- **Rejection Rule:** A candle touches the level ($\text{Low} \le \text{Level} \le \text{High}$) and closes on the reversal side (above Support for bullish rejection, below Resistance for bearish rejection).

### C. Signal Patterns & Execution Triggers

#### 1. Bullish Engulfing (`CALL`)
1. Bearish candle followed by a Bullish candle that completely engulfs the previous body and wicks.
2. Next candle (**Retracement**) must be weak bearish and reject dynamic **Support**.
3. *Alternative:* If the 1st retracement breaks below support, the bot waits for the 2nd retracement candle to reject support.

#### 2. Bearish Engulfing (`PUT`)
1. Bullish candle followed by a Bearish candle that completely engulfs the previous body and wicks.
2. Next candle (**Retracement**) must be weak bullish and reject dynamic **Resistance**.
3. *Alternative:* If the 1st retracement breaks above resistance, the bot waits for the 2nd retracement candle to reject resistance.

#### 3. Piercing Line (`CALL`)
1. Preceding 5 candles must confirm a **prior downtrend** (consecutive lower highs and lower lows).
2. Bearish candle followed by a Bullish candle opening with a gap down and closing above the 50% midpoint of the previous candle.
3. Next candle (**Retracement**) must close above the 50% level and reject **Support**.
4. If support was broken without rejection, waits for the 2nd candle to touch and reject support.

#### 4. Dark Cloud Cover (`PUT`)
1. Preceding 5 candles must confirm a **prior uptrend** (consecutive higher highs and higher lows).
2. Bullish candle followed by a Bearish candle opening with a gap up and closing below the 50% midpoint of the previous candle.
3. Next candle touches and rejects **Resistance**, or forms a weak bullish exhaustion candle.

---

## 5. Components & Functions Index

| Function Name | Location | Parameters | Return | Description |
| :--- | :--- | :--- | :--- | :--- |
| `check_settings()` | Line 110 | `None` | `None` | Validates presence of `FINNHUB_API_KEY` and `TELEGRAM_BOT_TOKEN`. |
| `api_get()` | Line 131 | `path`, `params=None` | `dict`/`list` | Generic Finnhub HTTP GET wrapper with 15s timeout and error handling. |
| `get_candles()` | Line 149 | `symbol` | `pd.DataFrame` or `None` | Pulls 180 min of 1-minute OHLC candle data; sorts and cleans. |
| `candle_parts()` | Line 194 | `row` | `dict` | Extracts open, high, low, close, body, wicks, and bullish/bearish flags. |
| `weak_bullish()` | Line 217 | `row` | `bool` | Evaluates if bullish candle body is $\le 1.5 \times$ max wick. |
| `weak_bearish()` | Line 226 | `row` | `bool` | Evaluates if bearish candle body is $\le 1.5 \times$ max wick. |
| `prior_downtrend()` | Line 238 | `df`, `end_index`, `bars=5` | `bool` | Checks for lower highs and lower lows across the preceding 5 bars. |
| `prior_uptrend()` | Line 264 | `df`, `end_index`, `bars=5` | `bool` | Checks for higher highs and higher lows across the preceding 5 bars. |
| `key_levels()` | Line 290 | `df`, `end_index`, `window=20` | `tuple(support, resistance)` | Computes rolling min low (support) and max high (resistance). |
| `touches_level()` | Line 300 | `row`, `level` | `bool` | Verifies whether price penetrated or touched a given price level. |
| `rejects_support()` | Line 306 | `row`, `support` | `bool` | Touched support and closed above it. |
| `rejects_resistance()`| Line 317 | `row`, `resistance` | `bool` | Touched resistance and closed below it. |
| `bullish_engulfing()`| Line 333 | `df`, `i` | `bool` | Detects textbook Bullish Engulfing pattern. |
| `bearish_engulfing()`| Line 350 | `df`, `i` | `bool` | Detects textbook Bearish Engulfing pattern. |
| `piercing_line()` | Line 379 | `df`, `i` | `bool` | Detects Piercing Line pattern with 50% retracement penetration. |
| `dark_cloud_cover()` | Line 408 | `df`, `i` | `bool` | Detects Dark Cloud Cover pattern with 50% penetration. |
| `is_doji()` | Line 434 | `row` | `bool` | Identifies doji candle (body $\le 10\%$ of high-low range). |
| `is_spinning_top()` | Line 444 | `row` | `bool` | Identifies spinning top candle (body $\le 30\%$, long upper/lower wicks). |
| `find_recent_setup()`| Line 462 | `df` | `dict` or `None` | Core setup engine. Iterates the last 8 bars for pattern + retracement. |
| `get_forex_news()` | Line 618 | `None` | `list` | Queries Finnhub `/news?category=forex`. |
| `relevant_news_for_pair()` | Line 626 | `pair` | `tuple(bool, dict)` | Blocks signals if high-impact news for pair currencies occurred in last 10m. |
| `send_telegram()` | Line 701 | `message` | `None` | Sends HTTP POST request to Telegram Bot API `/sendMessage`. |
| `validate_entry()` | Line 723 | `df`, `setup` | `bool` | Verifies the required entry candle has officially closed. |
| `scan_pair()` | Line 741 | `pair`, `symbol` | `dict` or `None` | Scans a single pair through candle retrieval, setup detection, and news filter. |
| `main()` | Line 790 | `None` | `None` | Infinite polling loop over all 19 pairs with deduplication and throttling. |

---

## 6. Input & Output Formats

### A. Environment File (`.env`)
```env
FINNHUB_API_KEY=your_finnhub_api_key_here
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRstuVWXyz
CHAT_ID=123456789
```

### B. Telegram Signal Output
```text
🚨 PDF PRICE ACTION SIGNAL 🚨

💱 Pair: EUR/USD
⏱ Timeframe: 1 Minute
📊 Signal: CALL
🕯 Pattern: Bullish Engulfing
💰 Price: 1.08542
📍 Key Level: 1.08480

📌 PDF Rule:
Retracement touched support, rejected and formed weak bearish candle.

📰 News filter: CLEAR
⚠️ Demo/backtest before live money.
```

### C. Internal Signal Object
```python
{
    "blocked": False,
    "pair": "EUR/USD",
    "direction": "CALL",
    "pattern": "Bullish Engulfing",
    "level": 1.08480,
    "price": 1.08542,
    "candle_time": Timestamp('2026-09-22 00:30:00+0000', tz='UTC'),
    "reason": "Retracement touched support, rejected and formed weak bearish candle."
}
```

---

## 7. Deployment & Operational Considerations

### A. Critical Finnhub API Constraints
1. **Endpoint Access Tier:** Finnhub's `/forex/candle` endpoint requires an account tier that supports historical forex minute candles (often Premium). Free keys may encounter `403 Forbidden` or empty data frames.
2. **Rate Limit Throttling:** 19 pairs scanned every 5 seconds generates up to ~228 API calls per minute. Standard free keys are capped at 30–60 calls/minute, causing `429 Too Many Requests`.
   - *Fix:* Increase `SCAN_SECONDS` from 5 to 45–60 seconds, or migrate market feeds to MetaTrader 5 (MT5 Python API), OANDA REST API, or TwelveData.

### B. Telegram Bot Configuration
1. Obtain bot token from [@BotFather](https://t.me/botfather).
2. Start the bot and send a message.
3. Retrieve your numeric Chat ID:
   ```
   https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates
   ```
4. Replace `dummy_chat_id` in `.env` with your actual numeric `CHAT_ID`.

### C. 24/7 Server Deployment (Linux / VPS)
To run in production via `systemd`:
```ini
# /etc/systemd/system/txbot.service
[Unit]
Description=PDF Price Action Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Txbot
ExecStart=/home/ubuntu/Txbot/venv/bin/python pdf_price_action_bot_v1.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
Start and enable the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable txbot
sudo systemctl start txbot
```

---

## 8. Version 2.0 Enhancements (`pdf_price_action_bot_v2.py`)

Version 2.0 was created to solve API rate-limit bottlenecks, eliminate redundant polling, prevent memory leaks, and add multi-broker feed adaptability while preserving 100% of the PDF's price-action trading rules.

### Key Architectural Upgrades in V2

| Feature | Version 1.0 (`v1`) | Version 2.0 (`v2`) |
| :--- | :--- | :--- |
| **Polling Schedule** | Blind 5-second polling loops (~228 calls/min) | **Candle-Boundary Synchronization** (sleeps until `:02`s of each minute) |
| **API Request Volume** | ~13,680 API requests / hour | **~1,200 API requests / hour** (>85% reduction) |
| **Burst Protection** | None; floods all 19 pairs in milliseconds | **Intelligent pacing** (`PAIR_REQUEST_DELAY = 1.2s` between pairs) |
| **Data Providers** | Finnhub only | **Multi-Provider**: Finnhub, Twelve Data, OANDA REST, MetaTrader 5 |
| **News API Efficiency** | Fetches news repeatedly for every pair | **60-second in-memory TTL cache** (1 call/minute) |
| **Deduplication Cache** | Unbounded `set()` (long-term memory leak) | **Timestamped dict with 24-hour auto-pruning** |
| **Rate Limit Handling** | Unhandled 429 crash | **Automatic 30-second backoff and retry** |

### Environment Variables & Configuration Guide (`.env`)

Below is the complete reference of all supported environment variables in Version 2.0:

```env
# ============================================================
# DATA PROVIDER SELECTION
# ============================================================
# Options: 'mock', 'finnhub', 'twelvedata', 'oanda', 'mt5'
DATA_PROVIDER=mock

# ============================================================
# DATA PROVIDER CREDENTIALS
# ============================================================
# Finnhub API Key (Required if DATA_PROVIDER=finnhub)
FINNHUB_API_KEY=your_finnhub_key_here

# Twelve Data API Key (Required if DATA_PROVIDER=twelvedata)
TWELVEDATA_API_KEY=your_twelvedata_key_here

# OANDA REST API (Required if DATA_PROVIDER=oanda)
OANDA_API_KEY=your_oanda_personal_token
OANDA_ENVIRONMENT=practice # 'practice' (demo) or 'live'

# ============================================================
# TELEGRAM NOTIFICATIONS
# ============================================================
TELEGRAM_BOT_TOKEN=8641821032:AAFbcAZDsO1Pyvb90uzerCDodngQL0YG_vo
CHAT_ID=123456789

# ============================================================
# SCHEDULING & RATE-LIMIT PACING
# ============================================================
CANDLE_SYNC=true               # Synchronize scan cycles with candle close boundaries (:02s)
PAIR_REQUEST_DELAY=1.2         # Delay in seconds between pair calls (prevents API bursts)
SCAN_INTERVAL_SECONDS=60       # Fallback polling interval if CANDLE_SYNC=false
```

---

### Deep Dive: `DATA_PROVIDER` Values & Exact Usage

| Provider Value | Purpose & Description | Required Credentials | Tier & Limitations |
| :--- | :--- | :--- | :--- |
| **`mock`** *(Recommended for Testing)* | Generates realistic synthetic 1-minute Forex candles locally. Injects a textbook Bullish Engulfing + Retracement pattern on `EUR/USD` so you can verify the entire scanning, deduplication, Telegram dispatch, and file logging pipeline immediately without external APIs. | None (Runs 100% offline) | Completely free; zero API calls. |
| **`finnhub`** *(Default)* | Connects to Finnhub's `/forex/candle` and `/news` endpoints using OANDA symbols (`OANDA:EUR_USD`). | `FINNHUB_API_KEY` | **Important:** Finnhub requires a paid subscription for 1-minute historical Forex candles. On free accounts, Finnhub returns `403 Forbidden` on `/forex/candle`. |
| **`twelvedata`** | Connects to Twelve Data's REST API (`/time_series`) for 1-minute Forex data. | `TWELVEDATA_API_KEY` | Free API tier available (up to 800 API credits/day, 8 calls/minute). |
| **`oanda`** | Connects directly to OANDA v20 REST API (`/v3/instruments/{pair}/candles`). Works for both live broker accounts and free unlimited demo accounts. | `OANDA_API_KEY`, `OANDA_ENVIRONMENT` (`practice` or `live`) | Free demo accounts provide real-time institutional Forex candle feeds with no subscription costs. |
| **`mt5`** | Interfaces directly with a running MetaTrader 5 desktop terminal on Windows using the official `MetaTrader5` Python package. Zero HTTP latency. | None in `.env` (Requires MT5 terminal running on your PC) | 100% free with any broker supporting MT5 (e.g., Exness, IC Markets, Pepperstone). Requires `pip install MetaTrader5`. |

---

### Timing & Rate-Limiting Variables Explained

1. **`CANDLE_SYNC` (`true` / `false`, Default: `true`):**
   * **When `true`:** The bot sleeps until 2 seconds after the minute mark (e.g. `xx:xx:02`). Because 1-minute candles close at `:00s`, broker servers need 1–2 seconds to aggregate and finalize the candle. This guarantees that queries only trigger when a fresh, finalized candle exists, cutting API consumption by >85%.
   * **When `false`:** The bot runs on a standard sleep loop governed by `SCAN_INTERVAL_SECONDS`.

2. **`PAIR_REQUEST_DELAY` (Float, Default: `1.2`):**
   * Paces requests across the 19 currency pairs. With a 1.2s delay, scanning all 19 pairs takes ~23 seconds, well within the 60-second candle window and strictly below the rate limits of free APIs (such as Finnhub's 30/60 calls/min).

3. **`SCAN_INTERVAL_SECONDS` (Integer, Default: `60`):**
   * The duration to sleep between scanning cycles if `CANDLE_SYNC=false`.

---

### Telegram Configuration Explained

1. **`TELEGRAM_BOT_TOKEN`:**
   * Generated via [@BotFather](https://t.me/botfather) on Telegram using the `/newbot` command.
   * Example: `8641821032:AAFbcAZDsO1Pyvb90uzerCDodngQL0YG_vo`.
2. **`CHAT_ID`:**
   * The unique numeric identifier of your personal chat, group, or channel.
   * **How to retrieve your Chat ID:**
     1. Open Telegram and send any text message (e.g., `/start` or `hello`) to your bot.
     2. Open your browser and navigate to:
        ```
        https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/getUpdates
        ```
     3. Locate `"chat":{"id": 123456789}` in the JSON response.
     4. Paste that numeric ID into `CHAT_ID` in your `.env` file.

---

### Adding / Removing File Logging & Telegram (Direct Commenting)

Both file logging and Telegram alerts are positioned directly in [`pdf_price_action_bot_v2.py`](file:///e:/Txbot/pdf_price_action_bot_v2.py) at the output block in `main()`. You can immediately toggle either feature on or off by commenting or uncommenting its line:

```python
# ================================================================
# BOT OUTPUT HANDLERS
# (Comment or uncomment either line to remove or add it!)
# ================================================================

# 1. FILE LOGGING: Comment the line below to turn OFF saving to file
log_signal_to_file(message)

# 2. TELEGRAM ALERT: Comment the line below to turn OFF Telegram alerts
send_telegram(message)
```

* **To turn OFF file logging:** Add `#` before `log_signal_to_file(message)` $\rightarrow$ `# log_signal_to_file(message)`
* **To turn ON file logging:** Remove the `#` $\rightarrow$ `log_signal_to_file(message)`
* **To turn OFF Telegram:** Add `#` before `send_telegram(message)` $\rightarrow$ `# send_telegram(message)`
* **To turn ON Telegram:** Remove the `#` $\rightarrow$ `send_telegram(message)`

#### Persistent Output File Format (`signals_history.log`):

Whenever `log_signal_to_file(message)` executes, it preserves all emojis, attaches the generation timestamp (UTC and Local), specifies the 1-minute timeframe, and appends the entry to `signals_history.log`:

```text
================================================================================
🕒 LOG TIMESTAMP: 2026-09-22 01:14:01 UTC (06:44:01 Local) | TIMEFRAME: 1-Minute
--------------------------------------------------------------------------------
🚨 PDF PRICE ACTION SIGNAL (V2) 🚨

💱 Pair: EUR/USD
⏱ Timeframe: 1 Minute
📊 Signal: CALL
🕯 Pattern: Bullish Engulfing
💰 Price: 1.0854
📍 Key Level: 1.0848

📌 PDF Rule:
Retracement touched support, rejected and formed weak bearish candle.

📡 Provider: MOCK
📰 News filter: CLEAR
⚠️ Demo/backtest before live money.
================================================================================
```

---

## 9. Version 3.0 TradingView Feed, Recreated Chart & Idempotent Cache

Version 3.0 connects directly to **TradingView (FX_IDC)** via `tvDatafeed`, bypassing broker REST limits. To ensure absolute verification accuracy and computational efficiency, V3 bundles a **TradingView Chart Recreator** and an **Idempotent Historical SQLite Cache Engine**.

### A. Idempotent Past-Data & Analysis Persistence (`data/market_cache.db`)
Historical 1-minute candles and their calculated properties are permanently persisted into a local SQLite database:
1. **`candles`**: Raw OHLCV records indexed by `(pair, timestamp)`. Newly fetched bars are stored with `INSERT OR IGNORE`.
2. **`candle_analysis`**: Geometric anatomy (`body`, `upper_wick`, `lower_wick`, `ratio`), `candle_type` (e.g. Strong Bullish, Weak Bearish Retracement), and rolling 20-bar Support & Resistance.
   - **Idempotency Guarantee:** Once a past closed bar is evaluated, it is **never re-evaluated**, ensuring instant retrieval and immutable historical truth.
3. **`detected_setups`**: All identified multi-candle patterns (Bullish/Bearish Engulfing, Piercing Line, Dark Cloud Cover) with confirmation audit status (`CONFIRMED_SIGNAL`, `PATTERN_ONLY`, `LEVEL_BROKEN`).

### B. Interactive TradingView Recreated Chart
Powered by TradingView's official **Lightweight Charts (v4.2.1)**, the chart recreator outputs standalone, responsive, dark-themed HTML files into the `charts/` folder:
- **Visual Candlesticks:** High contrast green (`#26a69a`) and red (`#ef5350`) candles.
- **Dynamic S/R Level Overlay:** Rolling 20-bar Support (green dashed line) and Resistance (red dashed line).
- **Pattern Markers:** Distinct visual arrows and badges directly on pattern candles.
- **Retracement Markers:** Yellow pinpoints on candles touching & rejecting key levels.
- **Signal Entry Markers:** Target icons showing validated CALL/PUT entry points.
- **Live Cursor Inspector:** Hovering over any candle reveals exact Open, High, Low, Close, Body size, Upper/Lower wick lengths, Body-to-wick ratio, Candle classification, and active Support/Resistance.
- **Pattern Audit & Verification Table:** Clickable audit table below the chart listing all detected patterns with a "🔍 Zoom" button that smoothly centers and focuses the chart directly on that pattern.

### C. Turning Features ON and OFF (Direct Commenting)
In [`pdf_price_action_bot_v3_tradingview.py`](file:///e:/Txbot/pdf_price_action_bot_v3_tradingview.py), all components are bundled together and toggled simply by commenting or uncommenting their execution lines:

#### 1. In `scan_pair()`:
```python
# 1. TRADINGVIEW RAW MARKET DATA LOGGING (TEXT FILE)
# (Comment the line below to turn OFF saving raw text log)
log_tv_data_to_file(pair, df)

# 2. PERSISTENT MARKET DATA & IDEMPOTENT ANALYSIS CACHE (SQLITE)
# (Comment the line below to turn OFF SQLite caching & persistent analysis)
update_market_cache_and_analyze(pair, df)

# 3. AUTO CHART RECREATION ON EACH SCAN CYCLE (HTML VISUALIZATION)
# (Uncomment the line below to turn ON chart generation on every scan)
# recreate_tradingview_chart(pair, df, auto_open=False)
```

#### 2. In `main()` Output Block (When Signal Fires):
```python
# 1. FILE LOGGING: Comment the line below to turn OFF saving to file
log_signal_to_file(message)

# 2. TELEGRAM TEXT ALERT: Comment the line below to turn OFF Telegram text alerts
send_telegram(message)

# 3. RECREATE SIGNAL CHART: Comment the line below to turn OFF chart generation/popup
chart_file = recreate_signal_chart(result, auto_open=True)

# 4. SEND CHART HTML TO TELEGRAM: Comment the line below to turn OFF sending HTML chart to Telegram
send_telegram_document(chart_file, caption=f"📊 Interactive Verification Chart: {result['pair']} ({result['direction']})")
```

### D. Standalone CLI Chart Recreator Commands

You can run the chart recreator or audit patterns on demand without running the full scanning service:

```bash
# 1. Recreate chart from live TradingView data and open in browser:
python chart_recreator.py --pair EUR/USD

# 2. Recreate chart directly from SQLite cache (zero API calls, verified past analysis):
python chart_recreator.py --pair EUR/USD --from-cache

# 3. Send generated HTML chart directly to your Telegram chat/channel:
python chart_recreator.py --pair EUR/USD --from-cache --send-telegram

# 4. Run end-to-end verification test signal (creates local chart + sends to Telegram):
python chart_recreator.py --test-signal
python chart_recreator.py --pair GBP/USD --test-signal

# 5. Print text pattern audit report for any pair:
python chart_recreator.py --audit EUR/USD

# 6. Same commands available via the main bot script:
python pdf_price_action_bot_v3_tradingview.py --test-signal
python pdf_price_action_bot_v3_tradingview.py --chart EUR/USD
python pdf_price_action_bot_v3_tradingview.py --chart EUR/USD --from-cache
python pdf_price_action_bot_v3_tradingview.py --chart EUR/USD --send-telegram
python pdf_price_action_bot_v3_tradingview.py --audit EUR/USD
```






