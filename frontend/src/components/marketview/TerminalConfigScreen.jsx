import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  Typography,
  Grid,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  FormControlLabel,
  FormGroup,
  CircularProgress,
  Alert,
  Chip,
  Divider,
} from '@mui/material';
import {
  Sliders,
  CheckCircle2,
  Save,
  RotateCcw,
  Layers,
  Activity,
  Compass,
} from 'lucide-react';
import { api } from '../../api';
import { CandleIconSvg, IndicatorIconSvg } from './PatternIndicatorIcons';

const MARKETS = [
  { id: 'INDIAN_EQUITY', label: 'NSE (India)', defaultSymbol: 'RELIANCE', exchange: 'NSE' },
  { id: 'US_EQUITY', label: 'US Equities', defaultSymbol: 'AAPL', exchange: 'NASDAQ' },
  { id: 'CRYPTO', label: 'Crypto (Binance)', defaultSymbol: 'BTCUSDT', exchange: 'BINANCE' },
  { id: 'FOREX', label: 'Forex (Global)', defaultSymbol: 'EURUSD', exchange: 'FX' },
  { id: 'MCX', label: 'MCX Commodities', defaultSymbol: 'CRUDEOIL', exchange: 'MCX' },
];

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

const TIMEFRAMES = [
  { value: '1m', label: '1m (1 Min Intraday)' },
  { value: '3m', label: '3m (3 Min Intraday)' },
  { value: '5m', label: '5m (5 Min Intraday)' },
  { value: '15m', label: '15m (15 Min Intraday)' },
  { value: '30m', label: '30m (30 Min Intraday)' },
  { value: '1h', label: '1h (1 Hour Hourly)' },
  { value: '2h', label: '2h (2 Hours Hourly)' },
  { value: '4h', label: '4h (4 Hours Hourly)' },
  { value: '1d', label: '1d (1 Day Daily)' },
  { value: '1w', label: '1w (1 Week Weekly)' },
  { value: '1M', label: '1M (1 Month Monthly)' },
];

const INDICATOR_OPTIONS = [
  // --- Moving Averages & Trend Baselines ---
  { id: 'EMA_9', label: 'EMA 9 (Fast Trend)', category: 'Moving Averages', color: '#38bdf8' },
  { id: 'EMA_21', label: 'EMA 21 (Short Trend)', category: 'Moving Averages', color: '#a855f7' },
  { id: 'EMA_50', label: 'EMA 50 (Medium Trend)', category: 'Moving Averages', color: '#f59e0b' },
  { id: 'EMA_200', label: 'EMA 200 (Macro Trend)', category: 'Moving Averages', color: '#f43f5e' },
  { id: 'SMA_20', label: 'SMA 20 (Mean Baseline)', category: 'Moving Averages', color: '#60a5fa' },
  { id: 'SMA_50', label: 'SMA 50 (Medium Baseline)', category: 'Moving Averages', color: '#fb923c' },
  { id: 'SMA_200', label: 'SMA 200 (Golden/Death Cross)', category: 'Moving Averages', color: '#e11d48' },
  // --- Price Envelopes & Overlays ---
  { id: 'VWAP', label: 'VWAP (Volume Weighted)', category: 'Price Bands & Envelopes', color: '#fbbf24' },
  { id: 'BB', label: 'Bollinger Bands (20, 2)', category: 'Price Bands & Envelopes', color: '#3b82f6' },
  { id: 'SUPERTREND', label: 'Supertrend (10, 3)', category: 'Trend Followers', color: '#10b981' },
  { id: 'KELTNER', label: 'Keltner Channels (20, 2)', category: 'Price Bands & Envelopes', color: '#06b6d4' },
  { id: 'DONCHIAN', label: 'Donchian Channels (20)', category: 'Price Bands & Envelopes', color: '#8b5cf6' },
  { id: 'PSAR', label: 'Parabolic SAR (0.02, 0.2)', category: 'Trend Followers', color: '#ec4899' },
  { id: 'PIVOT_POINTS', label: 'Pivot Points (Classic)', category: 'Support & Resistance', color: '#eab308' },
  { id: 'ZIGZAG', label: 'ZigZag Swing Pivots', category: 'Support & Resistance', color: '#14b8a6' },
  { id: 'ICHIMOKU', label: 'Ichimoku Cloud', category: 'Trend Followers', color: '#6366f1' },
  // --- Oscillators & Momentum ---
  { id: 'RSI', label: 'RSI (14 - Momentum)', category: 'Oscillators', color: '#c084fc' },
  { id: 'MACD', label: 'MACD (12, 26, 9)', category: 'Oscillators', color: '#0284c7' },
  { id: 'STOCH_RSI', label: 'Stochastic RSI (14, 14, 3, 3)', category: 'Oscillators', color: '#f43f5e' },
  { id: 'ADX', label: 'ADX / DMI (14)', category: 'Oscillators', color: '#d97706' },
  { id: 'ATR', label: 'ATR (14 - Volatility)', category: 'Volatility & Volume', color: '#14b8a6' },
  { id: 'OBV', label: 'OBV (On-Balance Volume)', category: 'Volatility & Volume', color: '#84cc16' },
];
const OVERLAY_OPTIONS = INDICATOR_OPTIONS;

