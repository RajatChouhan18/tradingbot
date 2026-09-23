"""
TradingView Chart Recreator & Price Action Pattern Verification Tool
Companion runner for PDF Price Action Bot (Version 3 - TradingView Feed)

Usage:
  # Fetch latest 180 bars from TradingView, cache/analyze, and recreate chart in browser:
  python chart_recreator.py --pair EUR/USD

  # Recreate chart directly from SQLite cache (zero API calls, verified historical data):
  python chart_recreator.py --pair EUR/USD --from-cache

  # View pattern audit report in CLI:
  python chart_recreator.py --audit EUR/USD

  # Recreate chart for specific bar count without auto-opening browser:
  python chart_recreator.py --pair GBP/USD --bars 300 --no-open
"""

import sys
import argparse
from pdf_price_action_bot_v3_tradingview import (
    recreate_tradingview_chart,
    audit_pair_patterns,
    run_test_signal,
    PAIRS,
)

def main():
    parser = argparse.ArgumentParser(
        description="Recreate TradingView charts and verify PDF price action patterns."
    )
    parser.add_argument(
        "--pair",
        type=str,
        default="EUR/USD",
        help="Currency pair to recreate chart for (e.g. EUR/USD, GBP/USD, USD/JPY). Default: EUR/USD"
    )
    parser.add_argument(
        "--from-cache",
        action="store_true",
        help="Load candles and pattern analysis directly from local SQLite cache (zero network calls)."
    )
    parser.add_argument(
        "--audit",
        type=str,
        default=None,
        help="Print text audit report of all patterns found for this pair."
    )
    parser.add_argument(
        "--bars",
        type=int,
        default=180,
        help="Number of 1-minute bars to load/fetch (default: 180)."
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not automatically open the generated chart in default web browser."
    )
    parser.add_argument(
        "--send-telegram",
        action="store_true",
        help="Send the generated interactive HTML chart file directly to Telegram chat/channel."
    )
    parser.add_argument(
        "--test-signal",
        action="store_true",
        help="Run an end-to-end verification test signal with local chart creation and Telegram dispatch."
    )
    parser.add_argument(
        "--list-pairs",
        action="store_true",
        help="List all supported 19 currency pairs."
    )

    args = parser.parse_args()

    if args.list_pairs:
        print("Supported Currency Pairs:")
        for p in PAIRS:
            print(f"  • {p}")
        return

    if args.test_signal:
        run_test_signal(args.pair)
        return

    if args.audit:
        audit_pair_patterns(args.audit, from_cache=args.from_cache, n_bars=args.bars)
        return

    # Normalize pair formatting (e.g. EURUSD -> EUR/USD)
    pair = args.pair.strip()
    if "/" not in pair and len(pair) == 6:
        pair = f"{pair[:3]}/{pair[3:]}"


    print(f"🚀 Recreating TradingView chart for {pair}...")
    chart_path = recreate_tradingview_chart(
        pair=pair,
        from_cache=args.from_cache,
        auto_open=not args.no_open,
        n_bars=args.bars,
        send_tg=args.send_telegram
    )

    if chart_path:
        print(f"✅ Success! Chart generated at: {chart_path}")
    else:
        print(f"❌ Failed to generate chart for {pair}.")

if __name__ == "__main__":
    main()
