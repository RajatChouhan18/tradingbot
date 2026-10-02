"""
txcore.visualization.chart_cli
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Command-Line Interface for TradingView chart recreation, pattern auditing,
and end-to-end signal verification.
"""

import sys
import argparse
from typing import Optional, List
from config.settings import PAIRS
from txcore.visualization.chart_builder import (
    recreate_tradingview_chart,
    audit_pair_patterns,
    run_test_signal,
)


def build_cli_parser() -> argparse.ArgumentParser:
    """Constructs the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="chart_cli",
        description="TradingView Chart Recreator & Price Action Pattern Verification CLI",
    )
    parser.add_argument(
        "--pair",
        type=str,
        default="EUR/USD",
        help="Currency pair to recreate chart for (e.g. EUR/USD, GBP/USD, USD/JPY). Default: EUR/USD",
    )
    parser.add_argument(
        "--from-cache",
        action="store_true",
        help="Load candles and pattern analysis directly from local SQLite cache.",
    )
    parser.add_argument(
        "--audit",
        type=str,
        default=None,
        help="Print text audit report of all patterns found for this pair.",
    )
    parser.add_argument(
        "--bars",
        type=int,
        default=180,
        help="Number of 1-minute bars to load/fetch (default: 180).",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not automatically open the generated chart in default web browser.",
    )
    parser.add_argument(
        "--send-telegram",
        action="store_true",
        help="Send the generated interactive HTML chart file directly to Telegram chat/channel.",
    )
    parser.add_argument(
        "--test-signal",
        action="store_true",
        help="Run an end-to-end verification test signal with local chart creation and Telegram dispatch.",
    )
    parser.add_argument(
        "--list-pairs",
        action="store_true",
        help="List all supported 19 currency pairs.",
    )
    return parser


def run_chart_cli(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for chart CLI execution.
    Returns 0 on success, non-zero on error.
    """
    parser = build_cli_parser()
    args = parser.parse_args(argv)

    if args.list_pairs:
        print("Supported Currency Pairs:")
        for p in PAIRS:
            print(f"  • {p}")
        return 0

    if args.test_signal:
        run_test_signal(args.pair)
        return 0

    if args.audit:
        audit_pair_patterns(args.audit, from_cache=args.from_cache, n_bars=args.bars)
        return 0

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
        send_tg=args.send_telegram,
    )

    if chart_path:
        print(f"✅ Success! Chart generated at: {chart_path}")
        return 0
    else:
        print(f"❌ Failed to generate chart for {pair}.")
        return 1


if __name__ == "__main__":
    sys.exit(run_chart_cli())
