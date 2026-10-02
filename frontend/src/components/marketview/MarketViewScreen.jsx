import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  Box,
  Card,
  Typography,
  Chip,
  Button,
  IconButton,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tooltip,
  CircularProgress,
  Grid,
  Menu,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Switch,
} from '@mui/material';
import {
  LineChart as ChartIcon,
  RefreshCw,
  Clock,
  Zap,
  Layers,
  Columns,
  Search,
  Activity,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  ChevronDown,
  Sliders,
  Calendar,
  Eye,
  Info,
  Maximize2,
} from 'lucide-react';
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  createSeriesMarkers,
  ColorType,
  CrosshairMode,
} from 'lightweight-charts';
import { api } from '../../api';

const MARKETS = [
  { id: 'INDIAN_EQUITY', label: 'NSE (India)', defaultSymbol: 'RELIANCE', exchange: 'NSE' },
  { id: 'US_EQUITY', label: 'US Equities', defaultSymbol: 'AAPL', exchange: 'NASDAQ' },
  { id: 'CRYPTO', label: 'Crypto (Binance)', defaultSymbol: 'BTCUSDT', exchange: 'BINANCE' },
  { id: 'FOREX', label: 'Forex (Global)', defaultSymbol: 'EURUSD', exchange: 'FX' },
  { id: 'MCX', label: 'MCX Commodities', defaultSymbol: 'CRUDEOIL', exchange: 'MCX' },
];

const TIMEFRAMES = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d', '1w', '1M'];

const DEFAULT_SYMBOLS_BY_MARKET = {
  INDIAN_EQUITY: [
    { symbol: 'RELIANCE', shortName: 'Reliance Industries Ltd', exchange: 'NSE' },
    { symbol: 'TCS', shortName: 'Tata Consultancy Services', exchange: 'NSE' },
    { symbol: 'INFY', shortName: 'Infosys Ltd', exchange: 'NSE' },
    { symbol: 'HDFCBANK', shortName: 'HDFC Bank Ltd', exchange: 'NSE' },
    { symbol: 'ICICIBANK', shortName: 'ICICI Bank Ltd', exchange: 'NSE' },
    { symbol: 'SBIN', shortName: 'State Bank of India', exchange: 'NSE' },
    { symbol: 'BHARTIARTL', shortName: 'Bharti Airtel Ltd', exchange: 'NSE' },
    { symbol: 'ITC', shortName: 'ITC Ltd', exchange: 'NSE' },
    { symbol: 'NIFTY', shortName: 'NIFTY 50 Benchmark Index', exchange: 'NSE' },
    { symbol: 'BANKNIFTY', shortName: 'NIFTY Bank Index', exchange: 'NSE' },
    { symbol: 'FINNIFTY', shortName: 'NIFTY Financial Services', exchange: 'NSE' },
    { symbol: 'MIDCPNIFTY', shortName: 'NIFTY Midcap Select', exchange: 'NSE' },
    { symbol: 'SENSEX', shortName: 'BSE SENSEX Index', exchange: 'BSE' },
    { symbol: 'INDIAVIX', shortName: 'India VIX Volatility Index', exchange: 'NSE' },
  ],
  US_EQUITY: [
    { symbol: 'AAPL', shortName: 'Apple Inc', exchange: 'NASDAQ' },
    { symbol: 'MSFT', shortName: 'Microsoft Corporation', exchange: 'NASDAQ' },
    { symbol: 'GOOGL', shortName: 'Alphabet Inc', exchange: 'NASDAQ' },
    { symbol: 'AMZN', shortName: 'Amazon.com Inc', exchange: 'NASDAQ' },
    { symbol: 'TSLA', shortName: 'Tesla Inc', exchange: 'NASDAQ' },
    { symbol: 'SPY', shortName: 'SPDR S&P 500 ETF Trust', exchange: 'NYSE' },
    { symbol: 'QQQ', shortName: 'Invesco QQQ Trust', exchange: 'NASDAQ' },
  ],
  CRYPTO: [
    { symbol: 'BTCUSDT', shortName: 'Bitcoin / USDT Spot', exchange: 'BINANCE' },
    { symbol: 'ETHUSDT', shortName: 'Ethereum / USDT Spot', exchange: 'BINANCE' },
    { symbol: 'SOLUSDT', shortName: 'Solana / USDT Spot', exchange: 'BINANCE' },
    { symbol: 'BNBUSDT', shortName: 'BNB / USDT Spot', exchange: 'BINANCE' },
    { symbol: 'XRPUSDT', shortName: 'Ripple / USDT Spot', exchange: 'BINANCE' },
  ],
  FOREX: [
    { symbol: 'EURUSD', shortName: 'Euro / US Dollar Spot', exchange: 'FX' },
    { symbol: 'GBPUSD', shortName: 'British Pound / US Dollar', exchange: 'FX' },
    { symbol: 'USDJPY', shortName: 'US Dollar / Japanese Yen', exchange: 'FX' },
    { symbol: 'USDINR', shortName: 'US Dollar / Indian Rupee', exchange: 'FX' },
  ],
  MCX: [
    { symbol: 'CRUDEOIL', shortName: 'Crude Oil Futures', exchange: 'MCX' },
    { symbol: 'GOLD', shortName: 'Gold 1KG Futures', exchange: 'MCX' },
    { symbol: 'SILVER', shortName: 'Silver 30KG Futures', exchange: 'MCX' },
    { symbol: 'NATURALGAS', shortName: 'Natural Gas Futures', exchange: 'MCX' },
    { symbol: 'COPPER', shortName: 'Copper Futures', exchange: 'MCX' },
  ],
};

const TIMEFRAME_OPTIONS = [
  {
    category: 'Intraday Minutes',
    items: [
      { value: '1m', label: '1m (1 Min)' },
      { value: '3m', label: '3m (3 Min)' },
      { value: '5m', label: '5m (5 Min)' },
      { value: '15m', label: '15m (15 Min)' },
      { value: '30m', label: '30m (30 Min)' },
    ],
  },
  {
    category: 'Hourly',
    items: [
      { value: '1h', label: '1h (1 Hour)' },
      { value: '2h', label: '2h (2 Hours)' },
      { value: '4h', label: '4h (4 Hours)' },
    ],
  },
  {
    category: 'Daily & Higher Ranges',
    items: [
      { value: '1d', label: '1d (1 Day)' },
      { value: '1w', label: '1w (1 Week)' },
      { value: '1M', label: '1M (1 Month)' },
      { value: '3M', label: '3M (3 Months)' },
      { value: '6M', label: '6M (6 Months)' },
      { value: '1Y', label: '1Y (1 Year)' },
      { value: '5Y', label: '5Y (5 Years)' },
    ],
  },
];

const OVERLAY_OPTIONS = [
  { id: 'EMA_9', label: 'EMA 9', color: '#38bdf8' },
  { id: 'EMA_21', label: 'EMA 21', color: '#a855f7' },
  { id: 'EMA_50', label: 'EMA 50', color: '#f59e0b' },
  { id: 'EMA_200', label: 'EMA 200', color: '#f43f5e' },
  { id: 'SMA_20', label: 'SMA 20', color: '#60a5fa' },
  { id: 'VWAP', label: 'VWAP', color: '#fbbf24' },
  { id: 'BB', label: 'Bollinger Bands (20, 2)', color: '#3b82f6' },
];

const CANDLESTICK_PATTERNS = [
  { id: 'ALL', label: 'All Detected Patterns' },
  { id: 'ENGULFING_BULLISH', label: 'Bullish Engulfing' },
  { id: 'ENGULFING_BEARISH', label: 'Bearish Engulfing' },
  { id: 'HAMMER', label: 'Hammer' },
  { id: 'INVERTED_HAMMER', label: 'Inverted Hammer' },
  { id: 'SHOOTING_STAR', label: 'Shooting Star' },
  { id: 'HANGING_MAN', label: 'Hanging Man' },
  { id: 'DOJI', label: 'Doji' },
  { id: 'DRAGONFLY_DOJI', label: 'Dragonfly Doji' },
  { id: 'GRAVESTONE_DOJI', label: 'Gravestone Doji' },
  { id: 'MORNING_STAR', label: 'Morning Star' },
  { id: 'EVENING_STAR', label: 'Evening Star' },
  { id: 'MARUBOZU_BULLISH', label: 'Bullish Marubozu' },
  { id: 'MARUBOZU_BEARISH', label: 'Bearish Marubozu' },
  { id: 'HARAMI_BULLISH', label: 'Bullish Harami' },
  { id: 'HARAMI_BEARISH', label: 'Bearish Harami' },
  { id: 'PIERCING_LINE', label: 'Piercing Line' },
  { id: 'DARK_CLOUD_COVER', label: 'Dark Cloud Cover' },
];

const getPrecision = (mkt) => (['CRYPTO', 'FOREX', 'MCX'].includes(mkt) ? 6 : 4);
const formatPrice = (price, mkt) => {
  if (price === null || price === undefined || isNaN(price)) return '---';
  return Number(price).toFixed(getPrecision(mkt));
};

