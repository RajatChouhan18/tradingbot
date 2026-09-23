"""
PDF-BASED PRICE ACTION BOT (VERSION 3 - TRADINGVIEW FEED & MODULAR TXCORE ARCHITECTURE)
Source: BO Price Action Book by Ishaq's Binary Academy

MODULAR ARCHITECTURE:
  - Provider Layer:        txcore.providers.TradingViewProvider
  - Candle & Pattern Layer: txcore.analysis (candle, patterns, levels)
  - Strategy State Engine: txcore.strategies.PDFPriceActionStrategy
  - Safety & News Filter:  txcore.filters.FinnhubNewsFilter
  - Output & Notifiers:    txcore.execution (telegram, file_logger)
  - Deduplication & Audit: txcore.audit (deduplicator, auditor)
  - Interactive Charting:  txcore.visualization.create_interactive_chart
"""

import sys
import time
from datetime import datetime, timezone

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Configuration import
from config.settings import (
    TRADINGVIEW_USERNAME,
    TRADINGVIEW_PASSWORD,
    FINNHUB_API_KEY,
    FINNHUB_BASE_URL,
    NEWS_LOOKBACK_MINUTES,
    NEWS_CACHE_TTL,
    TELEGRAM_BOT_TOKEN,
    CHAT_ID,
    CANDLE_SYNC,
    PAIR_REQUEST_DELAY,
    SCAN_INTERVAL_SECONDS,
    LOOKBACK_MINUTES,
    PAIRS,
    PAIR_CURRENCIES,
)

# Core framework modules
from txcore import (
    TradingViewProvider,
    PDFPriceActionStrategy,
    FinnhubNewsFilter,
    TelegramNotifier,
    SignalDeduplicator,
    TradeAuditor,
    log_signal_to_file,
    log_market_data_to_file,
    create_interactive_chart,
)

# Initialize singletons
provider = TradingViewProvider(
    username=TRADINGVIEW_USERNAME,
    password=TRADINGVIEW_PASSWORD,
    default_exchange="FX_IDC",
    pair_mappings=PAIRS,
)

strategy = PDFPriceActionStrategy(scan_bars=8, lookback_sr=20)

news_filter = FinnhubNewsFilter(
    api_key=FINNHUB_API_KEY,
    lookback_minutes=NEWS_LOOKBACK_MINUTES,
    cache_ttl_seconds=NEWS_CACHE_TTL,
    base_url=FINNHUB_BASE_URL,
    pair_currencies=PAIR_CURRENCIES,
)

telegram_notifier = TelegramNotifier(
    bot_token=TELEGRAM_BOT_TOKEN,
    chat_id=CHAT_ID,
)

deduplicator = SignalDeduplicator(max_age_seconds=86400.0)
auditor = TradeAuditor()


def wait_for_candle_close():
    """
    Synchronizes execution to 2 seconds after the minute candle closes (:02s).
    """
    now = datetime.now(timezone.utc)
    seconds_to_wait = 60 - now.second + 2
    if seconds_to_wait > 60:
        seconds_to_wait -= 60

    print(f"⏳ Sleeping {seconds_to_wait:.1f}s until next 1-minute candle close (:02s)...")
    time.sleep(seconds_to_wait)


def scan_pair(pair: str):
    """
    Executes the modular pipeline for a single pair:
      1. Download candles via TradingViewProvider.
      2. Log raw market data to tv_market_data.log (optional toggle).
      3. Drop forming in-progress candle (df.iloc[:-1]).
      4. Evaluate core price action pattern + retracement rejection via Strategy.
      5. Apply Finnhub Macro News Filter.
      6. Return verified Signal or None.
    """
    df = provider.get_candles(pair, timeframe="1m", lookback_bars=LOOKBACK_MINUTES)
    if df is None or len(df) < 5:
        return None

    # ================================================================
    # 1. TRADINGVIEW MARKET DATA LOGGING
    # (Comment the line below to turn OFF saving TV market data to file)
    # ================================================================
    log_market_data_to_file(pair, df)

    # CRITICAL: Always slice off the last row (the in-progress forming candle)
    completed = df.iloc[:-1].copy()

    # Strategy Evaluation (State machine, retracement & level rejection, entry readiness)
    signal = strategy.evaluate(completed, symbol=pair)
    if not signal:
        return None

    # Safety News Circuit Breaker
    is_allowed, block_reason = news_filter.is_allowed(pair)
    if not is_allowed:
        auditor.record_signal(pair, signal.direction.value, signal.pattern, "BLOCKED", str(block_reason))
        print(f"{pair}: SIGNAL BLOCKED - {block_reason}")
        return None

    return signal, completed


