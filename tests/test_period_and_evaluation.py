"""
tests.test_period_and_evaluation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit and integration tests for:
  1. Period parsing, timeframe conversions, bar estimation, and date range filtering.
  2. Historical strategy walk-forward evaluation (StrategyEvaluator, StrategyEvaluationReport, TradeRecord).
  3. AlgoTrade date range integration and backtesting mode.
"""

from datetime import datetime, timezone, timedelta
import pandas as pd
import pytest

from txcore.analysis.period import (
    parse_datetime,
    timeframe_to_seconds,
    estimate_required_bars,
    filter_candles_by_date,
)
from txcore.strategies.evaluator import (
    StrategyEvaluator,
    StrategyEvaluationReport,
    TradeRecord,
)
from txcore.strategies.pdf_price_action import PDFPriceActionStrategy
from txcore.algotrade import AlgoTrade, AlgoTradeConfig
from txcore.providers.base import BaseDataProvider


class MockDataProvider(BaseDataProvider):
    """Synthetic in-memory provider for deterministic testing."""

    def __init__(self, df: pd.DataFrame):
        super().__init__(cache_ttl_seconds=10.0)
        self.mock_df = df

    def get_candles(self, symbol, timeframe="5m", lookback_bars=100, start_date=None, end_date=None, **kwargs):
        df = self.mock_df.copy()
        if start_date or end_date:
            df = filter_candles_by_date(df, start_date=start_date, end_date=end_date)
        return df.tail(lookback_bars).reset_index(drop=True)


def generate_synthetic_candles(num_bars: int = 60, base_price: float = 1000.0, start_time: datetime = None) -> pd.DataFrame:
    """Creates synthetic OHLCV candles spaced 5 minutes apart."""
    if start_time is None:
        start_time = datetime(2026, 9, 1, 9, 15, tzinfo=timezone.utc)

    records = []
    price = base_price
    for i in range(num_bars):
        t = start_time + timedelta(minutes=5 * i)
        # Create subtle price changes
        o = price
        h = o + 2.0
        l = o - 2.0
        c = o + 0.5
        records.append({
            "time": t,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": 1500.0,
        })
        price = c
    return pd.DataFrame(records)


# =============================================================================
# 1. PERIOD PARSING & ESTIMATION TESTS
# =============================================================================

def test_parse_datetime():
    # None handling
    assert parse_datetime(None) is None

    # Already timezone-aware datetime
    dt_aware = datetime(2026, 9, 1, 9, 15, tzinfo=timezone.utc)
    assert parse_datetime(dt_aware) == dt_aware

    # Naive datetime
    dt_naive = datetime(2026, 9, 1, 9, 15)
    parsed = parse_datetime(dt_naive)
    assert parsed.tzinfo == timezone.utc
    assert parsed.hour == 9

    # ISO string
    parsed_iso = parse_datetime("2026-09-01T09:15:00Z")
    assert parsed_iso == dt_aware

    # Date-only string
    parsed_date = parse_datetime("2026-09-01")
    assert parsed_date == datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)

    # Standard space-separated datetime string
    parsed_space = parse_datetime("2026-09-01 09:15:00")
    assert parsed_space == dt_aware


def test_timeframe_to_seconds():
    assert timeframe_to_seconds("1m") == 60
    assert timeframe_to_seconds("3m") == 180
    assert timeframe_to_seconds("5m") == 300
    assert timeframe_to_seconds("15m") == 900
    assert timeframe_to_seconds("30m") == 1800
    assert timeframe_to_seconds("1h") == 3600
    assert timeframe_to_seconds("4h") == 14400
    assert timeframe_to_seconds("1d") == 86400
    assert timeframe_to_seconds("invalid") == 300  # Default fallback


def test_estimate_required_bars():
    start = datetime(2026, 9, 1, 9, 15, tzinfo=timezone.utc)
    end = datetime(2026, 9, 1, 10, 15, tzinfo=timezone.utc)  # 1 hour = 60 mins = 12 5-min bars
    estimated = estimate_required_bars(start, end, timeframe="5m")
    # buffer factor 1.25 gives ~15 bars
    assert estimated >= 12


def test_filter_candles_by_date():
    df = generate_synthetic_candles(num_bars=30)  # 30 bars * 5m = 150 minutes
    start = datetime(2026, 9, 1, 9, 30, tzinfo=timezone.utc)
    end = datetime(2026, 9, 1, 10, 30, tzinfo=timezone.utc)

    filtered = filter_candles_by_date(df, start_date=start, end_date=end)
    assert filtered is not None
    assert len(filtered) < len(df)
    assert filtered.iloc[0]["time"] >= start
    assert filtered.iloc[-1]["time"] <= end


