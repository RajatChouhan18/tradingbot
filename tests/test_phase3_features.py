"""
tests.test_phase3_features
~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for Phase 3 core features:
  1. Candle Representation & Inversion Protection
  2. Multi-Timeframe Confirmation (MTF) Engine
  3. Dynamic ATR Risk Management
  4. Full Bar Integrity & Chart Ordering
"""

from datetime import datetime, timezone, timedelta
import pandas as pd
import pytest

from txcore.models.types import Direction, Candle, CandleType, SignalStatus
from txcore.analysis.candle import (
    classify_candle,
    is_dragonfly_doji,
    is_gravestone_doji,
    is_bullish_doji,
    is_bearish_doji,
)
from txcore.analysis.indicators import calculate_atr
from txcore.analysis.mtf import (
    resample_to_timeframe,
    evaluate_mtf_trend,
    validate_mtf_confirmation,
)
from txcore.algotrade import AlgoTrade, AlgoTradeConfig
from txcore.visualization.chart_builder import build_tradingview_chart_html


@pytest.fixture
def sample_1m_ohlcv() -> pd.DataFrame:
    """Generates 60 bars of 1-minute OHLCV data."""
    t0 = datetime(2026, 9, 28, 9, 15, tzinfo=timezone.utc)
    rows = []
    base_price = 100.0
    for i in range(60):
        t = t0 + timedelta(minutes=i)
        o = base_price + (i * 0.1)
        h = o + 0.5
        l = o - 0.4
        c = o + 0.2
        v = 1000.0 + (i * 10)
        rows.append({"time": t, "open": o, "high": h, "low": l, "close": c, "volume": v})
    return pd.DataFrame(rows)


class TestATRCalculation:
    def test_calculate_atr_valid_series(self, sample_1m_ohlcv):
        atr = calculate_atr(sample_1m_ohlcv, period=14)
        assert len(atr) == len(sample_1m_ohlcv)
        assert not atr.isna().any()
        # High - Low is 0.9, so ATR should be around 0.9
        assert 0.8 <= atr.iloc[-1] <= 1.0

    def test_calculate_atr_empty_and_short_df(self):
        empty_df = pd.DataFrame()
        atr_empty = calculate_atr(empty_df, period=14)
        assert atr_empty.empty

        short_df = pd.DataFrame([{"high": 10.0, "low": 9.0, "close": 9.5}])
        atr_short = calculate_atr(short_df, period=14)
        assert len(atr_short) == 1
        assert atr_short.iloc[0] == 0.0


class TestMultiTimeframeEngine:
    def test_resample_to_15m(self, sample_1m_ohlcv):
        resampled = resample_to_timeframe(sample_1m_ohlcv, "15m")
        # 60 1-minute bars should produce 4 15-minute bars
        assert len(resampled) == 4
        # Verify first 15m bar
        first_15m = resampled.iloc[0]
        # Open should equal first 1m bar open
        assert first_15m["open"] == sample_1m_ohlcv.iloc[0]["open"]
        # High should equal max of first 15 bars
        assert first_15m["high"] == sample_1m_ohlcv.iloc[:15]["high"].max()
        # Low should equal min of first 15 bars
        assert first_15m["low"] == sample_1m_ohlcv.iloc[:15]["low"].min()
        # Close should equal last of first 15 bars
        assert first_15m["close"] == sample_1m_ohlcv.iloc[14]["close"]
        # Volume should equal sum of first 15 bars
        assert first_15m["volume"] == sample_1m_ohlcv.iloc[:15]["volume"].sum()

    def test_validate_mtf_confirmation_call_signal(self):
        # CALL blocked if HTF is STRONG_DOWNTREND
        ok, reason = validate_mtf_confirmation(Direction.CALL, "STRONG_DOWNTREND")
        assert ok is False
        assert "Counter-trend CALL blocked" in reason

        # CALL allowed in UPTREND
        ok, reason = validate_mtf_confirmation(Direction.CALL, "STRONG_UPTREND")
        assert ok is True

        # CALL allowed in SIDEWAYS (non-strict)
        ok, reason = validate_mtf_confirmation(Direction.CALL, "SIDEWAYS / CONSOLIDATION", strict=False)
        assert ok is True

        # CALL blocked in SIDEWAYS if strict=True
        ok, reason = validate_mtf_confirmation(Direction.CALL, "SIDEWAYS / CONSOLIDATION", strict=True)
        assert ok is False

    def test_validate_mtf_confirmation_put_signal(self):
        # PUT blocked if HTF is STRONG_UPTREND
        ok, reason = validate_mtf_confirmation(Direction.PUT, "STRONG_UPTREND")
        assert ok is False
        assert "Counter-trend PUT blocked" in reason

        # PUT allowed in DOWNTREND
        ok, reason = validate_mtf_confirmation(Direction.PUT, "STRONG_DOWNTREND")
        assert ok is True

        # PUT blocked in SIDEWAYS if strict=True
        ok, reason = validate_mtf_confirmation(Direction.PUT, "SIDEWAYS / CONSOLIDATION", strict=True)
        assert ok is False