def main():
    print("=" * 70)
    print("PDF PRICE ACTION LIVE SIGNAL BOT (V3 - MODULAR TXCORE ARCHITECTURE)")
    print("FEED PROVIDER:    TRADINGVIEW (FX_IDC)")
    print(f"CANDLE SYNC:      {'ENABLED (triggers at :02s of each minute)' if CANDLE_SYNC else 'DISABLED'}")
    print(f"INTER-PAIR DELAY: {PAIR_REQUEST_DELAY}s (Rate-limit pacing)")
    print(f"PAIRS MONITORED:  {len(PAIRS)} Forex Pairs (1-Minute Candles)")
    print("=" * 70)

    if not telegram_notifier.is_configured:
        print("⚠️ [WARNING] CHAT_ID is empty or set to 'dummy_chat_id'. Telegram alerts will be skipped.")

    while True:
        if CANDLE_SYNC:
            wait_for_candle_close()

        cycle_start = time.time()
        auditor.cycle_count += 1
        deduplicator.prune()

        for pair in PAIRS:
            try:
                res = scan_pair(pair)
                if res is None:
                    time.sleep(PAIR_REQUEST_DELAY)
                    continue

                signal, completed_df = res

                # Deduplication Check: Prevent re-alerting on the same setup
                if deduplicator.is_duplicate(signal.pair, signal.pattern, signal.candle_time):
                    time.sleep(PAIR_REQUEST_DELAY)
                    continue

                # Construct Alert Message
                alert_text = signal.to_alert_message(version_tag="V3 - MODULAR TXCORE")

                # ================================================================
                # BOT OUTPUT HANDLERS
                # (Comment or uncomment either line to remove or add it!)
                # ================================================================

                # 1. FILE LOGGING: Comment the line below to turn OFF saving to file
                log_signal_to_file(alert_text)

                # 2. TELEGRAM ALERT: Comment the line below to turn OFF Telegram alerts
                telegram_notifier.send(alert_text, signal=signal)

                # 3. INTERACTIVE CHART: Generates standalone HTML visual chart with annotations
                try:
                    chart_path = create_interactive_chart(
                        completed_df,
                        symbol=signal.pair,
                        signal=signal,
                        support_level=signal.level if signal.direction.value == "CALL" else None,
                        resistance_level=signal.level if signal.direction.value == "PUT" else None,
                    )
                    print(f"📊 [CHART CREATED] {chart_path}")
                except Exception as chart_err:
                    print(f"⚠️ [CHART ERROR] {chart_err}")

                deduplicator.record(signal.pair, signal.pattern, signal.candle_time)
                auditor.record_signal(signal.pair, signal.direction.value, signal.pattern, "APPROVED")

                print(
                    f"SIGNAL | {signal.pair} | "
                    f"{signal.direction.value} | "
                    f"{signal.pattern} | Key Level: {signal.level:.5f} | Price: {signal.price:.5f}"
                )

                time.sleep(PAIR_REQUEST_DELAY)

            except Exception as e:
                print(f"{pair}: ERROR: {e}")
                time.sleep(PAIR_REQUEST_DELAY)

        elapsed = time.time() - cycle_start
        print(f"✅ Completed scan cycle across {len(PAIRS)} pairs in {elapsed:.1f}s.")

        if not CANDLE_SYNC:
            remaining_sleep = max(1.0, SCAN_INTERVAL_SECONDS - elapsed)
            time.sleep(remaining_sleep)


if __name__ == "__main__":
    main()
