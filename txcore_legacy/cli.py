"""
txcore.cli
~~~~~~~~~~
Universal Command-Line Interface for market inspection, trend & pattern analysis,
interactive chart generation, and AlgoTrade pipeline execution.
Works across all markets (Forex, Indian Equities, Commodities, Crypto).
"""

import argparse
import sys
from typing import Optional, List, Dict, Any
import pandas as pd

from txcore.algotrade import (
    AlgoTrade,
    AlgoTradeConfig,
    AlgoTradeManager,
    TradeAlgo,
    TradeAlgoConfig,
    TradeAlgoManager,
)
from txcore.providers.base import BaseDataProvider
from txcore.providers.tradingview import TradingViewProvider
from txcore.providers.indian_provider import IndianMarketDataProvider
from txcore.providers.nse_provider import NSEClient
from txcore.providers.session_manager import MarketSessionManager, create_indian_session_manager
from txcore.analysis.indicators import analyze_trend
from txcore.analysis.volatility import analyze_vix
from txcore.visualization.chart_builder import create_interactive_chart, scan_df_for_patterns
from txcore.strategies.pdf_price_action import PDFPriceActionStrategy
from txcore.strategies.evaluator import StrategyEvaluator, StrategyEvaluationReport
from txcore.execution.telegram import TelegramNotifier
from txcore.execution.file_logger import log_signal_to_file
from config.settings import TELEGRAM_BOT_TOKEN, CHAT_IDS, VIX_REGIMES, INDIAN_STOCKS


def get_default_provider(market: str = "INDIAN_EQUITY") -> BaseDataProvider:
    """Instantiates the appropriate provider based on market selection."""
    if market.upper() in ("INDIAN_EQUITY", "INDIAN", "NSE", "BSE"):
        return IndianMarketDataProvider()
    return TradingViewProvider()