const CANDLE_OPTIONS = [
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
const PATTERN_OPTIONS = CANDLE_OPTIONS;

export default function TerminalConfigScreen() {
  const [defaultMarket, setDefaultMarket] = useState('INDIAN_EQUITY');
  const [defaultSymbol, setDefaultSymbol] = useState('RELIANCE');
  const [defaultTimeframe, setDefaultTimeframe] = useState('5m');
  const [selectedIndicators, setSelectedIndicators] = useState(['EMA_9', 'EMA_21', 'VWAP']);
  const [selectedCandles, setSelectedCandles] = useState(CANDLE_OPTIONS.map((p) => p.id));

  const [catalogSymbols, setCatalogSymbols] = useState(DEFAULT_SYMBOLS_BY_MARKET['INDIAN_EQUITY']);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // Load User Configuration on Mount
  useEffect(() => {
    setLoading(true);
    api.getUserTerminalConfig()
      .then((cfg) => {
        if (cfg) {
          const mkt = cfg.default_market || 'INDIAN_EQUITY';
          setDefaultMarket(mkt);
          setDefaultSymbol(cfg.default_symbol || 'RELIANCE');
          setDefaultTimeframe(cfg.default_timeframe || '5m');
          const indics = cfg.default_indicators !== undefined ? cfg.default_indicators : cfg.default_overlays;
          if (indics !== undefined && indics !== null) {
            setSelectedIndicators(indics.split(',').map((s) => s.trim()).filter(Boolean));
          }
          const cands = cfg.default_candles !== undefined ? cfg.default_candles : cfg.default_patterns;
          if (cands !== undefined && cands !== null) {
            const parsed = cands.split(',').map((s) => s.trim()).filter(Boolean);
            if (parsed.includes('ALL')) {
              setSelectedCandles(CANDLE_OPTIONS.map((p) => p.id));
            } else {
              setSelectedCandles(parsed);
            }
          }
        }
      })
      .catch((err) => {
        console.warn('Failed to load user terminal config:', err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  // Sync catalog symbols when market changes
  useEffect(() => {
    const fallbackList = DEFAULT_SYMBOLS_BY_MARKET[defaultMarket] || [];
    setCatalogSymbols(fallbackList);
    api.getCatalogSymbols({ market: defaultMarket, activeOnly: true, limit: 100 })
      .then((res) => {
        if (Array.isArray(res) && res.length > 0) {
          setCatalogSymbols(res);
        }
      })
      .catch(() => {});
  }, [defaultMarket]);

  const handleMarketChange = async (newMarket) => {
    setDefaultMarket(newMarket);
    const fallbackList = DEFAULT_SYMBOLS_BY_MARKET[newMarket] || [];
    setCatalogSymbols(fallbackList);
    const def = MARKETS.find((m) => m.id === newMarket)?.defaultSymbol || fallbackList[0]?.symbol || 'RELIANCE';
    setDefaultSymbol(def);

    try {
      const res = await api.getCatalogSymbols({ market: newMarket, activeOnly: true, limit: 100 });
      if (Array.isArray(res) && res.length > 0) {
        setCatalogSymbols(res);
        if (!res.some((item) => item.symbol === def)) {
          setDefaultSymbol(res[0].symbol);
        }
      }
    } catch (err) {
      console.warn('Failed to load dynamic catalog symbols for market:', newMarket, err);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setFeedback(null);
    try {
      await api.updateUserTerminalConfig({
        default_market: defaultMarket,
        default_symbol: defaultSymbol,
        default_timeframe: defaultTimeframe,
        default_indicators: selectedIndicators.join(','),
        default_overlays: selectedIndicators.join(','),
        default_candles: selectedCandles.join(','),
        default_patterns: selectedCandles.join(','),
      });
      setFeedback({ type: 'success', message: 'Terminal preferences saved successfully. MarketView will automatically open with these settings.' });
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Failed to save terminal preferences.' });
    } finally {
      setSaving(false);
    }
  };

  const handleResetDefaults = () => {
    setDefaultMarket('INDIAN_EQUITY');
    setDefaultSymbol('RELIANCE');
    setDefaultTimeframe('5m');
    setSelectedIndicators(['EMA_9', 'EMA_21', 'VWAP']);
    setSelectedCandles(CANDLE_OPTIONS.map((p) => p.id));
    setFeedback({ type: 'info', message: 'Preferences reset to factory defaults. Click Save to persist.' });
  };



  return (
    <Box sx={{ p: { xs: 1.5, sm: 2 }, maxWidth: 1300, margin: '0 auto', color: 'text.primary' }}>
      {/* Feedback Banner */}
      {feedback && (
        <Alert
          severity={feedback.type}
          onClose={() => setFeedback(null)}
          sx={{
            mb: 1.5,
            py: 0.5,
            borderRadius: 2,
            bgcolor: feedback.type === 'success' ? '#1C3A24' : feedback.type === 'error' ? '#3A1C1C' : '#1E293B',
            color: feedback.type === 'success' ? '#32D74B' : feedback.type === 'error' ? '#FF453A' : '#38bdf8',
            border: `1px solid ${feedback.type === 'success' ? '#32D74B' : feedback.type === 'error' ? '#FF453A' : '#38bdf8'}`,
          }}
        >
          {feedback.message}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 6 }}>
          <CircularProgress color="primary" size={28} />
        </Box>
      ) : (
        <Grid container spacing={1.5}>
          {/* 1. Primary Terminal Defaults Card */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Card sx={{ p: 1.8, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 2, height: '100%' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.8 }}>
                <Compass size={16} color="#2563EB" />
                <Typography variant="h6" sx={{ fontSize: '0.88rem', fontWeight: 800 }}>
                  Primary Market &amp; Instrument Defaults
                </Typography>
              </Box>

              <Typography sx={{ fontSize: '0.74rem', color: 'text.secondary', mb: 1.5 }}>
                Baseline market exchange, instrument ticker, and chart timeframe loaded automatically upon access.
              </Typography>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.2 }}>
                {/* Default Market Exchange */}
                <FormControl fullWidth size="small">
                  <InputLabel id="config-market-label" sx={{ color: 'text.secondary', fontSize: '0.78rem' }}>
                    Default Market Exchange
                  </InputLabel>
                  <Select
                    labelId="config-market-label"
                    value={defaultMarket}
                    displayEmpty
                    label="Default Market Exchange"
                    onChange={(e) => handleMarketChange(e.target.value)}
                    renderValue={(selected) => {
                      if (!selected) return <span style={{ color: '#98989D' }}>Select Market</span>;
                      const m = MARKETS.find((x) => x.id === selected);
                      return m ? `${m.label} (${m.exchange})` : selected;
                    }}
                    sx={{ fontSize: '0.8rem', fontWeight: 700, borderRadius: 1.8 }}
                  >
                    <MenuItem value="" disabled sx={{ color: '#98989D' }}>Select Market</MenuItem>
                    {MARKETS.map((m) => (
                      <MenuItem key={m.id} value={m.id} sx={{ fontSize: '0.8rem', py: 0.6 }}>
                        {m.label} ({m.exchange})
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {/* Default Asset Symbol */}
                <FormControl fullWidth size="small">
                  <InputLabel id="config-symbol-label" sx={{ color: 'text.secondary', fontSize: '0.78rem' }}>
                    Default Asset Symbol ({catalogSymbols.length})
                  </InputLabel>
                  <Select
                    labelId="config-symbol-label"
                    value={defaultSymbol}
                    displayEmpty
                    label={`Default Asset Symbol (${catalogSymbols.length})`}
                    onChange={(e) => setDefaultSymbol(e.target.value)}
                    renderValue={(selected) => {
                      if (!selected) return <span style={{ color: '#98989D' }}>Select Asset</span>;
                      return (
                        <Typography sx={{ fontFamily: 'monospace', fontWeight: 800, color: '#2563EB', fontSize: '0.8rem' }}>
                          {selected}
                        </Typography>
                      );
                    }}
                    sx={{ fontSize: '0.8rem', fontWeight: 700, fontFamily: 'monospace', borderRadius: 1.8 }}
                    MenuProps={{ PaperProps: { sx: { bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', maxHeight: 300 } } }}
                  >
                    <MenuItem value="" disabled sx={{ color: '#98989D' }}>Select Asset</MenuItem>
                    {catalogSymbols.map((item) => (
                      <MenuItem key={item.symbol} value={item.symbol} sx={{ fontSize: '0.8rem', display: 'flex', justifyContent: 'space-between', gap: 1.5, py: 0.6 }}>
                        <Box sx={{ display: 'flex', gap: 0.8, alignItems: 'center' }}>
                          <Typography sx={{ fontFamily: 'monospace', fontWeight: 800, color: '#2563EB', fontSize: '0.78rem' }}>{item.symbol}</Typography>
                          <Typography sx={{ fontSize: '0.72rem', color: 'text.secondary' }}>• {item.shortName || item.fullName}</Typography>
                        </Box>
                        <Chip label={item.exchange || item.market} size="small" sx={{ height: 16, fontSize: '0.62rem' }} />
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {/* Default Timeframe */}
                <FormControl fullWidth size="small">
                  <InputLabel id="config-timeframe-label" sx={{ color: 'text.secondary', fontSize: '0.78rem' }}>
                    Default Candle Timeframe
                  </InputLabel>
                  <Select
                    labelId="config-timeframe-label"
                    value={defaultTimeframe}
                    displayEmpty
                    label="Default Candle Timeframe"
                    onChange={(e) => setDefaultTimeframe(e.target.value)}
                    renderValue={(selected) => {
                      if (!selected) return <span style={{ color: '#98989D', fontFamily: 'monospace' }}>1m, 2m, 1h, ...</span>;
                      const tf = TIMEFRAMES.find((t) => t.value === selected);
                      return tf ? tf.label : selected;
                    }}
                    sx={{ fontSize: '0.8rem', fontWeight: 700, fontFamily: 'monospace', borderRadius: 1.8 }}
                  >
                    <MenuItem value="" disabled sx={{ color: '#98989D' }}>1m, 2m, 1h, ...</MenuItem>
                    {TIMEFRAMES.map((tf) => (
                      <MenuItem key={tf.value} value={tf.value} sx={{ fontSize: '0.8rem', py: 0.6, fontFamily: 'monospace' }}>
                        {tf.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Box>
            </Card>
          </Grid>

          {/* 2. Technical Indicators Defaults Card */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Card sx={{ p: 1.8, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 2, height: '100%' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.8 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Sliders size={16} color="#38bdf8" />
                  <Typography variant="h6" sx={{ fontSize: '0.88rem', fontWeight: 800 }}>
                    Active Technical Indicators ({selectedIndicators.length}/{INDICATOR_OPTIONS.length})
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 0.8 }}>
                  <Button
                    size="small"
                    onClick={() => setSelectedIndicators(INDICATOR_OPTIONS.map((o) => o.id))}
                    sx={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'none', color: '#2563EB', p: 0, minWidth: 0 }}
                  >
                    Select All
                  </Button>
                  <Typography sx={{ color: 'text.disabled', fontSize: '0.7rem' }}>|</Typography>
                  <Button
                    size="small"
                    onClick={() => setSelectedIndicators([])}
                    sx={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'none', color: '#f43f5e', p: 0, minWidth: 0 }}
                  >
                    Clear All
                  </Button>
                </Box>
              </Box>

              <Typography sx={{ fontSize: '0.74rem', color: 'text.secondary', mb: 1.2 }}>
                Mathematical indicators and trend lines to synthesize immediately onto the chart canvas.
              </Typography>

              <FormGroup sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(185px, 1fr))', gap: 0.4, maxHeight: 210, overflowY: 'auto', pr: 0.5 }}>
                {INDICATOR_OPTIONS.map((opt) => {
                  const isChecked = selectedIndicators.includes(opt.id);
                  return (
                    <FormControlLabel
                      key={opt.id}
                      control={
                        <Checkbox
                          size="small"
                          checked={isChecked}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedIndicators((prev) => [...prev, opt.id]);
                            } else {
                              setSelectedIndicators((prev) => prev.filter((id) => id !== opt.id));
                            }
                          }}
                          sx={{ color: opt.color, '&.Mui-checked': { color: opt.color }, p: 0.4 }}
                        />
                      }
                      label={
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', gap: 0.8, pr: 0.5 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.6 }}>
                            <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: opt.color }} />
                            <Typography sx={{ fontSize: '0.74rem', fontWeight: isChecked ? 700 : 500 }}>{opt.label}</Typography>
                          </Box>
                          <IndicatorIconSvg id={opt.id} color={opt.color} size={18} />
                        </Box>
                      }
                      sx={{ mx: 0, width: '100%', py: 0.1 }}
                    />
                  );
                })}
              </FormGroup>
            </Card>
          </Grid>

          {/* 3. Candle Pattern Recognition Defaults Card */}
          <Grid size={{ xs: 12 }}>
            <Card sx={{ p: 1.8, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.8 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Layers size={16} color="#32D74B" />
                  <Typography variant="h6" sx={{ fontSize: '0.88rem', fontWeight: 800 }}>
                    Default Candle Pattern Filters ({selectedCandles.length}/{CANDLE_OPTIONS.length})
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 0.8 }}>
                  <Button
                    size="small"
                    onClick={() => setSelectedCandles(CANDLE_OPTIONS.map((p) => p.id))}
                    sx={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'none', color: '#32D74B', p: 0, minWidth: 0 }}
                  >
                    Select All
                  </Button>
                  <Typography sx={{ color: 'text.disabled', fontSize: '0.7rem' }}>|</Typography>
                  <Button
                    size="small"
                    onClick={() => setSelectedCandles([])}
                    sx={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'none', color: '#f43f5e', p: 0, minWidth: 0 }}
                  >
                    Clear All
                  </Button>
                </Box>
              </Box>

              <Typography sx={{ fontSize: '0.74rem', color: 'text.secondary', mb: 1.2 }}>
                Algorithmic candlestick patterns that automatically trigger chart markers and telemetry badges upon load.
              </Typography>

              <FormGroup sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(175px, 1fr))', gap: 0.4 }}>
                {CANDLE_OPTIONS.map((p) => {
                  const isChecked = selectedCandles.includes(p.id);
                  return (
                    <FormControlLabel
                      key={p.id}
                      control={
                        <Checkbox
                          size="small"
                          checked={isChecked}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedCandles((prev) => [...prev, p.id]);
                            } else {
                              setSelectedCandles((prev) => prev.filter((id) => id !== p.id));
                            }
                          }}
                          sx={{ color: '#32D74B', '&.Mui-checked': { color: '#32D74B' }, p: 0.4 }}
                        />
                      }
                      label={
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', gap: 0.8, pr: 0.5 }}>
                          <Typography sx={{ fontSize: '0.74rem', color: isChecked ? 'text.primary' : 'text.secondary', fontWeight: isChecked ? 700 : 500 }}>
                            {p.label}
                          </Typography>
                          <CandleIconSvg id={p.id} size={16} />
                        </Box>
                      }
                      sx={{ mx: 0, width: '100%', py: 0.1 }}
                    />
                  );
                })}
              </FormGroup>
            </Card>
          </Grid>

          {/* 4. Action Buttons Bar */}
          <Grid size={{ xs: 12 }}>
            <Box sx={{ display: 'flex', gap: 1.5, justifyContent: 'flex-end', alignItems: 'center', pt: 0.5 }}>
              <Button
                variant="outlined"
                onClick={handleResetDefaults}
                disabled={saving}
                size="small"
                sx={{
                  borderColor: 'divider',
                  color: 'text.secondary',
                  fontWeight: 700,
                  fontSize: '0.78rem',
                  textTransform: 'none',
                  borderRadius: 1.8,
                  px: 2,
                  py: 0.7,
                  '&:hover': { borderColor: 'text.primary', color: 'text.primary' },
                }}
                startIcon={<RotateCcw size={14} />}
              >
                Reset to Defaults
              </Button>

              <Button
                variant="contained"
                onClick={handleSave}
                disabled={saving}
                size="small"
                sx={{
                  bgcolor: '#2563EB',
                  color: '#ffffff',
                  fontWeight: 700,
                  fontSize: '0.78rem',
                  textTransform: 'none',
                  borderRadius: 1.8,
                  px: 2.8,
                  py: 0.7,
                  '&:hover': { bgcolor: '#1d4ed8' },
                }}
                startIcon={saving ? <CircularProgress size={14} color="inherit" /> : <Save size={14} />}
              >
                {saving ? 'Saving...' : 'Save Preferences'}
              </Button>
            </Box>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}