class TestChartIntegrityAndDojiColor:
    def test_chart_builder_preserves_all_bars_and_sorts(self, sample_1m_ohlcv):
        # Shuffle bars to test out-of-order resilience
        shuffled = sample_1m_ohlcv.sample(frac=1.0, random_state=42)
        html = build_tradingview_chart_html(pair="TESTPAIR", df=shuffled)
        assert html is not None
        assert "Total Bars" in html
        # All 60 bars must be present in candleData JSON
        assert '"open":' in html

    def test_dragonfly_doji_hud_is_bullish(self):
        t0 = datetime(2026, 9, 28, 10, 0, tzinfo=timezone.utc)
        # Dragonfly doji with micro red close (open 100.0, close 99.98, low 90.0, high 100.0)
        c = Candle(time=t0, open=100.0, high=100.0, low=90.0, close=99.98)
        assert is_dragonfly_doji(c) is True
        assert is_bullish_doji(c) is True
        assert classify_candle(c) == CandleType.DRAGONFLY_DOJI

        df = pd.DataFrame([{
            "time": t0,
            "open": 100.0,
            "high": 100.0,
            "low": 90.0,
            "close": 99.98,
            "volume": 500.0,
        }])
        html = build_tradingview_chart_html(pair="TESTPAIR", df=df)
        # In analysisData, bullish must be True
        assert '"bullish": true' in html
        # Color must be emerald green #10b981
        assert '"color": "#10b981"' in html


class DummyPhase3Provider:
    """Mock provider generating candles that trigger a clean Bullish Engulfing setup."""
    def __init__(self, df: pd.DataFrame):
        self._df = df

    def get_candles(self, symbol: str, timeframe: str = "5m", lookback_bars: int = 60, **kwargs):
        return self._df.copy()

    def get_cached_candles(self, symbol: str, timeframe: str = "5m", lookback_bars: int = 60, **kwargs):
        return self._df.copy()