# =============================================================================
# 2. HISTORICAL STRATEGY EVALUATOR TESTS
# =============================================================================

def test_strategy_evaluator_empty_or_short_df():
    evaluator = StrategyEvaluator()
    # Short dataframe (< 15 bars)
    df_short = generate_synthetic_candles(num_bars=10)
    report = evaluator.evaluate(df_short, symbol="TEST_SHORT")
    assert report.total_signals == 0
    assert report.win_rate_pct == 0.0
    assert report.trades == []


def test_strategy_evaluator_walk_forward_simulation():
    # Build a 25-bar dataframe designed to trigger a Bullish Engulfing setup
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=timezone.utc)
    bars = [
        # 16 warmup bars establishing support around 100.0
        (105.0, 106.0, 104.0, 104.5),
        (104.5, 105.0, 103.0, 103.5),
        (103.5, 104.0, 102.0, 102.5),
        (102.5, 103.0, 101.0, 101.5),
        (101.5, 102.0, 100.0, 100.5),  # Established support at 100.0
        (100.5, 102.0, 100.2, 101.5),
        (101.5, 102.5, 101.0, 102.0),
        (102.0, 103.0, 101.5, 102.5),
        (102.5, 103.5, 102.0, 103.0),
        (103.0, 104.0, 102.5, 103.5),
        (103.5, 104.5, 103.0, 104.0),
        (104.0, 105.0, 103.5, 104.5),
        (104.5, 105.0, 102.0, 102.5),
        (102.5, 103.0, 101.0, 101.5),
        (101.5, 102.0, 100.2, 100.5),  # Bar 14: Bearish near support
        (100.0, 103.5, 99.8, 103.0),   # Bar 15: Bullish Engulfing
        (103.0, 103.2, 99.9, 101.5),   # Bar 16: Retracement touches support & rejects
        # Future bars simulating a WIN (hitting target):
        (101.5, 107.0, 101.0, 106.5),  # Bar 17: Rallies sharply
        (106.5, 108.0, 105.5, 107.5),  # Bar 18
        (107.5, 109.0, 107.0, 108.5),  # Bar 19
        (108.5, 110.0, 108.0, 109.5),  # Bar 20
    ]

    data = []
    for idx, (o, h, l, c) in enumerate(bars):
        data.append({
            "time": t0 + timedelta(minutes=5 * idx),
            "open": float(o),
            "high": float(h),
            "low": float(l),
            "close": float(c),
            "volume": 2000.0,
        })
    df = pd.DataFrame(data)

    evaluator = StrategyEvaluator(risk_reward_ratio=1.5, max_holding_bars=5)
    report = evaluator.evaluate(df, symbol="RELIANCE", timeframe="5m")

    assert isinstance(report, StrategyEvaluationReport)
    assert report.total_bars == len(df)
    summary_text = report.to_summary_string()
    assert "HISTORICAL STRATEGY EVALUATION REPORT" in summary_text
    assert "Win Rate:" in summary_text


# =============================================================================
# 3. ALGOTRADE INTEGRATION & BACKTESTING MODE
# =============================================================================

def test_algotrade_historical_evaluation_mode():
    df = generate_synthetic_candles(num_bars=40)
    provider = MockDataProvider(df)

    config = AlgoTradeConfig(
        algo_name="HistoricalTester",
        market="INDIAN_EQUITY",
        timeframe="5m",
        symbols=["TCS"],
        evaluate_strategy=True,
        start_date="2026-09-01",
        end_date="2026-09-02",
        chart_enabled=False,
    )

    algo = AlgoTrade(config=config, provider=provider)
    assert algo.config.evaluate_strategy is True
    assert algo.config.start_date == "2026-09-01"

    # Execute single symbol pipeline in evaluation mode
    result = algo.execute_pipeline("TCS")
    assert result is not None
    assert result["symbol"] == "TCS"
    assert "evaluation" in result
    assert isinstance(result["evaluation"], StrategyEvaluationReport)

    # Directly call evaluate_historical
    direct_report = algo.evaluate_historical("TCS")
    assert isinstance(direct_report, StrategyEvaluationReport)
    assert direct_report.symbol == "TCS"

    algo.close()