export default function MarketViewScreen() {
  const [activeTab, setActiveTab] = useState('terminal'); // 'terminal', 'compare', 'history'
  
  // Market & Asset State
  const [selectedMarket, setSelectedMarket] = useState('INDIAN_EQUITY');
  const [symbol, setSymbol] = useState('RELIANCE');
  const [timeframe, setTimeframe] = useState('5m');
  const [mode, setMode] = useState('LIVE'); // 'LIVE' | 'HISTORICAL'
  const [lookback, setLookback] = useState(180);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [catalogSymbols, setCatalogSymbols] = useState(DEFAULT_SYMBOLS_BY_MARKET['INDIAN_EQUITY']);
  
  // Active Overlays (Clean default: EMA 9, EMA 21, VWAP)
  const [selectedOverlays, setSelectedOverlays] = useState(['EMA_9', 'EMA_21', 'VWAP']);
  const [overlayMenuAnchor, setOverlayMenuAnchor] = useState(null);

  // Dedicated Candlestick Patterns Filter
  const [selectedPatterns, setSelectedPatterns] = useState(['ALL']);
  const [patternMenuAnchor, setPatternMenuAnchor] = useState(null);

  // Response Data & Diagnostics State
  const [loading, setLoading] = useState(false);
  const [marketData, setMarketData] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  
  // Diagnostic Timings
  const [timings, setTimings] = useState({
    fetchMs: 0,
    renderMs: 0,
    totalMs: 0,
    barCount: 0,
    provider: 'N/A',
  });

  // Crosshair HUD State (Defaults to latest candle)
  const [hudData, setHudData] = useState(null);

  // Query History & Dedicated History Filter State (All by default)
  const [queryHistory, setQueryHistory] = useState([]);
  const [historyMarket, setHistoryMarket] = useState('ALL');
  const [historySymbol, setHistorySymbol] = useState('ALL');
  const [historyTimeframe, setHistoryTimeframe] = useState('ALL');

  // Side-by-Side Dual Comparison State
  const [compareA, setCompareA] = useState({ symbol: 'RELIANCE', market: 'INDIAN_EQUITY', timeframe: '5m' });
  const [compareB, setCompareB] = useState({ symbol: 'TCS', market: 'INDIAN_EQUITY', timeframe: '5m' });
  const [compareResultA, setCompareResultA] = useState(null);
  const [compareResultB, setCompareResultB] = useState(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareTimingsA, setCompareTimingsA] = useState({ fetchMs: 0, renderMs: 0, totalMs: 0, barCount: 0, provider: 'N/A' });
  const [compareTimingsB, setCompareTimingsB] = useState({ fetchMs: 0, renderMs: 0, totalMs: 0, barCount: 0, provider: 'N/A' });

  // Chart DOM & Instance Refs
  const chartContainerRef = useRef(null);
  const chartInstanceRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const markersPluginRef = useRef(null);
  const resizeObserverRef = useRef(null);

  const compareChartRefA = useRef(null);
  const compareChartRefB = useRef(null);
  const compareChartInstanceA = useRef(null);
  const compareChartInstanceB = useRef(null);

  // Main Data Fetcher
  const fetchData = useCallback(async (customParams = {}) => {
    const targetSymbol = (customParams.symbol || symbol || '').trim().toUpperCase();
    const targetMarket = customParams.market || selectedMarket;
    const targetTimeframe = customParams.timeframe || timeframe;
    const targetMode = customParams.mode || mode;
    const targetLookback = customParams.lookback !== undefined ? customParams.lookback : lookback;
    const targetOverlays = customParams.overlays !== undefined ? customParams.overlays : selectedOverlays;
    const targetPatterns = customParams.patterns !== undefined ? customParams.patterns : selectedPatterns;

    if (!targetSymbol) return;

    setLoading(true);
    setErrorMsg(null);
    const fetchStart = performance.now();

    try {
      const activeOverlayList = [...targetOverlays];
      if (targetPatterns.length > 0 && !activeOverlayList.includes('PATTERNS')) {
        activeOverlayList.push('PATTERNS');
      }

      const params = {
        symbol: targetSymbol,
        timeframe: targetTimeframe,
        market: targetMarket,
        mode: targetMode,
        lookback: targetMode === 'LIVE' ? targetLookback : undefined,
        startDate: targetMode === 'HISTORICAL' && startDate ? new Date(startDate).toISOString() : undefined,
        endDate: targetMode === 'HISTORICAL' && endDate ? new Date(endDate).toISOString() : undefined,
        overlays: activeOverlayList.join(','),
      };

      const res = await api.getMarketViewData(params);
      const fetchEnd = performance.now();
      const fetchLatency = Math.round(fetchEnd - fetchStart);

      setMarketData(res);

      // Record to history
      const historyEntry = {
        id: `REQ-${Date.now().toString().slice(-6)}`,
        symbol: res.symbol,
        market: res.market,
        timeframe: res.timeframe,
        bars: res.candles?.length || 0,
        provider: res.provider,
        price: res.liveQuote?.lastPrice ?? (res.candles?.length ? res.candles[res.candles.length - 1].close : 'N/A'),
        fetchLatency,
        timestamp: new Date().toLocaleTimeString(),
      };
      setQueryHistory((prev) => [historyEntry, ...prev.slice(0, 49)]);

      // Render chart
      renderLightweightChart(res, fetchLatency, targetPatterns);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to fetch market data from providers');
    } finally {
      setLoading(false);
    }
  }, [symbol, timeframe, selectedMarket, mode, lookback, startDate, endDate, selectedOverlays, selectedPatterns]);

  // Handle Market Switch (Terminal Chart only)
  const handleMarketChange = async (newMarket) => {
    setSelectedMarket(newMarket);
    let chosenSymbol = 'RELIANCE';
    try {
      const res = await api.getCatalogSymbols({ market: newMarket, activeOnly: true, limit: 100 });
      if (Array.isArray(res) && res.length > 0) {
        setCatalogSymbols(res);
        chosenSymbol = res[0].symbol;
      } else {
        const fallbackList = DEFAULT_SYMBOLS_BY_MARKET[newMarket] || [];
        setCatalogSymbols(fallbackList);
        chosenSymbol = fallbackList[0]?.symbol || 'RELIANCE';
      }
    } catch (err) {
      console.warn('Failed to load dynamic catalog symbols for market:', newMarket, err);
      const fallbackList = DEFAULT_SYMBOLS_BY_MARKET[newMarket] || [];
      setCatalogSymbols(fallbackList);
      chosenSymbol = fallbackList[0]?.symbol || 'RELIANCE';
    }
    setSymbol(chosenSymbol);
    fetchData({ symbol: chosenSymbol, market: newMarket });
  };

  // Handle Symbol Select (Terminal Chart only)
  const handleSymbolChange = (newSymbol) => {
    setSymbol(newSymbol);
    fetchData({ symbol: newSymbol });
  };

  // Handle Timeframe Change (Terminal Chart only)
  const handleTimeframeChange = (tf) => {
    setTimeframe(tf);
    if (['3M', '6M', '1Y', '5Y'].includes(tf)) {
      const now = new Date();
      const past = new Date();
      if (tf === '3M') past.setMonth(now.getMonth() - 3);
      else if (tf === '6M') past.setMonth(now.getMonth() - 6);
      else if (tf === '1Y') past.setFullYear(now.getFullYear() - 1);
      else if (tf === '5Y') past.setFullYear(now.getFullYear() - 5);

      const sDate = past.toISOString().split('T')[0];
      const eDate = now.toISOString().split('T')[0];
      setStartDate(sDate);
      setEndDate(eDate);
      setMode('HISTORICAL');
      fetchData({ timeframe: '1d', mode: 'HISTORICAL', startDate: sDate, endDate: eDate });
    } else {
      fetchData({ timeframe: tf });
    }
  };

  // Dual View Individual Side A / Side B Change Handlers
  const handleCompareAChange = (field, value) => {
    const next = { ...compareA, [field]: value };
    if (field === 'market') {
      const list = DEFAULT_SYMBOLS_BY_MARKET[value] || [];
      next.symbol = list[0]?.symbol || 'RELIANCE';
    }
    setCompareA(next);
    handleRunComparison({
      symbolA: next.symbol,
      marketA: next.market,
      timeframeA: next.timeframe,
    });
  };

  const handleCompareBChange = (field, value) => {
    const next = { ...compareB, [field]: value };
    if (field === 'market') {
      const list = DEFAULT_SYMBOLS_BY_MARKET[value] || [];
      next.symbol = list[0]?.symbol || 'TCS';
    }
    setCompareB(next);
    handleRunComparison({
      symbolB: next.symbol,
      marketB: next.market,
      timeframeB: next.timeframe,
    });
  };

  // Initial Data & Dynamic User Configuration Hydration on Mount
  useEffect(() => {
    // 1. Fetch User Isolated Preferences
    api.getUserTerminalConfig()
      .then((cfg) => {
        if (cfg && cfg.default_market) {
          const mkt = cfg.default_market;
          const sym = cfg.default_symbol || (DEFAULT_SYMBOLS_BY_MARKET[mkt]?.[0]?.symbol || 'RELIANCE');
          const tf = cfg.default_timeframe || '5m';
          const ovs = cfg.default_overlays ? cfg.default_overlays.split(',').map((s) => s.trim()) : ['EMA_9', 'EMA_21', 'VWAP'];
          const pats = cfg.default_patterns ? cfg.default_patterns.split(',').map((s) => s.trim()) : ['ALL'];

          setSelectedMarket(mkt);
          setSymbol(sym);
          setTimeframe(tf);
          setSelectedOverlays(ovs);
          setSelectedPatterns(pats);
          fetchData({ market: mkt, symbol: sym, timeframe: tf, overlays: ovs, patterns: pats });
        } else {
          fetchData();
        }
      })
      .catch(() => {
        fetchData();
      });

    // 2. Load Catalog Directory
    api.getCatalogSymbols({ market: selectedMarket, activeOnly: true, limit: 100 })
      .then((res) => {
        if (Array.isArray(res) && res.length > 0) {
          setCatalogSymbols(res);
        }
      })
      .catch((err) => console.warn('Failed to load initial catalog symbols:', err));
  }, []);

  // Real-Time Fast Live Streaming Chart Poller (Updates Active Candle Bar, Spot Price and Diagnostic Bar on every tick)
  useEffect(() => {
    if (mode !== 'LIVE' || activeTab !== 'terminal') return;

    let isSubscribed = true;
    const liveInterval = setInterval(async () => {
      const pollStart = performance.now();
      try {
        const liveRes = await api.getMarketViewData({
          symbol,
          timeframe,
          market: selectedMarket,
          mode: 'LIVE',
          lookback: 10,
        });

        if (!isSubscribed || !liveRes?.candles?.length) return;
        const pollFetchEnd = performance.now();
        const pollFetchLatencyMs = Math.round(pollFetchEnd - pollStart);

        // 1. Update MarketData spot and quote state
        setMarketData((prev) => {
          if (!prev) return liveRes;
          return {
            ...prev,
            liveQuote: liveRes.liveQuote || prev.liveQuote,
            status: liveRes.status || prev.status,
            candles: liveRes.candles?.length ? [...prev.candles.slice(0, -liveRes.candles.length), ...liveRes.candles] : prev.candles,
          };
        });

        // 2. Incrementally update latest candle bar on chart canvas
        const renderStart = performance.now();
        if (candleSeriesRef.current && liveRes.candles.length > 0) {
          const rawBars = liveRes.candles.map((c) => ({
            time: Math.floor(new Date(c.timestamp).getTime() / 1000),
            open: c.open,
            high: c.high,
            low: c.low,
            close: c.close,
            volume: c.volume,
          }));

          // Deduplicate by time and sort ascending
          const barMap = new Map();
          rawBars.forEach((b) => barMap.set(b.time, b));
          const latestBars = Array.from(barMap.values()).sort((a, b) => a.time - b.time);

          latestBars.forEach((bar) => {
            try {
              candleSeriesRef.current.update(bar);
              if (volumeSeriesRef.current) {
                volumeSeriesRef.current.update({
                  time: bar.time,
                  value: bar.volume,
                  color: bar.close >= bar.open ? 'rgba(50, 215, 75, 0.45)' : 'rgba(255, 69, 58, 0.45)',
                });
              }
            } catch (updateErr) {
              // Ignore occasional out-of-order tick
            }
          });

          // Update HUD to latest bar
          const latest = latestBars[latestBars.length - 1];
          const prevBar = latestBars.length > 1 ? latestBars[latestBars.length - 2] : latest;
          const change = latest.close - prevBar.close;
          const changePct = prevBar.close ? (change / prevBar.close) * 100 : 0;
          setHudData({
            time: new Date(latest.time * 1000).toLocaleString(),
            open: latest.open,
            high: latest.high,
            low: latest.low,
            close: latest.close,
            change,
            changePct,
            volume: latest.volume,
            isLatest: true,
          });
        }
        const renderEnd = performance.now();
        const renderLatencyMs = Math.max(1, Math.round(renderEnd - renderStart));

        // 3. Update Diagnostic Bar Timings on each polling completion
        setTimings((prev) => ({
          fetchMs: pollFetchLatencyMs,
          renderMs: renderLatencyMs,
          totalMs: pollFetchLatencyMs + renderLatencyMs,
          barCount: prev.barCount || 120,
          provider: liveRes.provider || prev.provider || 'TRADINGVIEW',
        }));
      } catch (e) {
        // Polling error catch
      }
    }, 1000); // 1.0s fast real-time streaming interval

    return () => {
      isSubscribed = false;
      clearInterval(liveInterval);
    };
  }, [mode, activeTab, symbol, timeframe, selectedMarket]);

  // Fit Chart Helper
  const handleFitChart = () => {
    if (chartInstanceRef.current) {
      chartInstanceRef.current.timeScale().fitContent();
    }
  };

  // Lightweight Charts Renderer with Strict Institutional Asset Precision
  const renderLightweightChart = (data, fetchLatencyMs, activePatterns = selectedPatterns, activeOverlays = selectedOverlays) => {
    if (!chartContainerRef.current || !data?.candles?.length) return;

    const renderStart = performance.now();
    const activeMarket = data.market || selectedMarket;
    const prec = getPrecision(activeMarket);
    const minPriceMove = prec === 6 ? 0.000001 : 0.0001;

    // Clean previous observer and chart instance
    if (resizeObserverRef.current) {
      resizeObserverRef.current.disconnect();
      resizeObserverRef.current = null;
    }
    if (chartInstanceRef.current) {
      chartInstanceRef.current.remove();
      chartInstanceRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
      markersPluginRef.current = null;
    }

    const container = chartContainerRef.current;
    const chart = createChart(container, {
      autoSize: true,
      height: 500,
      layout: {
        background: { type: ColorType.Solid, color: '#1E1E1E' },
        textColor: '#98989D',
        fontSize: 11,
        fontFamily: "'JetBrains Mono', monospace",
      },
      grid: {
        vertLines: { color: '#2C2C2E' },
        horzLines: { color: '#2C2C2E' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: '#2C2C2E',
        scaleMargins: {
          top: 0.1,
          bottom: 0.22,
        },
      },
      timeScale: {
        borderColor: '#2C2C2E',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartInstanceRef.current = chart;

    // 1. Candlestick Series with Exact Decimal Precision
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#32D74B',
      downColor: '#FF453A',
      borderVisible: false,
      wickUpColor: '#32D74B',
      wickDownColor: '#FF453A',
      priceFormat: {
        type: 'price',
        precision: prec,
        minMove: minPriceMove,
      },
    });
    candleSeriesRef.current = candleSeries;

    // Format candle records for Lightweight Charts (timestamp in unix seconds)
    const formattedCandles = data.candles.map((c) => {
      const timeSec = Math.floor(new Date(c.timestamp).getTime() / 1000);
      return {
        time: timeSec,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
        volume: c.volume,
      };
    });

    // Sort chronologically ascending & deduplicate times
    const candleMap = new Map();
    formattedCandles.forEach((c) => candleMap.set(c.time, c));
    const sortedCandles = Array.from(candleMap.values()).sort((a, b) => a.time - b.time);
    candleSeries.setData(sortedCandles);

    // Default HUD to latest candle
    if (sortedCandles.length > 0) {
      const latest = sortedCandles[sortedCandles.length - 1];
      const prev = sortedCandles.length > 1 ? sortedCandles[sortedCandles.length - 2] : latest;
      const change = latest.close - prev.close;
      const changePct = prev.close ? (change / prev.close) * 100 : 0;
      setHudData({
        time: new Date(latest.time * 1000).toLocaleString(),
        open: latest.open,
        high: latest.high,
        low: latest.low,
        close: latest.close,
        change,
        changePct,
        volume: latest.volume,
        isLatest: true,
      });
    }

    // 2. Volume Histogram Overlay Series
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });
    volumeSeriesRef.current = volumeSeries;

    chart.priceScale('volume').applyOptions({
      scaleMargins: {
        top: 0.82,
        bottom: 0,
      },
    });

    const volumeData = sortedCandles.map((c) => ({
      time: c.time,
      value: c.volume,
      color: c.close >= c.open ? 'rgba(50, 215, 75, 0.45)' : 'rgba(255, 69, 58, 0.45)',
    }));
    volumeSeries.setData(volumeData);

    // 3. Technical Overlays Lines (Using overlays dictionary from ProviderTechnicals)
    const overlaysDict = data.technicals?.overlays || {};

    const addLineOverlay = (seriesName, color, values) => {
      if (!values || !values.length) return;
      const lineSeries = chart.addSeries(LineSeries, {
        color,
        lineWidth: 1.5,
        title: seriesName,
        priceLineVisible: false,
        priceFormat: {
          type: 'price',
          precision: prec,
          minMove: minPriceMove,
        },
      });

      const linePoints = [];
      data.candles.forEach((c, idx) => {
        const val = values[idx];
        if (val !== null && val !== undefined && !isNaN(val)) {
          linePoints.push({
            time: Math.floor(new Date(c.timestamp).getTime() / 1000),
            value: Number(val),
          });
        }
      });
      const lineMap = new Map();
      linePoints.forEach((p) => lineMap.set(p.time, p));
      lineSeries.setData(Array.from(lineMap.values()).sort((a, b) => a.time - b.time));
    };

    if (activeOverlays.includes('EMA_9')) addLineOverlay('EMA 9', '#38bdf8', overlaysDict['EMA_9']);
    if (activeOverlays.includes('EMA_21')) addLineOverlay('EMA 21', '#a855f7', overlaysDict['EMA_21']);
    if (activeOverlays.includes('EMA_50')) addLineOverlay('EMA 50', '#f59e0b', overlaysDict['EMA_50']);
    if (activeOverlays.includes('EMA_200')) addLineOverlay('EMA 200', '#f43f5e', overlaysDict['EMA_200']);
    if (activeOverlays.includes('SMA_20')) addLineOverlay('SMA 20', '#60a5fa', overlaysDict['SMA_20']);
    if (activeOverlays.includes('VWAP')) addLineOverlay('VWAP', '#fbbf24', overlaysDict['VWAP']);
    if (activeOverlays.includes('BB')) {
      addLineOverlay('BB Upper', '#3b82f6', overlaysDict['BB_UPPER']);
      addLineOverlay('BB Lower', '#3b82f6', overlaysDict['BB_LOWER']);
    }

    // 4. Candlestick Pattern Markers (Filtered by activePatterns)
    if (activePatterns.length > 0 && data.technicals?.patterns?.length) {
      const markers = [];
      data.technicals.patterns.forEach((p) => {
        // Filter by pattern selection
        if (!activePatterns.includes('ALL') && !activePatterns.includes(p.pattern)) {
          return;
        }

        const timeSec = Math.floor(new Date(p.timestamp).getTime() / 1000);
        const sentiment = p.sentiment || 'NEUTRAL';
        const isBullish = sentiment === 'BULLISH';
        const isBearish = sentiment === 'BEARISH';
        
        if (isBullish || isBearish) {
          markers.push({
            time: timeSec,
            position: isBullish ? 'belowBar' : 'aboveBar',
            color: isBullish ? '#32D74B' : '#FF453A',
            shape: isBullish ? 'arrowUp' : 'arrowDown',
            text: (p.pattern || 'Pattern').replace(/_/g, ' '),
          });
        }
      });
      // Sort markers chronologically
      markers.sort((a, b) => a.time - b.time);
      if (markers.length > 0) {
        markersPluginRef.current = createSeriesMarkers(candleSeries, markers);
      }
    }

    // 5. Crosshair HUD Listener (Updates OHLC in real time on hover)
    chart.subscribeCrosshairMove((param) => {
      if (
        param.point === undefined ||
        !param.time ||
        param.point.x < 0 ||
        param.point.x > container.clientWidth ||
        param.point.y < 0 ||
        param.point.y > 500
      ) {
        // Reset to latest candle
        if (sortedCandles.length > 0) {
          const latest = sortedCandles[sortedCandles.length - 1];
          const prev = sortedCandles.length > 1 ? sortedCandles[sortedCandles.length - 2] : latest;
          const change = latest.close - prev.close;
          const changePct = prev.close ? (change / prev.close) * 100 : 0;
          setHudData({
            time: new Date(latest.time * 1000).toLocaleString(),
            open: latest.open,
            high: latest.high,
            low: latest.low,
            close: latest.close,
            change,
            changePct,
            volume: latest.volume,
            isLatest: true,
          });
        }
      } else {
        const candlePoint = param.seriesData.get(candleSeries);
        const volumePoint = param.seriesData.get(volumeSeries);
        if (candlePoint) {
          const change = candlePoint.close - candlePoint.open;
          const changePct = candlePoint.open ? (change / candlePoint.open) * 100 : 0;
          setHudData({
            time: new Date(param.time * 1000).toLocaleString(),
            open: candlePoint.open,
            high: candlePoint.high,
            low: candlePoint.low,
            close: candlePoint.close,
            change,
            changePct,
            volume: volumePoint?.value ?? 0,
            isLatest: false,
          });
        }
      }
    });

    // Auto-fit content on initial render
    chart.timeScale().fitContent();

    // Responsive auto-fit observer
    const observer = new ResizeObserver(() => {
      if (chartInstanceRef.current && container) {
        chartInstanceRef.current.timeScale().fitContent();
      }
    });
    observer.observe(container);
    resizeObserverRef.current = observer;

    const renderEnd = performance.now();
    const renderLatency = Math.round(renderEnd - renderStart);
    const totalLatency = fetchLatencyMs + renderLatency;

    setTimings({
      fetchMs: fetchLatencyMs,
      renderMs: renderLatency,
      totalMs: totalLatency,
      barCount: sortedCandles.length,
      provider: data.provider || 'REGISTRY',
    });
  };


  // Side-by-Side Compare Runner
  const handleRunComparison = async (param = false) => {
    const isBackground = typeof param === 'boolean' ? param : !!param?.isBackground;
    const sA = param?.symbolA || compareA.symbol;
    const mA = param?.marketA || compareA.market;
    const tA = param?.timeframeA || compareA.timeframe;
    const sB = param?.symbolB || compareB.symbol;
    const mB = param?.marketB || compareB.market;
    const tB = param?.timeframeB || compareB.timeframe;

    if (!isBackground) setCompareLoading(true);
    const fetchStart = performance.now();
    try {
      const [resA, resB] = await Promise.all([
        api.getMarketViewData({
          symbol: sA,
          market: mA,
          timeframe: tA,
          lookback: 120,
        }),
        api.getMarketViewData({
          symbol: sB,
          market: mB,
          timeframe: tB,
          lookback: 120,
        }),
      ]);
      const fetchEnd = performance.now();
      const fetchLatencyMs = Math.round(fetchEnd - fetchStart);

      setCompareResultA(resA);
      setCompareResultB(resB);
      renderCompareCharts(resA, resB, fetchLatencyMs);
    } catch (err) {
      if (!isBackground) console.warn(`Comparison failed: ${err.message}`);
    } finally {
      if (!isBackground) setCompareLoading(false);
    }
  };

  // Auto-run comparison & Live stream interval when in compare tab
  useEffect(() => {
    if (activeTab === 'compare') {
      handleRunComparison();

      let intervalId = null;
      if (mode === 'LIVE') {
        intervalId = setInterval(() => {
          handleRunComparison(true);
        }, 2500);
      }
      return () => {
        if (intervalId) clearInterval(intervalId);
      };
    }
  }, [activeTab, mode, compareA.symbol, compareA.market, compareA.timeframe, compareB.symbol, compareB.market, compareB.timeframe]);

  const renderCompareCharts = (dataA, dataB, fetchLatencyMs = 0) => {
    const renderStartA = performance.now();
    if (compareChartInstanceA.current) {
      compareChartInstanceA.current.remove();
      compareChartInstanceA.current = null;
    }
    if (compareChartInstanceB.current) {
      compareChartInstanceB.current.remove();
      compareChartInstanceB.current = null;
    }

    if (compareChartRefA.current && dataA?.candles?.length) {
      const precA = getPrecision(dataA.market || compareA.market);
      const minMoveA = precA === 6 ? 0.000001 : 0.0001;
      const chartA = createChart(compareChartRefA.current, {
        autoSize: true,
        height: 380,
        layout: { background: { type: ColorType.Solid, color: '#1E1E1E' }, textColor: '#98989D', fontSize: 10, fontFamily: "'JetBrains Mono', monospace" },
        grid: { vertLines: { color: '#2C2C2E' }, horzLines: { color: '#2C2C2E' } },
        timeScale: { timeVisible: true },
        rightPriceScale: { borderColor: '#2C2C2E' },
      });
      compareChartInstanceA.current = chartA;
      const sA = chartA.addSeries(CandlestickSeries, {
        upColor: '#32D74B',
        downColor: '#FF453A',
        priceFormat: { type: 'price', precision: precA, minMove: minMoveA },
      });
      const cA = dataA.candles.map((c) => ({ time: Math.floor(new Date(c.timestamp).getTime() / 1000), open: c.open, high: c.high, low: c.low, close: c.close }));
      const sortedA = cA.sort((a, b) => a.time - b.time);
      sA.setData(sortedA);
      chartA.timeScale().fitContent();

      const renderEndA = performance.now();
      const renderMsA = Math.round(renderEndA - renderStartA);
      setCompareTimingsA({
        fetchMs: fetchLatencyMs,
        renderMs: renderMsA,
        totalMs: fetchLatencyMs + renderMsA,
        barCount: sortedA.length,
        provider: dataA.provider || 'TRADINGVIEW',
      });
    }

    const renderStartB = performance.now();
    if (compareChartRefB.current && dataB?.candles?.length) {
      const precB = getPrecision(dataB.market || compareB.market);
      const minMoveB = precB === 6 ? 0.000001 : 0.0001;
      const chartB = createChart(compareChartRefB.current, {
        autoSize: true,
        height: 380,
        layout: { background: { type: ColorType.Solid, color: '#1E1E1E' }, textColor: '#98989D', fontSize: 10, fontFamily: "'JetBrains Mono', monospace" },
        grid: { vertLines: { color: '#2C2C2E' }, horzLines: { color: '#2C2C2E' } },
        timeScale: { timeVisible: true },
        rightPriceScale: { borderColor: '#2C2C2E' },
      });
      compareChartInstanceB.current = chartB;
      const sB = chartB.addSeries(CandlestickSeries, {
        upColor: '#32D74B',
        downColor: '#FF453A',
        priceFormat: { type: 'price', precision: precB, minMove: minMoveB },
      });
      const cB = dataB.candles.map((c) => ({ time: Math.floor(new Date(c.timestamp).getTime() / 1000), open: c.open, high: c.high, low: c.low, close: c.close }));
      const sortedB = cB.sort((a, b) => a.time - b.time);
      sB.setData(sortedB);
      chartB.timeScale().fitContent();

      const renderEndB = performance.now();
      const renderMsB = Math.round(renderEndB - renderStartB);
      setCompareTimingsB({
        fetchMs: fetchLatencyMs,
        renderMs: renderMsB,
        totalMs: fetchLatencyMs + renderMsB,
        barCount: sortedB.length,
        provider: dataB.provider || 'TRADINGVIEW',
      });
    }
  };

  // Filtered Query Audit History based on history filters with "ALL" options
  const filteredHistory = useMemo(() => {
    return queryHistory.filter((q) => {
      const matchMarket = historyMarket === 'ALL' || q.market === historyMarket;
      const matchSymbol = historySymbol === 'ALL' || q.symbol === historySymbol;
      const matchTimeframe = historyTimeframe === 'ALL' || q.timeframe === historyTimeframe;
      return matchMarket && matchSymbol && matchTimeframe;
    });
  }, [queryHistory, historyMarket, historySymbol, historyTimeframe]);

  const statusInfo = marketData?.status || {};
  const isMarketOpen = statusInfo.isOpen;
  const liveQuote = marketData?.liveQuote || {};
  const latestPrice = liveQuote.lastPrice ?? (marketData?.candles?.length ? marketData.candles[marketData.candles.length - 1].close : null);
  const changePct = liveQuote.changePercent ?? 0;
  const isPositive = changePct >= 0;

  // View Mode Toggles Bar Helper
  const renderViewToggles = () => (
    <Card sx={{ display: 'flex', alignItems: 'center', px: 1, py: 0.8, bgcolor: '#1E1E1E', border: '1px solid #2C2C2E', borderRadius: 2, flexShrink: 0 }}>
      <Box sx={{ display: 'flex', gap: 0.5, bgcolor: 'rgba(0,0,0,0.3)', p: 0.5, borderRadius: 1.8, border: '1px solid #2C2C2E' }}>
        <Tooltip title="Terminal Chart">
          <IconButton
            size="small"
            onClick={() => setActiveTab('terminal')}
            sx={{
              bgcolor: activeTab === 'terminal' ? '#2563EB' : 'transparent',
              color: activeTab === 'terminal' ? '#ffffff' : 'text.secondary',
              borderRadius: 1.5,
              p: 0.8,
              '&:hover': { bgcolor: activeTab === 'terminal' ? '#1d4ed8' : 'rgba(255,255,255,0.08)' },
            }}
          >
            <ChartIcon size={17} />
          </IconButton>
        </Tooltip>
        <Tooltip title="Side-by-Side Dual View">
          <IconButton
            size="small"
            onClick={() => setActiveTab('compare')}
            sx={{
              bgcolor: activeTab === 'compare' ? '#2563EB' : 'transparent',
              color: activeTab === 'compare' ? '#ffffff' : 'text.secondary',
              borderRadius: 1.5,
              p: 0.8,
              '&:hover': { bgcolor: activeTab === 'compare' ? '#1d4ed8' : 'rgba(255,255,255,0.08)' },
            }}
          >
            <Columns size={17} />
          </IconButton>
        </Tooltip>
        <Tooltip title={`Query Audit Log (${queryHistory.length})`}>
          <IconButton
            size="small"
            onClick={() => setActiveTab('history')}
            sx={{
              bgcolor: activeTab === 'history' ? '#2563EB' : 'transparent',
              color: activeTab === 'history' ? '#ffffff' : 'text.secondary',
              borderRadius: 1.5,
              p: 0.8,
              '&:hover': { bgcolor: activeTab === 'history' ? '#1d4ed8' : 'rgba(255,255,255,0.08)' },
            }}
          >
            <Clock size={17} />
          </IconButton>
        </Tooltip>
      </Box>
    </Card>
  );

  return (
    <Box sx={{ p: 3, maxWidth: 1600, margin: '0 auto', color: 'text.primary' }}>

      {/* TAB 1: TERMINAL CHART */}
      {activeTab === 'terminal' && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* Top Filter Ribbon & View Switcher (Single Row) */}
          <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'stretch', width: '100%', flexWrap: { xs: 'wrap', md: 'nowrap' } }}>
            {/* Terminal Main Filters Card */}
            <Card sx={{ flex: 1, p: 1.2, bgcolor: '#1E1E1E', border: '1px solid #2C2C2E', borderRadius: 2 }}>
              <Box sx={{ display: 'flex', gap: 1.2, alignItems: 'center', flexWrap: 'wrap', width: '100%' }}>
                {/* Market Exchange Select */}
                <FormControl size="small" sx={{ minWidth: 130, flex: { xs: '1 1 calc(50% - 10px)', sm: '0 0 140px' } }}>
                  <InputLabel id="market-exchange-select-label" sx={{ color: 'text.secondary', fontSize: '0.78rem' }}>
                    Market
                  </InputLabel>
                  <Select
                    labelId="market-exchange-select-label"
                    id="market-exchange-select"
                    value={selectedMarket}
                    label="Market"
                    onChange={(e) => handleMarketChange(e.target.value)}
                    sx={{
                      fontSize: '0.8rem',
                      fontWeight: 700,
                      color: 'text.primary',
                      borderRadius: 1.8,
                    }}
                    MenuProps={{
                      PaperProps: {
                        sx: {
                          bgcolor: '#1E1E1E',
                          border: '1px solid #2C2C2E',
                          borderRadius: 2,
                          boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
                        },
                      },
                    }}
                  >
                    {MARKETS.map((m) => (
                      <MenuItem
                        key={m.id}
                        value={m.id}
                        sx={{
                          fontSize: '0.8rem',
                          fontWeight: selectedMarket === m.id ? 700 : 500,
                          py: 0.7,
                          '&:hover': { bgcolor: 'rgba(255,255,255,0.06)' },
                          '&.Mui-selected': { bgcolor: 'rgba(37, 99, 235, 0.2) !important' },
                        }}
                      >
                        {m.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {/* Asset Symbol Select */}
                <FormControl size="small" sx={{ minWidth: 150, flex: { xs: '1 1 calc(50% - 10px)', sm: '0 0 180px' } }}>
                  <InputLabel id="asset-symbol-select-label" sx={{ color: 'text.secondary', fontSize: '0.78rem' }}>
                    Asset ({catalogSymbols.length})
                  </InputLabel>
                  <Select
                    labelId="asset-symbol-select-label"
                    id="asset-symbol-select"
                    value={symbol}
                    label={`Asset (${catalogSymbols.length})`}
                    onChange={(e) => handleSymbolChange(e.target.value)}
                    renderValue={(selected) => (
                      <Typography sx={{ fontFamily: 'monospace', fontWeight: 800, fontSize: '0.8rem', color: '#60a5fa', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {selected}
                      </Typography>
                    )}
                    MenuProps={{
                      PaperProps: {
                        sx: {
                          bgcolor: '#1E1E1E',
                          border: '1px solid #2C2C2E',
                          borderRadius: 2,
                          maxHeight: 340,
                          boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
                        },
                      },
                    }}
                    sx={{
                      fontSize: '0.8rem',
                      fontWeight: 700,
                      color: 'text.primary',
                      borderRadius: 1.8,
                      fontFamily: 'monospace',
                    }}
                  >
                    {catalogSymbols.map((item) => (
                      <MenuItem
                        key={item.symbol}
                        value={item.symbol}
                        sx={{
                          fontSize: '0.8rem',
                          display: 'flex',
                          justifyContent: 'space-between',
                          gap: 1.5,
                          py: 0.7,
                          '&:hover': { bgcolor: 'rgba(255,255,255,0.06)' },
                          '&.Mui-selected': { bgcolor: 'rgba(37, 99, 235, 0.2) !important' },
                        }}
                      >
                        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', minWidth: 0 }}>
                          <Typography sx={{ fontFamily: 'monospace', fontWeight: 800, fontSize: '0.8rem', color: '#60a5fa' }}>
                            {item.symbol}
                          </Typography>
                          <Typography sx={{ fontSize: '0.72rem', color: 'text.secondary', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {item.shortName || item.fullName}
                          </Typography>
                        </Box>
                        <Chip
                          label={item.exchange || item.market}
                          size="small"
                          sx={{
                            height: 18,
                            fontSize: '0.62rem',
                            fontWeight: 700,
                            bgcolor: 'rgba(255,255,255,0.08)',
                            color: 'text.secondary',
                            flexShrink: 0,
                          }}
                        />
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {/* Timeframe Select */}
                <FormControl size="small" sx={{ minWidth: 110, flex: { xs: '1 1 calc(50% - 10px)', sm: '0 0 120px' } }}>
                  <InputLabel id="timeframe-select-label" sx={{ color: 'text.secondary', fontSize: '0.78rem' }}>
                    Candle
                  </InputLabel>
                  <Select
                    labelId="timeframe-select-label"
                    id="timeframe-select"
                    value={timeframe}
                    label="Candle"
                    onChange={(e) => handleTimeframeChange(e.target.value)}
                    sx={{
                      fontSize: '0.8rem',
                      fontWeight: 700,
                      color: 'text.primary',
                      borderRadius: 1.8,
                      fontFamily: 'monospace',
                    }}
                    MenuProps={{
                      PaperProps: {
                        sx: {
                          bgcolor: '#1E1E1E',
                          border: '1px solid #2C2C2E',
                          borderRadius: 2,
                          maxHeight: 340,
                          boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
                        },
                      },
                    }}
                  >
                    {TIMEFRAME_OPTIONS.map((group, gIdx) => [
                      <MenuItem
                        key={`header-${group.category}`}
                        disabled
                        sx={{
                          fontSize: '0.65rem',
                          fontWeight: 800,
                          color: '#98989D',
                          textTransform: 'uppercase',
                          letterSpacing: '0.04em',
                          bgcolor: 'rgba(255,255,255,0.02)',
                          py: 0.3,
                          borderTop: gIdx > 0 ? '1px solid #2C2C2E' : 'none',
                        }}
                      >
                        {group.category}
                      </MenuItem>,
                      ...group.items.map((item) => (
                        <MenuItem
                          key={item.value}
                          value={item.value}
                          sx={{
                            fontSize: '0.8rem',
                            fontFamily: 'monospace',
                            fontWeight: timeframe === item.value ? 700 : 500,
                            py: 0.5,
                            pl: 2,
                            '&:hover': { bgcolor: 'rgba(255,255,255,0.06)' },
                            '&.Mui-selected': { bgcolor: 'rgba(37, 99, 235, 0.2) !important' },
                          }}
                        >
                          {item.label}
                        </MenuItem>
                      )),
                    ])}
                  </Select>
                </FormControl>

                {/* Live Stream Switch, Patterns & Overlays */}
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', ml: 'auto', flexWrap: 'wrap' }}>
                  {/* Live Stream Toggle Switch */}
                  <FormControlLabel
                    control={
                      <Switch
                        size="small"
                        checked={mode === 'LIVE'}
                        onChange={(e) => {
                          const nextMode = e.target.checked ? 'LIVE' : 'HISTORICAL';
                          setMode(nextMode);
                          if (nextMode === 'LIVE') {
                            fetchData({ mode: 'LIVE' });
                          }
                        }}
                        sx={{
                          '& .MuiSwitch-switchBase.Mui-checked': {
                            color: '#32D74B',
                          },
                          '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                            backgroundColor: '#32D74B',
                          },
                        }}
                      />
                    }
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Activity size={13} color={mode === 'LIVE' ? '#32D74B' : '#98989D'} />
                        <Typography sx={{ fontSize: '0.76rem', fontWeight: 700, color: mode === 'LIVE' ? '#32D74B' : 'text.secondary' }}>
                          Live Stream
                        </Typography>
                      </Box>
                    }
                    sx={{ mr: 0.5 }}
                  />

                  {/* Dedicated Patterns Popover Button */}
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={(e) => setPatternMenuAnchor(e.currentTarget)}
                    sx={{
                      borderColor: selectedPatterns.length > 0 ? 'rgba(50, 215, 75, 0.4)' : '#2C2C2E',
                      color: selectedPatterns.length > 0 ? '#32D74B' : 'text.primary',
                      bgcolor: selectedPatterns.length > 0 ? 'rgba(50, 215, 75, 0.08)' : 'transparent',
                      fontSize: '0.74rem',
                      fontWeight: 700,
                      borderRadius: 1.8,
                      textTransform: 'none',
                      px: 1.2,
                      py: 0.5,
                      '&:hover': { borderColor: '#32D74B', bgcolor: 'rgba(50, 215, 75, 0.15)' },
                    }}
                    startIcon={<Layers size={13} color="#32D74B" />}
                    endIcon={<ChevronDown size={13} />}
                  >
                    Patterns ({selectedPatterns.includes('ALL') ? 'All' : selectedPatterns.length})
                  </Button>

                  {/* Overlays Popover Button */}
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={(e) => setOverlayMenuAnchor(e.currentTarget)}
                    sx={{
                      borderColor: '#2C2C2E',
                      color: 'text.primary',
                      fontSize: '0.74rem',
                      fontWeight: 700,
                      borderRadius: 1.8,
                      textTransform: 'none',
                      px: 1.2,
                      py: 0.5,
                    }}
                    startIcon={<Sliders size={13} color="#38bdf8" />}
                    endIcon={<ChevronDown size={13} />}
                  >
                    Overlays ({selectedOverlays.length})
                  </Button>
                </Box>
              </Box>

              {/* Historical Date Range Filter */}
              {mode === 'HISTORICAL' && (
                <Box sx={{ mt: 1.2, pt: 1.2, borderTop: '1px solid #2C2C2E', display: 'flex', gap: 1.5, alignItems: 'center', flexWrap: 'wrap' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8 }}>
                    <Calendar size={14} color="#60a5fa" />
                    <Typography sx={{ fontSize: '0.75rem', fontWeight: 700, color: 'text.secondary' }}>
                      Historical Date Filter:
                    </Typography>
                  </Box>
                  <TextField
                    size="small"
                    type="date"
                    label="Start Date"
                    value={startDate}
                    onChange={(e) => {
                      setStartDate(e.target.value);
                      fetchData({ mode: 'HISTORICAL', startDate: e.target.value, endDate });
                    }}
                    slotProps={{ inputLabel: { shrink: true } }}
                    sx={{ width: 160 }}
                  />
                  <TextField
                    size="small"
                    type="date"
                    label="End Date"
                    value={endDate}
                    onChange={(e) => {
                      setEndDate(e.target.value);
                      fetchData({ mode: 'HISTORICAL', startDate, endDate: e.target.value });
                    }}
                    slotProps={{ inputLabel: { shrink: true } }}
                    sx={{ width: 160 }}
                  />
                </Box>
              )}
            </Card>

            {/* 3 View Mode Toggles Bar */}
            {renderViewToggles()}
          </Box>

          {/* Patterns Popover Menu */}
          <Menu
            anchorEl={patternMenuAnchor}
            open={Boolean(patternMenuAnchor)}
            onClose={() => setPatternMenuAnchor(null)}
            slotProps={{
              paper: {
                sx: {
                  bgcolor: '#1E1E1E',
                  border: '1px solid #2C2C2E',
                  borderRadius: 2,
                  p: 1.5,
                  minWidth: 260,
                  maxHeight: 380,
                  boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
                },
              },
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.2, pb: 0.8, borderBottom: '1px solid #2C2C2E', px: 0.5 }}>
              <Typography sx={{ fontSize: '0.72rem', fontWeight: 800, color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Filter Patterns ({selectedPatterns.length})
              </Typography>
              {selectedPatterns.length > 0 && (
                <Button
                  size="small"
                  onClick={() => {
                    setSelectedPatterns([]);
                    if (marketData) renderLightweightChart(marketData, timings.fetchMs, [], selectedOverlays);
                  }}
                  sx={{
                    fontSize: '0.68rem',
                    fontWeight: 700,
                    px: 1,
                    py: 0.2,
                    minWidth: 0,
                    textTransform: 'none',
                    color: '#FF453A',
                    bgcolor: 'rgba(255, 69, 58, 0.1)',
                    border: '1px solid rgba(255, 69, 58, 0.25)',
                    borderRadius: 1.2,
                    '&:hover': { bgcolor: 'rgba(255, 69, 58, 0.2)', borderColor: '#FF453A' },
                  }}
                >
                  Clear All
                </Button>
              )}
            </Box>
            <FormGroup>
              {CANDLESTICK_PATTERNS.map((p) => {
                const isChecked = selectedPatterns.includes(p.id);
                return (
                  <FormControlLabel
                    key={p.id}
                    control={
                      <Checkbox
                        size="small"
                        checked={isChecked}
                        onChange={(e) => {
                          let nextPatterns;
                          if (p.id === 'ALL') {
                            nextPatterns = e.target.checked ? ['ALL'] : [];
                          } else {
                            if (e.target.checked) {
                              nextPatterns = [...selectedPatterns.filter((id) => id !== 'ALL'), p.id];
                            } else {
                              nextPatterns = selectedPatterns.filter((id) => id !== p.id);
                            }
                          }
                          setSelectedPatterns(nextPatterns);
                          if (marketData) {
                            renderLightweightChart(marketData, timings.fetchMs, nextPatterns, selectedOverlays);
                          }
                        }}
                        sx={{ color: '#32D74B', '&.Mui-checked': { color: '#32D74B' } }}
                      />
                    }
                    label={
                      <Typography sx={{ fontSize: '0.78rem', color: isChecked ? '#ffffff' : 'text.secondary', fontWeight: isChecked ? 700 : 500 }}>
                        {p.label}
                      </Typography>
                    }
                    sx={{ mx: 0, my: 0.2 }}
                  />
                );
              })}
            </FormGroup>
          </Menu>

          {/* Overlays Popover Menu */}
          <Menu
            anchorEl={overlayMenuAnchor}
            open={Boolean(overlayMenuAnchor)}
            onClose={() => setOverlayMenuAnchor(null)}
            slotProps={{
              paper: {
                sx: {
                  bgcolor: '#1E1E1E',
                  border: '1px solid #2C2C2E',
                  borderRadius: 2,
                  p: 1.5,
                  minWidth: 260,
                },
              },
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.2, pb: 0.8, borderBottom: '1px solid #2C2C2E', px: 0.5 }}>
              <Typography sx={{ fontSize: '0.72rem', fontWeight: 800, color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Technical Overlays ({selectedOverlays.length})
              </Typography>
              {selectedOverlays.length > 0 && (
                <Button
                  size="small"
                  onClick={() => {
                    setSelectedOverlays([]);
                    if (marketData) {
                      renderLightweightChart(marketData, timings.fetchMs, selectedPatterns, []);
                    }
                  }}
                  sx={{
                    fontSize: '0.68rem',
                    fontWeight: 700,
                    px: 1,
                    py: 0.2,
                    minWidth: 0,
                    textTransform: 'none',
                    color: '#FF453A',
                    bgcolor: 'rgba(255, 69, 58, 0.1)',
                    border: '1px solid rgba(255, 69, 58, 0.25)',
                    borderRadius: 1.2,
                    '&:hover': { bgcolor: 'rgba(255, 69, 58, 0.2)', borderColor: '#FF453A' },
                  }}
                >
                  Clear All
                </Button>
              )}
            </Box>
            <FormGroup>
              {OVERLAY_OPTIONS.map((opt) => (
                <FormControlLabel
                  key={opt.id}
                  control={
                    <Checkbox
                      size="small"
                      checked={selectedOverlays.includes(opt.id)}
                      onChange={(e) => {
                        let nextOverlays;
                        if (e.target.checked) {
                          nextOverlays = [...selectedOverlays, opt.id];
                        } else {
                          nextOverlays = selectedOverlays.filter((id) => id !== opt.id);
                        }
                        setSelectedOverlays(nextOverlays);
                        if (marketData) {
                          renderLightweightChart(marketData, timings.fetchMs, selectedPatterns, nextOverlays);
                        }
                      }}
                      sx={{ color: opt.color, '&.Mui-checked': { color: opt.color } }}
                    />
                  }
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: opt.color }} />
                      <Typography sx={{ fontSize: '0.8rem', color: 'text.primary', fontWeight: 600 }}>{opt.label}</Typography>
                    </Box>
                  }
                  sx={{ mx: 0, my: 0.3 }}
                />
              ))}
            </FormGroup>
          </Menu>

          {/* TradingView Lightweight Charts Native Canvas, Floating HUD & Bottom Info Footer */}
          <Card sx={{ p: 2, bgcolor: '#1E1E1E', border: '1px solid #2C2C2E', borderRadius: 2, position: 'relative' }}>
            {errorMsg && (
              <Box sx={{ p: 1.5, mb: 1.5, bgcolor: 'rgba(255, 69, 58, 0.15)', border: '1px solid #FF453A', borderRadius: 1.5 }}>
                <Typography sx={{ color: '#FF453A', fontSize: '0.8rem', fontWeight: 600 }}>
                  ⚠️ {errorMsg}
                </Typography>
              </Box>
            )}

            {/* TradingView-Style Interactive OHLC HUD Bar & Spot Rate */}
            <Box
              sx={{
                position: 'absolute',
                top: 16,
                left: 16,
                zIndex: 10,
                bgcolor: 'rgba(18, 18, 18, 0.92)',
                backdropFilter: 'blur(8px)',
                px: 1.5,
                py: 0.6,
                borderRadius: 1.5,
                border: '1px solid #2C2C2E',
                display: 'flex',
                alignItems: 'center',
                gap: 1.5,
                flexWrap: 'wrap',
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
              }}
            >
              {/* Asset Symbol, Timeframe & Current Live Spot Rate */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography sx={{ fontWeight: 800, fontSize: '0.82rem', color: 'text.primary', fontFamily: 'monospace' }}>
                  {symbol}
                </Typography>
                <Chip label={timeframe} size="small" sx={{ height: 18, fontSize: '0.65rem', fontWeight: 700, bgcolor: '#2563EB', color: '#fff' }} />
                <Typography sx={{ fontWeight: 800, fontSize: '0.86rem', fontFamily: 'monospace', color: isPositive ? '#32D74B' : '#FF453A' }}>
                  {formatPrice(latestPrice, selectedMarket)}
                </Typography>
                <Typography sx={{ fontSize: '0.7rem', color: isPositive ? '#32D74B' : '#FF453A', fontFamily: 'monospace', fontWeight: 700 }}>
                  ({isPositive ? '+' : ''}{changePct.toFixed(2)}%)
                </Typography>
              </Box>

              {/* Crosshair / Candle OHLC details */}
              {hudData && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2, flexWrap: 'wrap' }}>
                  <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary', fontFamily: 'monospace' }}>
                    O: <span style={{ color: '#ffffff', fontWeight: 600 }}>{formatPrice(hudData.open, selectedMarket)}</span>
                  </Typography>
                  <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary', fontFamily: 'monospace' }}>
                    H: <span style={{ color: '#32D74B', fontWeight: 600 }}>{formatPrice(hudData.high, selectedMarket)}</span>
                  </Typography>
                  <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary', fontFamily: 'monospace' }}>
                    L: <span style={{ color: '#FF453A', fontWeight: 600 }}>{formatPrice(hudData.low, selectedMarket)}</span>
                  </Typography>
                  <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary', fontFamily: 'monospace' }}>
                    C: <span style={{ color: hudData.close >= hudData.open ? '#32D74B' : '#FF453A', fontWeight: 700 }}>{formatPrice(hudData.close, selectedMarket)}</span>
                  </Typography>
                  <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary', fontFamily: 'monospace' }}>
                    Vol: <span style={{ color: '#38bdf8', fontWeight: 600 }}>{hudData.volume ? Number(hudData.volume).toLocaleString() : '0'}</span>
                  </Typography>
                  <Typography sx={{ fontSize: '0.68rem', color: 'text.secondary', fontFamily: 'monospace' }}>
                    {hudData.time}
                  </Typography>
                </Box>
              )}
            </Box>

            {/* Quick Fit Chart Icon Button */}
            <Tooltip title="Fit Chart to Viewport">
              <IconButton
                size="small"
                onClick={handleFitChart}
                sx={{
                  position: 'absolute',
                  top: 16,
                  right: 16,
                  zIndex: 10,
                  bgcolor: 'rgba(30, 30, 30, 0.8)',
                  border: '1px solid #2C2C2E',
                  color: 'text.secondary',
                  '&:hover': { bgcolor: '#2563EB', color: '#ffffff' },
                }}
              >
                <Maximize2 size={15} />
              </IconButton>
            </Tooltip>

            {/* Canvas Container */}
            <Box
              ref={chartContainerRef}
              sx={{
                width: '100%',
                height: 480,
                borderRadius: 1.5,
                overflow: 'hidden',
                bgcolor: '#1E1E1E',
              }}
            />

            {/* Chart Bottom Info & Holiday Message Footer Bar */}
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', pt: 1.2, mt: 1, borderTop: '1px solid #2C2C2E', flexWrap: 'wrap', gap: 1 }}>
              {/* Holiday & Market Session Information Icon */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Tooltip title={statusInfo.message || (isMarketOpen ? 'Market is open for live trading.' : 'Exchange session is closed.')}>
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 0.8,
                      bgcolor: isMarketOpen ? 'rgba(50, 215, 75, 0.08)' : 'rgba(255, 159, 10, 0.08)',
                      px: 1.2,
                      py: 0.4,
                      borderRadius: 1.5,
                      border: `1px solid ${isMarketOpen ? 'rgba(50, 215, 75, 0.25)' : 'rgba(255, 159, 10, 0.25)'}`,
                    }}
                  >
                    {isMarketOpen ? (
                      <CheckCircle2 size={13} color="#32D74B" />
                    ) : (
                      <Info size={13} color="#FF9F0A" />
                    )}
                    <Typography sx={{ fontSize: '0.72rem', fontWeight: 700, color: isMarketOpen ? '#32D74B' : '#FF9F0A' }}>
                      {statusInfo.sessionName || (isMarketOpen ? 'Regular Session' : 'Market Closed')}
                    </Typography>
                    <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>
                      • {statusInfo.message || (isMarketOpen ? 'Live ticks streaming' : 'Replay cache active')}
                      {statusInfo.nextOpenTime && ` (Opens: ${new Date(statusInfo.nextOpenTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})`}
                    </Typography>
                  </Box>
                </Tooltip>
              </Box>

              {/* Diagnostic Timings & Latency Monospace Footer */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary', fontFamily: 'monospace' }}>
                  Diagnostic: <span style={{ color: '#38bdf8' }}>{(timings.fetchMs / 1000).toFixed(3)}s</span> Data | <span style={{ color: '#a855f7' }}>{(timings.renderMs / 1000).toFixed(3)}s</span> Chart | <span style={{ color: '#32D74B', fontWeight: 700 }}>{(timings.totalMs / 1000).toFixed(3)}s</span> Total ({timings.barCount} bars • {timings.provider})
                </Typography>
              </Box>
            </Box>
          </Card>
        </Box>
      )}

      {/* TAB 2: SIDE-BY-SIDE DUAL COMPARISON (No Top Filter Bar, 2 Square Filter Cards directly on Dual View) */}
      {activeTab === 'compare' && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* Top Bar for Dual View: Title on left, 3 View Mode Toggles on right */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', flexWrap: 'wrap', gap: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Typography variant="h6" sx={{ fontSize: '0.95rem', fontWeight: 800, color: 'text.primary' }}>
                Dual Instrument Synchronous Comparison
              </Typography>
              <Chip
                label="LIVE SYNC"
                size="small"
                sx={{ height: 20, fontSize: '0.65rem', fontWeight: 800, bgcolor: 'rgba(50, 215, 75, 0.15)', color: '#32D74B' }}
              />
            </Box>
            {renderViewToggles()}
          </Box>

          {/* 2 Square-Shaped Dedicated Filter Cards for Side A and Side B */}
          <Grid container spacing={2}>
            {/* Side A Filter Bar (Square Card) */}
            <Grid size={{ xs: 12, md: 6 }}>
              <Card sx={{ p: 2, bgcolor: '#1E1E1E', border: '1px solid #2C2C2E', borderRadius: 2 }}>
                <Typography sx={{ fontSize: '0.78rem', fontWeight: 800, color: '#38bdf8', mb: 1.5, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Side A (Primary Instrument)
                </Typography>
                <Grid container spacing={1.2} alignItems="center">
                  <Grid size={{ xs: 12, sm: 4 }}>
                    <FormControl fullWidth size="small">
                      <InputLabel sx={{ color: 'text.secondary', fontSize: '0.78rem' }}>Market</InputLabel>
                      <Select
                        value={compareA.market}
                        label="Market"
                        onChange={(e) => handleCompareAChange('market', e.target.value)}
                        sx={{ fontSize: '0.8rem', fontWeight: 700 }}
                      >
                        {MARKETS.map((m) => (
                          <MenuItem key={m.id} value={m.id}>{m.label}</MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid size={{ xs: 12, sm: 5 }}>
                    <FormControl fullWidth size="small">
                      <InputLabel sx={{ color: 'text.secondary', fontSize: '0.78rem' }}>Asset</InputLabel>
                      <Select
                        value={compareA.symbol}
                        label="Asset"
                        onChange={(e) => handleCompareAChange('symbol', e.target.value)}
                        sx={{ fontSize: '0.8rem', fontWeight: 700, fontFamily: 'monospace' }}
                      >
                        {(DEFAULT_SYMBOLS_BY_MARKET[compareA.market] || catalogSymbols).map((s) => (
                          <MenuItem key={s.symbol} value={s.symbol}>
                            {s.symbol} - {s.shortName || s.symbol}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid size={{ xs: 12, sm: 3 }}>
                    <FormControl fullWidth size="small">
                      <InputLabel sx={{ color: 'text.secondary', fontSize: '0.78rem' }}>Candle</InputLabel>
                      <Select
                        value={compareA.timeframe}
                        label="Candle"
                        onChange={(e) => handleCompareAChange('timeframe', e.target.value)}
                        sx={{ fontSize: '0.8rem', fontWeight: 700, fontFamily: 'monospace' }}
                      >
                        {TIMEFRAMES.map((tf) => (
                          <MenuItem key={tf} value={tf}>{tf}</MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                </Grid>
              </Card>
            </Grid>

            {/* Side B Filter Bar (Square Card) */}
            <Grid size={{ xs: 12, md: 6 }}>
              <Card sx={{ p: 2, bgcolor: '#1E1E1E', border: '1px solid #2C2C2E', borderRadius: 2 }}>
                <Typography sx={{ fontSize: '0.78rem', fontWeight: 800, color: '#a855f7', mb: 1.5, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Side B (Comparison Instrument)
                </Typography>
                <Grid container spacing={1.2} alignItems="center">
                  <Grid size={{ xs: 12, sm: 4 }}>
                    <FormControl fullWidth size="small">
                      <InputLabel sx={{ color: 'text.secondary', fontSize: '0.78rem' }}>Market</InputLabel>
                      <Select
                        value={compareB.market}
                        label="Market"
                        onChange={(e) => handleCompareBChange('market', e.target.value)}
                        sx={{ fontSize: '0.8rem', fontWeight: 700 }}
                      >
                        {MARKETS.map((m) => (
                          <MenuItem key={m.id} value={m.id}>{m.label}</MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid size={{ xs: 12, sm: 5 }}>
                    <FormControl fullWidth size="small">
                      <InputLabel sx={{ color: 'text.secondary', fontSize: '0.78rem' }}>Asset</InputLabel>
                      <Select
                        value={compareB.symbol}
                        label="Asset"
                        onChange={(e) => handleCompareBChange('symbol', e.target.value)}
                        sx={{ fontSize: '0.8rem', fontWeight: 700, fontFamily: 'monospace' }}
                      >
                        {(DEFAULT_SYMBOLS_BY_MARKET[compareB.market] || catalogSymbols).map((s) => (
                          <MenuItem key={s.symbol} value={s.symbol}>
                            {s.symbol} - {s.shortName || s.symbol}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid size={{ xs: 12, sm: 3 }}>
                    <FormControl fullWidth size="small">
                      <InputLabel sx={{ color: 'text.secondary', fontSize: '0.78rem' }}>Candle</InputLabel>
                      <Select
                        value={compareB.timeframe}
                        label="Candle"
                        onChange={(e) => handleCompareBChange('timeframe', e.target.value)}
                        sx={{ fontSize: '0.8rem', fontWeight: 700, fontFamily: 'monospace' }}
                      >
                        {TIMEFRAMES.map((tf) => (
                          <MenuItem key={tf} value={tf}>{tf}</MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                </Grid>
              </Card>
            </Grid>
          </Grid>

          {/* Dual Charts Grid */}
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card sx={{ p: 2, bgcolor: '#1E1E1E', border: '1px solid #2C2C2E', borderRadius: 2.5 }}>
                <Typography sx={{ fontWeight: 800, color: '#38bdf8', mb: 1, fontSize: '0.9rem' }}>
                  {compareA.symbol} [{compareA.timeframe}]
                </Typography>
                <Box ref={compareChartRefA} sx={{ width: '100%', height: 380, bgcolor: '#1E1E1E', borderRadius: 2 }} />
                <Box sx={{ mt: 1.5, pt: 1, borderTop: '1px solid #2C2C2E', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary', fontFamily: 'monospace' }}>
                    Diagnostic: <span style={{ color: '#38bdf8' }}>{(compareTimingsA.fetchMs / 1000).toFixed(3)}s</span> Data | <span style={{ color: '#a855f7' }}>{(compareTimingsA.renderMs / 1000).toFixed(3)}s</span> Chart | <span style={{ color: '#32D74B', fontWeight: 700 }}>{(compareTimingsA.totalMs / 1000).toFixed(3)}s</span> Total ({compareTimingsA.barCount} bars • {compareTimingsA.provider})
                  </Typography>
                </Box>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card sx={{ p: 2, bgcolor: '#1E1E1E', border: '1px solid #2C2C2E', borderRadius: 2.5 }}>
                <Typography sx={{ fontWeight: 800, color: '#a855f7', mb: 1, fontSize: '0.9rem' }}>
                  {compareB.symbol} [{compareB.timeframe}]
                </Typography>
                <Box ref={compareChartRefB} sx={{ width: '100%', height: 380, bgcolor: '#1E1E1E', borderRadius: 2 }} />
                <Box sx={{ mt: 1.5, pt: 1, borderTop: '1px solid #2C2C2E', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary', fontFamily: 'monospace' }}>
                    Diagnostic: <span style={{ color: '#38bdf8' }}>{(compareTimingsB.fetchMs / 1000).toFixed(3)}s</span> Data | <span style={{ color: '#a855f7' }}>{(compareTimingsB.renderMs / 1000).toFixed(3)}s</span> Chart | <span style={{ color: '#32D74B', fontWeight: 700 }}>{(compareTimingsB.totalMs / 1000).toFixed(3)}s</span> Total ({compareTimingsB.barCount} bars • {compareTimingsB.provider})
                  </Typography>
                </Box>
              </Card>
            </Grid>
          </Grid>
        </Box>
      )}

      {/* TAB 3: STORED QUERY AUDIT LOG */}
      {activeTab === 'history' && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* Top Filter Bar & View Toggles for Audit Log */}
          <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'stretch', width: '100%', flexWrap: { xs: 'wrap', md: 'nowrap' } }}>
            <Card sx={{ flex: 1, p: 1.2, bgcolor: '#1E1E1E', border: '1px solid #2C2C2E', borderRadius: 2 }}>
              <Box sx={{ display: 'flex', gap: 1.2, alignItems: 'center', flexWrap: 'wrap', width: '100%' }}>
                {/* Market Filter (with ALL option) */}
                <FormControl size="small" sx={{ minWidth: 140, flex: { xs: '1 1 calc(50% - 10px)', sm: '0 0 150px' } }}>
                  <InputLabel id="history-market-select-label" sx={{ color: 'text.secondary', fontSize: '0.78rem' }}>
                    Market
                  </InputLabel>
                  <Select
                    labelId="history-market-select-label"
                    value={historyMarket}
                    label="Market"
                    onChange={(e) => setHistoryMarket(e.target.value)}
                    sx={{ fontSize: '0.8rem', fontWeight: 700, color: 'text.primary', borderRadius: 1.8 }}
                  >
                    <MenuItem value="ALL" sx={{ fontWeight: 800, color: '#60a5fa' }}>All Markets</MenuItem>
                    {MARKETS.map((m) => (
                      <MenuItem key={m.id} value={m.id}>{m.label}</MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {/* Asset Filter (with ALL option) */}
                <FormControl size="small" sx={{ minWidth: 160, flex: { xs: '1 1 calc(50% - 10px)', sm: '0 0 180px' } }}>
                  <InputLabel id="history-asset-select-label" sx={{ color: 'text.secondary', fontSize: '0.78rem' }}>
                    Asset
                  </InputLabel>
                  <Select
                    labelId="history-asset-select-label"
                    value={historySymbol}
                    label="Asset"
                    onChange={(e) => setHistorySymbol(e.target.value)}
                    sx={{ fontSize: '0.8rem', fontWeight: 700, color: 'text.primary', borderRadius: 1.8, fontFamily: 'monospace' }}
                  >
                    <MenuItem value="ALL" sx={{ fontWeight: 800, color: '#60a5fa' }}>All Assets</MenuItem>
                    {(historyMarket !== 'ALL' && DEFAULT_SYMBOLS_BY_MARKET[historyMarket] ? DEFAULT_SYMBOLS_BY_MARKET[historyMarket] : catalogSymbols).map((item) => (
                      <MenuItem key={item.symbol} value={item.symbol}>
                        {item.symbol} - {item.shortName || item.fullName || item.symbol}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {/* Timeframe Filter (with ALL option) */}
                <FormControl size="small" sx={{ minWidth: 130, flex: { xs: '1 1 calc(50% - 10px)', sm: '0 0 140px' } }}>
                  <InputLabel id="history-timeframe-select-label" sx={{ color: 'text.secondary', fontSize: '0.78rem' }}>
                    Candle
                  </InputLabel>
                  <Select
                    labelId="history-timeframe-select-label"
                    value={historyTimeframe}
                    label="Candle"
                    onChange={(e) => setHistoryTimeframe(e.target.value)}
                    sx={{ fontSize: '0.8rem', fontWeight: 700, color: 'text.primary', borderRadius: 1.8, fontFamily: 'monospace' }}
                  >
                    <MenuItem value="ALL" sx={{ fontWeight: 800, color: '#60a5fa' }}>All Timeframes</MenuItem>
                    {TIMEFRAMES.map((tf) => (
                      <MenuItem key={tf} value={tf}>{tf}</MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {/* Clear / Reset Filters */}
                {(historyMarket !== 'ALL' || historySymbol !== 'ALL' || historyTimeframe !== 'ALL') && (
                  <Button
                    size="small"
                    onClick={() => {
                      setHistoryMarket('ALL');
                      setHistorySymbol('ALL');
                      setHistoryTimeframe('ALL');
                    }}
                    sx={{ color: '#FF453A', fontSize: '0.72rem', textTransform: 'none', fontWeight: 700 }}
                  >
                    Reset Filters
                  </Button>
                )}

                <Box sx={{ ml: 'auto', display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Chip
                    label={`Showing ${filteredHistory.length} of ${queryHistory.length} records`}
                    size="small"
                    sx={{ bgcolor: 'rgba(37, 99, 235, 0.15)', color: '#60a5fa', fontWeight: 700, fontSize: '0.72rem' }}
                  />
                </Box>
              </Box>
            </Card>

            {renderViewToggles()}
          </Box>

          {/* Audit Log Table */}
          <Card sx={{ bgcolor: '#1E1E1E', border: '1px solid #2C2C2E', borderRadius: 2.5, overflow: 'hidden' }}>
            <Box sx={{ p: 2.5, borderBottom: '1px solid #2C2C2E', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6" sx={{ fontSize: '0.95rem', fontWeight: 800, color: 'text.primary' }}>
                Execution &amp; Telemetry Query History
              </Typography>
              <Button
                size="small"
                onClick={() => setQueryHistory([])}
                sx={{ color: 'text.secondary', fontSize: '0.75rem', textTransform: 'none' }}
              >
                Clear Log
              </Button>
            </Box>

            <TableContainer component={Paper} sx={{ bgcolor: 'transparent', boxShadow: 'none' }}>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: '#18181b' }}>
                    <TableCell sx={{ color: 'text.secondary', fontWeight: 700, fontSize: '0.72rem' }}>REQ ID</TableCell>
                    <TableCell sx={{ color: 'text.secondary', fontWeight: 700, fontSize: '0.72rem' }}>SYMBOL</TableCell>
                    <TableCell sx={{ color: 'text.secondary', fontWeight: 700, fontSize: '0.72rem' }}>MARKET</TableCell>
                    <TableCell sx={{ color: 'text.secondary', fontWeight: 700, fontSize: '0.72rem' }}>TIMEFRAME</TableCell>
                    <TableCell sx={{ color: 'text.secondary', fontWeight: 700, fontSize: '0.72rem' }}>BARS</TableCell>
                    <TableCell sx={{ color: 'text.secondary', fontWeight: 700, fontSize: '0.72rem' }}>PROVIDER</TableCell>
                    <TableCell sx={{ color: 'text.secondary', fontWeight: 700, fontSize: '0.72rem' }}>PRICE</TableCell>
                    <TableCell sx={{ color: 'text.secondary', fontWeight: 700, fontSize: '0.72rem' }}>FETCH TIME</TableCell>
                    <TableCell sx={{ color: 'text.secondary', fontWeight: 700, fontSize: '0.72rem', textAlign: 'right' }}>ACTION</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredHistory.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} sx={{ textAlign: 'center', py: 5, color: 'text.secondary' }}>
                        {queryHistory.length === 0
                          ? 'No queries recorded in this session.'
                          : `No queries matched current filter (${historyMarket} • ${historySymbol} • ${historyTimeframe}). Total queries recorded: ${queryHistory.length}`}
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredHistory.map((q) => (
                      <TableRow key={q.id} hover sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                        <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'text.secondary' }}>{q.id}</TableCell>
                        <TableCell sx={{ fontFamily: 'monospace', fontWeight: 700, color: 'text.primary', fontSize: '0.8rem' }}>{q.symbol}</TableCell>
                        <TableCell sx={{ fontSize: '0.78rem', color: 'text.secondary' }}>{q.market}</TableCell>
                        <TableCell sx={{ color: '#a855f7', fontWeight: 700, fontSize: '0.78rem' }}>{q.timeframe}</TableCell>
                        <TableCell sx={{ fontSize: '0.78rem', color: 'text.primary' }}>{q.bars} bars</TableCell>
                        <TableCell>
                          <Chip label={q.provider} size="small" sx={{ height: 20, fontSize: '0.68rem', bgcolor: 'rgba(37,99,235,0.15)', color: '#60a5fa', fontWeight: 700 }} />
                        </TableCell>
                        <TableCell sx={{ fontFamily: 'monospace', fontWeight: 700, color: 'text.primary' }}>{q.price}</TableCell>
                        <TableCell sx={{ fontFamily: 'monospace', color: '#38bdf8', fontSize: '0.75rem' }}>{q.fetchLatency}ms</TableCell>
                        <TableCell sx={{ textAlign: 'right' }}>
                          <Button
                            size="small"
                            onClick={() => {
                              setSymbol(q.symbol);
                              setSelectedMarket(q.market);
                              setTimeframe(q.timeframe);
                              setActiveTab('terminal');
                              fetchData({ symbol: q.symbol, market: q.market, timeframe: q.timeframe });
                            }}
                            sx={{
                              fontSize: '0.72rem',
                              bgcolor: 'rgba(37, 99, 235, 0.15)',
                              color: '#2563EB',
                              fontWeight: 700,
                              textTransform: 'none',
                              borderRadius: 1.5,
                              '&:hover': { bgcolor: 'rgba(37, 99, 235, 0.25)' },
                            }}
                          >
                            Load
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Card>
        </Box>
      )}
    </Box>
  );
}