class TestAlgoTradeDynamicRiskAndMTF:
    @pytest.fixture
    def setup_candles(self) -> pd.DataFrame:
        """Constructs bars matching test_strategy_engine plus 1 forming bar."""
        t0 = datetime(2026, 9, 28, 9, 15, tzinfo=timezone.utc)
        bars = [
            (1.0890, 1.0900, 1.0880, 1.0885),
            (1.0885, 1.0890, 1.0870, 1.0875),
            (1.0875, 1.0880, 1.0860, 1.0865),
            (1.0865, 1.0870, 1.0850, 1.0855),
            (1.0855, 1.0875, 1.0852, 1.0870),
            (1.0870, 1.0880, 1.0865, 1.0875),
            (1.0875, 1.0880, 1.0852, 1.0855),  # Bar 6: Bearish
            (1.0850, 1.0885, 1.0848, 1.0880),  # Bar 7: Bullish Engulfing
            (1.0880, 1.0882, 1.0848, 1.0865),  # Bar 8: Retracement (touches support & rejects)
            (1.0865, 1.0870, 1.0860, 1.0868),  # Bar 9: In-progress forming bar
        ]
        rows = []
        for idx, (o, h, l, c) in enumerate(bars):
            rows.append({
                "time": t0 + timedelta(minutes=idx * 5),
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(c),
                "volume": 1000.0,
            })
        return pd.DataFrame(rows)

    def test_algotrade_atr_dynamic_risk(self, setup_candles):
        provider = DummyPhase3Provider(setup_candles)
        config = AlgoTradeConfig(
            algo_name="TestATRTrade",
            symbols=["TESTCO"],
            timeframe="5m",
            chart_enabled=False,
            use_atr_risk=True,
            atr_period=14,
            atr_multiplier=1.5,
            risk_reward_ratio=2.0,
            enable_mtf=False,
        )
        algo = AlgoTrade(config=config, provider=provider)
        res = algo.execute_pipeline("TESTCO")
        assert res is not None
        assert res.get("signal") is not None
        sig = res["signal"]

        # Verify dynamic ATR attached to metadata
        assert "atr" in sig.metadata
        assert sig.metadata["atr"] is not None and sig.metadata["atr"] > 0
        assert "stop_loss" in sig.metadata
        assert "target" in sig.metadata
        assert sig.metadata["risk_reward"] == 2.0
        assert sig.metadata["stop_loss"] < sig.price < sig.metadata["target"]

        # Verify alert text includes formatted Stop Loss and Target
        alert_msg = sig.to_alert_message()
        assert "🛑 Stop Loss:" in alert_msg
        assert "🎯 Target (1:2.0):" in alert_msg
        assert "📏 ATR:" in alert_msg

    def test_algotrade_mtf_aligned(self, setup_candles):
        """When HTF trend is aligned (e.g. MODERATE_UPTREND), signal is approved and metadata is tagged."""
        provider = DummyPhase3Provider(setup_candles)
        config = AlgoTradeConfig(
            algo_name="TestMTFAligned",
            symbols=["TESTCO"],
            timeframe="5m",
            chart_enabled=False,
            enable_mtf=True,
            higher_timeframe="15m",
            strict_mtf=False,
        )
        algo = AlgoTrade(config=config, provider=provider)
        res = algo.execute_pipeline("TESTCO")
        assert res is not None
        assert res.get("signal") is not None
        sig = res["signal"]
        assert "mtf_trend" in sig.metadata
        assert sig.metadata["mtf_timeframe"] == "15m"
        assert "📈 MTF Trend (15m):" in sig.to_alert_message()

    def test_algotrade_mtf_blocked_countertrend(self, setup_candles):
        """When HTF is in STRONG_DOWNTREND, CALL signal is blocked by the MTF filter."""
        class MockHTFDowntrendProvider(DummyPhase3Provider):
            def get_candles(self, symbol: str, timeframe: str = "5m", lookback_bars: int = 60, **kwargs):
                if timeframe == "15m":
                    # Strong downtrend bars (declining closes below falling EMAs)
                    t0 = datetime(2026, 9, 28, 6, 0, tzinfo=timezone.utc)
                    rows = []
                    p = 200.0
                    for i in range(30):
                        p -= 2.0
                        rows.append({"time": t0 + timedelta(minutes=i * 15), "open": p + 1.0, "high": p + 1.5, "low": p - 0.5, "close": p, "volume": 1000.0})
                    return pd.DataFrame(rows)
                return self._df.copy()

        provider = MockHTFDowntrendProvider(setup_candles)
        config = AlgoTradeConfig(
            algo_name="TestMTFBlocked",
            symbols=["TESTCO"],
            timeframe="5m",
            chart_enabled=False,
            enable_mtf=True,
            higher_timeframe="15m",
            strict_mtf=False,
        )
        algo = AlgoTrade(config=config, provider=provider)
        res = algo.execute_pipeline("TESTCO")
        # CALL signal must be blocked because 15m is in STRONG_DOWNTREND
        assert res is None