def print_market_snapshot(nse_client: NSEClient, session_mgr: MarketSessionManager):
    """Prints a formatted overview of market session, VIX, breadth, and benchmarks."""
    session = session_mgr.get_session_info()
    vix_quote = nse_client.get_vix_quote()
    vix_val = vix_quote.last_price if vix_quote and vix_quote.last_price > 0 else 14.5
    vix = analyze_vix(vix_val, change=vix_quote.change if vix_quote else 0.0, percent_change=vix_quote.percent_change if vix_quote else 0.0)
    breadth = nse_client.get_market_breadth("NIFTY 50")

    benchmarks = ["NIFTY 50", "NIFTY BANK", "NIFTY FINANCIAL SERVICES", "NIFTY MIDCAP SELECT", "INDIA VIX"]
    quotes = {name: nse_client.get_index_quote(name) for name in benchmarks}

    lines = [
        "🇮🇳 ========================================= 🇮🇳",
        "          INDIAN FINANCIAL MARKETS REPORT       ",
        "🇮🇳 ========================================= 🇮🇳",
        f"📅 Session:  {session.to_alert_line()}",
        f"📊 VIX:      {vix.to_summary_string()}",
        f"📈 Breadth:  {breadth.to_string()}",
        "",
        "📌 CORE BENCHMARKS:",
    ]

    for _, q in quotes.items():
        if q:
            lines.append(f"  {q.to_summary_line()}")

    # Sectoral Movers
    sector_names = ["NIFTY IT", "NIFTY AUTO", "NIFTY FMCG", "NIFTY METAL", "NIFTY PHARMA", "NIFTY REALTY"]
    sec_quotes = [nse_client.get_index_quote(s) for s in sector_names]
    active_sec = [s for s in sec_quotes if s is not None]
    if active_sec:
        sorted_sec = sorted(active_sec, key=lambda x: x.percent_change, reverse=True)
        lines.append("")
        lines.append("🏢 TOP SECTORAL MOVERS:")
        for s in (sorted_sec[:2] + sorted_sec[-2:]):
            lines.append(f"  {s.to_summary_line()}")

    lines.append("🇮🇳 =========================================")
    print("\n".join(lines))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="TxBot Universal Trading Engine & Market Intelligence CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Market snapshot & breadth
    parser.add_argument(
        "--snapshot",
        "-s",
        action="store_true",
        help="Print real-time market overview (Session, VIX, Benchmarks, Breadth, Sectors)",
    )
    parser.add_argument(
        "--stock",
        type=str,
        help="Target stock symbol (e.g. RELIANCE, TCS, HDFCBANK, INFY, SBIN)",
    )
    parser.add_argument(
        "--index",
        type=str,
        help="Target index symbol (e.g. NIFTY, BANKNIFTY, FINNIFTY, SENSEX, INDIAVIX)",
    )
    parser.add_argument(
        "--symbol",
        "--symbols",
        type=str,
        help="Generic target symbol(s) for any market (e.g. EUR/USD, RELIANCE, or comma-separated RELIANCE,TCS)",
    )
    parser.add_argument(
        "--timeframe",
        "-t",
        type=str,
        default="5m",
        choices=["1m", "3m", "5m", "15m", "1h", "1d"],
        help="Candlestick timeframe (default: 5m)",
    )
    parser.add_argument(
        "--bars",
        "-b",
        type=int,
        default=50,
        help="Number of lookback bars to extract (default: 50)",
    )
    parser.add_argument(
        "--chart",
        action="store_true",
        help="Generate an interactive TradingView Lightweight HTML chart in exports/charts/",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not automatically open the generated chart in default web browser.",
    )
    parser.add_argument(
        "--trend",
        action="store_true",
        help="Analyze price action trend, EMAs, Support & Resistance distance for the asset",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Audit all detected candlestick patterns (Engulfing, Piercing, Dark Cloud) in terminal",
    )
    parser.add_argument(
        "--scan-signal",
        action="store_true",
        help="Run strategy engine on recent completed candles and report any actionable entry signal",
    )
    parser.add_argument(
        "--scan-watchlist",
        action="store_true",
        help="Batch scan monitored watchlist for confirmed price action signals via AlgoTrade",
    )
    parser.add_argument(
        "--send-telegram",
        action="store_true",
        help="Dispatch generated signal alert text and/or chart document directly to Telegram",
    )
    parser.add_argument(
        "--breadth",
        action="store_true",
        help="Display market breadth (Advances / Declines / ADR) for NIFTY 50",
    )
    parser.add_argument(
        "--sectors",
        action="store_true",
        help="Display all sectoral indices ranked by performance",
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="Optional file path to save extracted candlestick DataFrame as CSV",
    )
    parser.add_argument(
        "--start-date",
        "--from-date",
        type=str,
        default=None,
        help="Start date/time for past data fetching & backtesting (e.g. '2026-09-01', '2026-09-20 09:15:00')",
    )
    parser.add_argument(
        "--end-date",
        "--to-date",
        type=str,
        default=None,
        help="End date/time for past data fetching & backtesting (e.g. '2026-09-25', '2026-09-26 15:30:00')",
    )
    parser.add_argument(
        "--evaluate",
        "--backtest",
        action="store_true",
        help="Evaluate/backtest strategy on historical past data and output win-rate, PnL %%, and trade records",
    )
    parser.add_argument(
        "--risk-reward",
        type=float,
        default=1.5,
        help="Risk-to-reward ratio for trade target calculation in strategy evaluation (default: 1.5)",
    )

    # AlgoTrade Process Model Options
    parser.add_argument(
        "--algo",
        action="store_true",
        help="Run an AlgoTrade process instance",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="AlgoTrade1",
        help="User-defined name for the AlgoTrade instance (e.g. 'Ishaq strategy 1', 'NiftyScalper')",
    )
    parser.add_argument(
        "--market",
        type=str,
        default="INDIAN_EQUITY",
        help="Target market for AlgoTrade (e.g. INDIAN_EQUITY, FOREX, COMMODITY, CRYPTO)",
    )

    args = parser.parse_args()

    nse_client = NSEClient()
    session_mgr = create_indian_session_manager()
    provider = get_default_provider(args.market)

    # 1. Default action if no args provided or snapshot requested
    if len(sys.argv) == 1 or args.snapshot:
        print_market_snapshot(nse_client, session_mgr)
        return

    # 2. Market breadth inspection
    if args.breadth:
        b = nse_client.get_market_breadth("NIFTY 50")
        print("\n" + b.to_string() + "\n")
        return

    # 3. Sectoral indices ranking
    if args.sectors:
        print("\n🏢 SECTORAL INDICES RANKING (By Performance):")
        print("-" * 65)
        sector_names = ["NIFTY IT", "NIFTY AUTO", "NIFTY FMCG", "NIFTY METAL", "NIFTY PHARMA", "NIFTY REALTY"]
        sec_quotes = [nse_client.get_index_quote(s) for s in sector_names]
        active = [s for s in sec_quotes if s is not None]
        for s in sorted(active, key=lambda x: x.percent_change, reverse=True):
            print(f"  {s.to_summary_line()}")
        print("-" * 65 + "\n")
        return

    # 4. AlgoTrade Process Model Execution or Batch Watchlist Scan
    if args.algo or args.scan_watchlist:
        target_symbols = []
        if args.stock:
            target_symbols.extend([s.strip().upper() for s in args.stock.split(",") if s.strip()])
        if args.index:
            target_symbols.extend([s.strip().upper() for s in args.index.split(",") if s.strip()])
        if args.symbol:
            target_symbols.extend([s.strip().upper() for s in args.symbol.split(",") if s.strip()])

        if not target_symbols and args.scan_watchlist:
            target_symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY"] + list(INDIAN_STOCKS.keys())[:7]

        config = AlgoTradeConfig(
            algo_name=args.name if args.algo else "WatchlistScanner",
            market=args.market,
            timeframe=args.timeframe,
            symbols=target_symbols or (["NIFTY", "BANKNIFTY", "RELIANCE"] if "INDIAN" in args.market.upper() else ["EUR/USD"]),
            chart_enabled=args.chart or args.scan_watchlist,
            chart_auto_open=not args.no_open if args.chart else False,
            lookback_bars=args.bars,
            start_date=args.start_date,
            end_date=args.end_date,
            evaluate_strategy=args.evaluate,
            risk_reward_ratio=args.risk_reward,
        )

        notifiers = []
        if args.send_telegram and TELEGRAM_BOT_TOKEN and CHAT_IDS:
            notifiers.append(TelegramNotifier(bot_token=TELEGRAM_BOT_TOKEN, chat_ids=CHAT_IDS))

        algo = AlgoTrade(config=config, provider=provider, notifiers=notifiers)
        print("=" * 70)
        print(f"🚀 INITIALIZING ALGOTRADE PROCESS: {algo.algo_name}")
        print(f"🆔 Process ID:  {algo.algo_id}")
        print(f"🌐 Market:      {algo.config.market}")
        print(f"⏱ Timeframe:   {algo.config.timeframe}")
        if algo.config.start_date or algo.config.end_date:
            print(f"🗓 Date Range:  {algo.config.start_date or 'Earliest'} -> {algo.config.end_date or 'Latest'}")
        if algo.config.evaluate_strategy:
            print(f"🔬 Mode:        HISTORICAL STRATEGY EVALUATION (Risk:Reward = 1:{algo.config.risk_reward_ratio})")
        print(f"📋 Symbols:     {', '.join(algo.config.symbols)}")
        print("=" * 70)

        results = algo.run_cycle()
        print(f"\n✅ Completed cycle {algo.cycle_count} across {len(algo.config.symbols)} symbol(s).")
        for res in results:
            sym = res["symbol"]
            eval_report = res.get("evaluation")
            if eval_report:
                print("\n" + eval_report.to_summary_string())
            else:
                sig = res.get("signal")
                if sig:
                    print(f"  🚨 SIGNAL on {sym}: {sig.direction.value} ({sig.pattern}) at {sig.price:.2f}")
                else:
                    tr = res.get("trend", {})
                    print(f"  ℹ️ {sym}: Trend={tr.get('trend', 'N/A')} | Price={tr.get('current_price', 'N/A')}")
            if res.get("chart_path"):
                print(f"     Chart: {res['chart_path']}")

        metrics = algo.get_metrics()
        print(f"\n📊 Metrics: Generated={metrics['signals_generated']}, Dispatched={metrics['signals_dispatched']}, Errors={metrics['error_count']}")
        algo.close()
        return

    # 5. Single Stock / Index / Symbol Operations
    target_name = (args.stock or args.index or args.symbol or "").upper().strip()
    if not target_name:
        print("⚠️ Please specify a target using --stock <SYM>, --index <IDX>, or --symbol <SYM>.")
        return

    # Fetch candles via provider with computation-saving cache & optional date range
    df = provider.get_cached_candles(
        target_name,
        timeframe=args.timeframe,
        lookback_bars=args.bars,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    if df is None or df.empty:
        print(f"❌ Could not extract data for {target_name}. Check connectivity or symbol name.")
        return

    # Historical Strategy Evaluation / Backtesting
    if args.evaluate:
        print(f"\n🔬 Running Historical Strategy Evaluation on {target_name} [{args.timeframe}]...")
        if args.start_date or args.end_date:
            print(f"🗓 Evaluation Period: {args.start_date or 'Earliest'} -> {args.end_date or 'Latest'}")
        evaluator = StrategyEvaluator(risk_reward_ratio=args.risk_reward)
        report = evaluator.evaluate(
            df,
            symbol=target_name,
            timeframe=args.timeframe,
            start_date=args.start_date,
            end_date=args.end_date,
        )
        print("\n" + report.to_summary_string() + "\n")
        if args.chart:
            chart_p = create_interactive_chart(
                df,
                symbol=target_name,
                lookback_bars=args.bars,
                auto_open=not args.no_open,
            )
            if chart_p:
                print(f"✅ Historical Chart saved: {chart_p}")
        return

    # Trend Analysis
    if args.trend:
        print(f"\n📈 Trend Analysis for {target_name} [{args.timeframe}]:")
        tr = analyze_trend(df, symbol=target_name, timeframe=args.timeframe, lookback_bars=args.bars)
        print("-" * 75)
        print(f"Symbol:        {tr['symbol']}")
        print(f"Current Price: {tr.get('current_price', 'N/A')}")
        print(f"Trend State:   {tr.get('trend', 'N/A')}")
        print(f"EMA 20:        {tr.get('ema20', 'N/A')} | EMA 50: {tr.get('ema50', 'N/A')}")
        print(f"Support Level: {tr.get('support', 'N/A')} (Distance: -{tr.get('dist_to_support_pct', 'N/A')}%)")
        print(f"Resistance:    {tr.get('resistance', 'N/A')} (Distance: +{tr.get('dist_to_resistance_pct', 'N/A')}%)")
        print(f"Window Change: {tr.get('window_change_pct', 'N/A')}%")
        print("-" * 75)
        print(f"Summary: {tr.get('summary', '')}\n")
        return

    # Pattern Audit
    if args.audit:
        print(f"\n🔍 Auditing Price Action Patterns for {target_name} [{args.timeframe}]...")
        patterns = scan_df_for_patterns(df)
        print(f"Total Bars Evaluated: {args.bars} | Total Setups Detected: {len(patterns)}")
        print("=" * 80)
        if not patterns:
            print("No patterns found in the evaluated window.")
        else:
            for idx, p in enumerate(patterns, 1):
                icon = "🟢 CALL" if p.get("direction") == "CALL" else "🔴 PUT "
                print(f"{idx:02d}. {icon} | {p['pattern']:22} | Level: {float(p['level']):10.2f} | Time: {p['pattern_time']}")
                print(f"    Reason: {p['reason']}")
        print("=" * 80 + "\n")
        return

    # Signal Evaluation
    if args.scan_signal:
        print(f"\n🎯 Evaluating Strategy Rules on {target_name} [{args.timeframe}]...")
        strategy = PDFPriceActionStrategy(scan_bars=8, lookback_sr=20)
        completed = df.iloc[:-1].copy()
        sig = strategy.evaluate(completed, symbol=target_name)
        if not sig:
            print(f"ℹ️ No confirmed setup for {target_name} at last completed candle close.")
        else:
            print("\n🚨 CONFIRMED ENTRY SIGNAL DETECTED 🚨")
            print(sig.to_alert_message(version_tag="TXCORE CLI"))
            chart_p = None
            if args.chart or args.send_telegram:
                chart_p = create_interactive_chart(
                    df,
                    symbol=target_name,
                    lookback_bars=args.bars,
                    signal=sig,
                    auto_open=not args.no_open,
                )
            if args.send_telegram and TELEGRAM_BOT_TOKEN and CHAT_IDS:
                notifier = TelegramNotifier(bot_token=TELEGRAM_BOT_TOKEN, chat_ids=CHAT_IDS)
                sent = notifier.send(sig.to_alert_message(version_tag="TXCORE CLI"), signal=sig, chart_path=chart_p)
                print(f"📡 Dispatched alert to Telegram: {'Success' if sent else 'Failed'}")
        print()
        return

    # Interactive Chart Generation
    if args.chart:
        print(f"\n📊 Generating Interactive TradingView Chart for {target_name} [{args.timeframe}] ({args.bars} bars)...")
        chart_p = create_interactive_chart(
            df,
            symbol=target_name,
            lookback_bars=args.bars,
            auto_open=not args.no_open,
        )
        if chart_p:
            print(f"✅ Chart saved: {chart_p}")
            if not args.no_open:
                print("🌐 Opened in default web browser.")
            if args.send_telegram and TELEGRAM_BOT_TOKEN and CHAT_IDS:
                notifier = TelegramNotifier(bot_token=TELEGRAM_BOT_TOKEN, chat_ids=CHAT_IDS)
                notifier.send_document(chart_p, caption=f"📊 Interactive Chart: {target_name}")
                print("📡 Chart document uploaded to Telegram.")
        return

    # Standard Candlestick Extraction Output
    print(f"\n✅ Extracted {len(df)} bars for {target_name} [{args.timeframe}]:")
    print("-" * 75)
    sample = df.tail(10)
    print(sample.to_string(index=False))
    print("-" * 75)
    latest = df.iloc[-1]
    first = df.iloc[0]
    pct_move = ((latest['close'] - first['open']) / first['open']) * 100
    print(f"Summary: First Open: {first['open']:.2f} | Latest Close: {latest['close']:.2f} | Range Return: {pct_move:+.2f}%\n")

    if args.csv:
        df.to_csv(args.csv, index=False)
        print(f"💾 Saved to CSV: {args.csv}")


if __name__ == "__main__":
    main()
