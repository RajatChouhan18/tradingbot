import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Typography,
  Chip,
  Alert,
  CircularProgress,
  Paper,
  Checkbox,
  FormControlLabel,
  Grid,
  IconButton,
  Divider,
} from '@mui/material';
import {
  X,
  Plus,
  Play,
  CheckCircle2,
  AlertTriangle,
  Zap,
  TrendingUp,
  BarChart2,
  Activity,
  Send,
} from 'lucide-react';
import { api } from '../../api';

const MARKETS = [
  { code: 'INDIAN_EQUITY', label: 'Indian Equities (NSE / BSE)' },
  { code: 'US_EQUITY', label: 'US Equities (NASDAQ / NYSE)' },
  { code: 'CRYPTO', label: 'Cryptocurrency (Binance)' },
  { code: 'FOREX', label: 'Foreign Exchange (FX_IDC)' },
  { code: 'MCX', label: 'MCX Commodities' },
];

const TIMEFRAMES = ['1m', '3m', '5m', '15m', '30m', '1h', '1d'];

const CANDLE_PATTERN_OPTIONS = [
  { id: 'HAMMER', label: 'Hammer (Bullish Reversal)' },
  { id: 'ENGULFING_BULLISH', label: 'Bullish Engulfing' },
  { id: 'ENGULFING_BEARISH', label: 'Bearish Engulfing' },
  { id: 'MORNING_STAR', label: 'Morning Star' },
  { id: 'EVENING_STAR', label: 'Evening Star' },
  { id: 'SHOOTING_STAR', label: 'Shooting Star' },
  { id: 'DOJI', label: 'Doji (Indecision)' },
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

export default function CreateEventTriggerModal({
  open,
  onClose,
  onTriggerSaved,
  editTrigger = null,
  showToast,
}) {
  const isEditing = Boolean(editTrigger);

  // Form State
  const [name, setName] = useState('');
  const [symbol, setSymbol] = useState('RELIANCE');
  const [market, setMarket] = useState('INDIAN_EQUITY');
  const [catalogSymbols, setCatalogSymbols] = useState(DEFAULT_SYMBOLS_BY_MARKET['INDIAN_EQUITY']);
  const [timeframe, setTimeframe] = useState('5m');
  const [triggerType, setTriggerType] = useState('PRICE_SPIKE');
  const [status, setStatus] = useState('ACTIVE');

  // Condition Sub-fields
  const [spikePct, setSpikePct] = useState(1.5);
  const [spikeLookback, setSpikeLookback] = useState(3);
  const [spikeDirection, setSpikeDirection] = useState('BULLISH');

  const [volMultiplier, setVolMultiplier] = useState(2.0);
  const [volPeriod, setVolPeriod] = useState(20);

  const [srLevel, setSrLevel] = useState(2500.0);
  const [srLevelType, setSrLevelType] = useState('RESISTANCE');
  const [srBreakType, setSrBreakType] = useState('BREAKOUT');
  const [srBufferPct, setSrBufferPct] = useState(0.1);

  const [selectedPatterns, setSelectedPatterns] = useState(['ENGULFING_BULLISH', 'HAMMER']);
  const [patternSentiment, setPatternSentiment] = useState('BULLISH');

  const [indicatorType, setIndicatorType] = useState('RSI');
  const [rsiThreshold, setRsiThreshold] = useState(70.0);
  const [rsiOperator, setRsiOperator] = useState('GREATER_THAN');
  const [emaFast, setEmaFast] = useState(9);
  const [emaSlow, setEmaSlow] = useState(21);
  const [crossDirection, setCrossDirection] = useState('GOLDEN');

  // Channels
  const [channels, setChannels] = useState(['TELEGRAM']);
  const [telegramChatId, setTelegramChatId] = useState('');
  const [whatsappNumber, setWhatsappNumber] = useState('');
  const [webhookUrl, setWebhookUrl] = useState('');

  // Simulation & Submission states
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationResult, setSimulationResult] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const loadMarketSymbols = async (mkt, currentSym = null) => {
    try {
      const data = await api.listMarketSymbols({ market: mkt });
      const dynamicList = (data || []).map((item) => ({
        symbol: item.symbol,
        shortName: item.description || item.symbol,
        exchange: item.exchange || mkt,
      }));
      const fallback = DEFAULT_SYMBOLS_BY_MARKET[mkt] || [];
      const combined = dynamicList.length > 0 ? dynamicList : fallback;
      setCatalogSymbols(combined);
      if (currentSym && combined.some((s) => s.symbol === currentSym)) {
        setSymbol(currentSym);
      } else if (combined.length > 0) {
        setSymbol(combined[0].symbol);
      }
    } catch {
      const fallback = DEFAULT_SYMBOLS_BY_MARKET[mkt] || [];
      setCatalogSymbols(fallback);
      if (currentSym && fallback.some((s) => s.symbol === currentSym)) {
        setSymbol(currentSym);
      } else if (fallback.length > 0) {
        setSymbol(fallback[0].symbol);
      }
    }
  };

  const handleMarketChange = (newMarket) => {
    setMarket(newMarket);
    loadMarketSymbols(newMarket);
  };

  useEffect(() => {
    if (open) {
      const initMarket = editTrigger?.market || 'INDIAN_EQUITY';
      const initSymbol = editTrigger?.symbol || (DEFAULT_SYMBOLS_BY_MARKET[initMarket]?.[0]?.symbol || 'RELIANCE');
      setMarket(initMarket);
      setSymbol(initSymbol);
      loadMarketSymbols(initMarket, initSymbol);

      if (editTrigger) {
        setName(editTrigger.name || '');
        setTimeframe(editTrigger.timeframe || '5m');
        setTriggerType(editTrigger.trigger_type || 'PRICE_SPIKE');
        setStatus(editTrigger.status || 'ACTIVE');

        const cfg = editTrigger.threshold_config || {};
        if (editTrigger.trigger_type === 'PRICE_SPIKE') {
          setSpikePct(cfg.spike_pct || 1.5);
          setSpikeLookback(cfg.lookback_bars || 3);
          setSpikeDirection(cfg.direction || 'BULLISH');
        } else if (editTrigger.trigger_type === 'VOLUME_SPIKE') {
          setVolMultiplier(cfg.volume_multiplier || 2.0);
          setVolPeriod(cfg.sma_period || 20);
        } else if (editTrigger.trigger_type === 'SR_BREAK') {
          setSrLevel(cfg.level || 2500.0);
          setSrLevelType(cfg.level_type || 'RESISTANCE');
          setSrBreakType(cfg.break_type || 'BREAKOUT');
          setSrBufferPct(cfg.buffer_pct || 0.1);
        } else if (editTrigger.trigger_type === 'CANDLE_PATTERN') {
          setSelectedPatterns(cfg.patterns || ['ENGULFING_BULLISH', 'HAMMER']);
          setPatternSentiment(cfg.sentiment || 'BULLISH');
        } else if (editTrigger.trigger_type === 'INDICATOR_CROSS') {
          setIndicatorType(cfg.indicator || 'RSI');
          setRsiThreshold(cfg.rsi_threshold || 70.0);
          setRsiOperator(cfg.rsi_operator || 'GREATER_THAN');
          setEmaFast(cfg.ema_fast || 9);
          setEmaSlow(cfg.ema_slow || 21);
          setCrossDirection(cfg.cross_direction || 'GOLDEN');
        }

        setChannels(editTrigger.channels || ['TELEGRAM']);
        const targets = editTrigger.channel_targets || {};
        setTelegramChatId(targets.telegram_chat_id || '');
        setWhatsappNumber(targets.whatsapp_number || '');
        setWebhookUrl(targets.webhook_url || '');
      } else {
        // Defaults
        setName('');
        setSymbol('RELIANCE');
        setMarket('INDIAN_EQUITY');
        setTimeframe('5m');
        setTriggerType('PRICE_SPIKE');
        setStatus('ACTIVE');
        setSpikePct(1.5);
        setSpikeLookback(3);
        setSpikeDirection('BULLISH');
        setChannels(['TELEGRAM']);
        setTelegramChatId('');
        setWhatsappNumber('');
        setWebhookUrl('');
      }
      setSimulationResult(null);
      setErrorMsg(null);
      setIsSimulating(false);
      setIsSubmitting(false);
    }
  }, [open, editTrigger]);

  const toggleChannel = (channelName) => {
    setChannels((prev) =>
      prev.includes(channelName) ? prev.filter((c) => c !== channelName) : [...prev, channelName]
    );
  };

  const togglePattern = (patternId) => {
    setSelectedPatterns((prev) =>
      prev.includes(patternId) ? prev.filter((p) => p !== patternId) : [...prev, patternId]
    );
  };

  const buildThresholdConfig = () => {
    if (triggerType === 'PRICE_SPIKE') {
      return {
        spike_pct: Number(spikePct),
        lookback_bars: Number(spikeLookback),
        direction: spikeDirection,
      };
    }
    if (triggerType === 'VOLUME_SPIKE') {
      return {
        volume_multiplier: Number(volMultiplier),
        sma_period: Number(volPeriod),
      };
    }
    if (triggerType === 'SR_BREAK') {
      return {
        level: Number(srLevel),
        level_type: srLevelType,
        break_type: srBreakType,
        buffer_pct: Number(srBufferPct),
      };
    }
    if (triggerType === 'CANDLE_PATTERN') {
      return {
        patterns: selectedPatterns,
        sentiment: patternSentiment,
      };
    }
    if (triggerType === 'INDICATOR_CROSS') {
      return {
        indicator: indicatorType,
        rsi_operator: rsiOperator,
        rsi_threshold: Number(rsiThreshold),
        ema_fast: Number(emaFast),
        ema_slow: Number(emaSlow),
        cross_direction: crossDirection,
      };
    }
    return {};
  };

  const handleSimulateRule = async () => {
    setIsSimulating(true);
    setErrorMsg(null);
    setSimulationResult(null);

    try {
      const config = buildThresholdConfig();
      const payload = {
        symbol: symbol.trim().toUpperCase(),
        market,
        timeframe,
        trigger_type: triggerType,
        threshold_config: config,
      };

      const res = await api.simulateEventTrigger(payload);
      setSimulationResult(res);
      if (showToast) {
        showToast(
          res.matched ? 'Condition Match Detected in Live Test!' : 'Condition not currently met.',
          res.matched ? 'success' : 'info'
        );
      }
    } catch (err) {
      setErrorMsg(err.message || 'Simulation failed. Check ticker symbol or market provider.');
    } finally {
      setIsSimulating(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      setErrorMsg('Please enter a descriptive name for this trigger.');
      return;
    }
    if (!symbol.trim()) {
      setErrorMsg('Please enter an asset symbol / ticker.');
      return;
    }
    if (channels.length === 0) {
      setErrorMsg('Please select at least one notification dispatch channel.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    const config = buildThresholdConfig();
    const channelTargets = {};
    if (telegramChatId.trim()) channelTargets.telegram_chat_id = telegramChatId.trim();
    if (whatsappNumber.trim()) channelTargets.whatsapp_number = whatsappNumber.trim();
    if (webhookUrl.trim()) channelTargets.webhook_url = webhookUrl.trim();

    const payload = {
      name: name.trim(),
      symbol: symbol.trim().toUpperCase(),
      market,
      timeframe,
      trigger_type: triggerType,
      threshold_config: config,
      channels,
      channel_targets: channelTargets,
      status,
      is_standalone: true,
    };

    try {
      let saved;
      if (isEditing) {
        saved = await api.updateEventTrigger(editTrigger.id, payload);
        if (showToast) showToast(`Event WatchDog '${saved.name}' updated successfully!`, 'success');
      } else {
        saved = await api.createEventTrigger(payload);
        if (showToast) showToast(`Event WatchDog '${saved.name}' created and activated!`, 'success');
      }
      if (onTriggerSaved) onTriggerSaved(saved);
      onClose();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to save event trigger.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
          backgroundImage: 'none',
          boxShadow: '0 20px 40px rgba(0,0,0,0.4)',
        },
      }}
    >
      <DialogTitle
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          pb: 1,
          pt: 2.5,
          px: 3,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={{
              width: 38,
              height: 38,
              borderRadius: 2,
              bgcolor: 'primary.main',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Zap size={20} />
          </Box>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1.15rem' }}>
              {isEditing ? 'Edit Event WatchDog' : 'New Event WatchDog'}
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>
              Event WatchDogs monitor live price action and dispatch multi-channel alerts (Telegram, WhatsApp, Webhooks) without trade execution.
            </Typography>
          </Box>
        </Box>
        <IconButton onClick={onClose} size="small" sx={{ color: 'text.secondary' }}>
          <X size={20} />
        </IconButton>
      </DialogTitle>

      <Divider />

      <DialogContent sx={{ p: 3 }}>
        {errorMsg && (
          <Alert severity="error" icon={<AlertTriangle size={18} />} sx={{ mb: 2.5, borderRadius: 2 }}>
            {errorMsg}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
          {/* Section 1: Basic Identifiers */}
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Event WatchDog Name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Nifty 5-min Spike Alert"
                fullWidth
                size="small"
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth size="small">
                <InputLabel>Target Market</InputLabel>
                <Select
                  value={market}
                  label="Target Market"
                  onChange={(e) => handleMarketChange(e.target.value)}
                >
                  {MARKETS.map((m) => (
                    <MenuItem key={m.code} value={m.code}>
                      {m.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={4}>
              <FormControl fullWidth size="small">
                <InputLabel id="event-modal-symbol-select-label" sx={{ fontSize: '0.8rem' }}>
                  Asset ({catalogSymbols.length})
                </InputLabel>
                <Select
                  labelId="event-modal-symbol-select-label"
                  value={symbol}
                  label={`Asset (${catalogSymbols.length})`}
                  onChange={(e) => setSymbol(e.target.value)}
                  renderValue={(selected) => (
                    <Typography sx={{ fontFamily: 'monospace', fontWeight: 800, fontSize: '0.82rem', color: '#60a5fa' }}>
                      {selected}
                    </Typography>
                  )}
                  sx={{
                    fontFamily: 'monospace',
                    fontWeight: 700,
                    fontSize: '0.82rem',
                    borderRadius: 1.8,
                  }}
                  MenuProps={{
                    PaperProps: {
                      sx: {
                        maxHeight: 340,
                      },
                    },
                  }}
                >
                  {(catalogSymbols.length > 0 ? catalogSymbols : (DEFAULT_SYMBOLS_BY_MARKET[market] || [])).map((item) => (
                    <MenuItem
                      key={item.symbol}
                      value={item.symbol}
                      sx={{
                        fontSize: '0.8rem',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        gap: 1.5,
                        py: 0.7,
                      }}
                    >
                      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', minWidth: 0 }}>
                        <Typography sx={{ fontFamily: 'monospace', fontWeight: 800, fontSize: '0.8rem', color: '#60a5fa' }}>
                          {item.symbol}
                        </Typography>
                        <Typography sx={{ fontSize: '0.72rem', color: 'text.secondary', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {item.shortName || item.description || item.fullName}
                        </Typography>
                      </Box>
                      <Chip
                        label={item.exchange || item.market || market}
                        size="small"
                        sx={{
                          height: 18,
                          fontSize: '0.62rem',
                          fontWeight: 700,
                          bgcolor: 'rgba(255,255,255,0.06)',
                          color: 'text.secondary',
                        }}
                      />
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Base Timeframe</InputLabel>
                <Select
                  value={timeframe}
                  label="Base Timeframe"
                  onChange={(e) => setTimeframe(e.target.value)}
                >
                  {TIMEFRAMES.map((tf) => (
                    <MenuItem key={tf} value={tf}>
                      {tf}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Signal Condition Type</InputLabel>
                <Select
                  value={triggerType}
                  label="Signal Condition Type"
                  onChange={(e) => setTriggerType(e.target.value)}
                >
                  <MenuItem value="PRICE_SPIKE">⚡ Price Spike / Crash</MenuItem>
                  <MenuItem value="VOLUME_SPIKE">📊 Volume Surge Multiplier</MenuItem>
                  <MenuItem value="SR_BREAK">📈 Support / Resistance Break</MenuItem>
                  <MenuItem value="CANDLE_PATTERN">🕯️ Candlestick Pattern</MenuItem>
                  <MenuItem value="INDICATOR_CROSS">🎯 Indicator Cross (RSI / EMA)</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>

          {/* Section 2: Dynamic Threshold Rule Configuration */}
          <Paper
            variant="outlined"
            sx={{
              p: 2.5,
              borderRadius: 2.5,
              bgcolor: (theme) => (theme.palette.mode === 'dark' ? 'rgba(30, 41, 59, 0.4)' : '#f8fafc'),
            }}
          >
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
              <TrendingUp size={16} /> Rule Condition Thresholds
            </Typography>

            {/* 1. PRICE_SPIKE */}
            {triggerType === 'PRICE_SPIKE' && (
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="Spike Threshold (%)"
                    type="number"
                    value={spikePct}
                    onChange={(e) => setSpikePct(e.target.value)}
                    size="small"
                    fullWidth
                    inputProps={{ step: '0.1', min: '0.01' }}
                    helperText="Percentage price shift"
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="Lookback Bars"
                    type="number"
                    value={spikeLookback}
                    onChange={(e) => setSpikeLookback(e.target.value)}
                    size="small"
                    fullWidth
                    inputProps={{ min: '1', max: '50' }}
                    helperText="Over how many candles"
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Direction</InputLabel>
                    <Select
                      value={spikeDirection}
                      label="Direction"
                      onChange={(e) => setSpikeDirection(e.target.value)}
                    >
                      <MenuItem value="BULLISH">Bullish (Surge Up)</MenuItem>
                      <MenuItem value="BEARISH">Bearish (Crash Down)</MenuItem>
                      <MenuItem value="ANY">Any Direction</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>
            )}

            {/* 2. VOLUME_SPIKE */}
            {triggerType === 'VOLUME_SPIKE' && (
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Volume Multiplier (x)"
                    type="number"
                    value={volMultiplier}
                    onChange={(e) => setVolMultiplier(e.target.value)}
                    size="small"
                    fullWidth
                    inputProps={{ step: '0.1', min: '1.1' }}
                    helperText="e.g. 2.0x of baseline volume"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="SMA Baseline Period"
                    type="number"
                    value={volPeriod}
                    onChange={(e) => setVolPeriod(e.target.value)}
                    size="small"
                    fullWidth
                    inputProps={{ min: '5', max: '100' }}
                    helperText="Default 20-period moving average"
                  />
                </Grid>
              </Grid>
            )}

            {/* 3. SR_BREAK */}
            {triggerType === 'SR_BREAK' && (
              <Grid container spacing={2}>
                <Grid item xs={12} sm={3}>
                  <TextField
                    label="Level Price"
                    type="number"
                    value={srLevel}
                    onChange={(e) => setSrLevel(e.target.value)}
                    size="small"
                    fullWidth
                    inputProps={{ step: '0.01', style: { fontFamily: 'monospace', fontWeight: 700 } }}
                  />
                </Grid>
                <Grid item xs={12} sm={3}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Level Type</InputLabel>
                    <Select
                      value={srLevelType}
                      label="Level Type"
                      onChange={(e) => setSrLevelType(e.target.value)}
                    >
                      <MenuItem value="RESISTANCE">Resistance</MenuItem>
                      <MenuItem value="SUPPORT">Support</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={3}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Break Type</InputLabel>
                    <Select
                      value={srBreakType}
                      label="Break Type"
                      onChange={(e) => setSrBreakType(e.target.value)}
                    >
                      <MenuItem value="BREAKOUT">Breakout (Cross Above)</MenuItem>
                      <MenuItem value="BREAKDOWN">Breakdown (Cross Below)</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={3}>
                  <TextField
                    label="Tolerance Buffer (%)"
                    type="number"
                    value={srBufferPct}
                    onChange={(e) => setSrBufferPct(e.target.value)}
                    size="small"
                    fullWidth
                    inputProps={{ step: '0.05', min: '0.0' }}
                  />
                </Grid>
              </Grid>
            )}

            {/* 4. CANDLE_PATTERN */}
            {triggerType === 'CANDLE_PATTERN' && (
              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, display: 'block', mb: 1 }}>
                  Select Patterns to Watch For:
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                  {CANDLE_PATTERN_OPTIONS.map((pat) => {
                    const isSelected = selectedPatterns.includes(pat.id);
                    return (
                      <Chip
                        key={pat.id}
                        label={pat.label}
                        onClick={() => togglePattern(pat.id)}
                        color={isSelected ? 'primary' : 'default'}
                        variant={isSelected ? 'filled' : 'outlined'}
                        sx={{ fontWeight: 600, cursor: 'pointer' }}
                      />
                    );
                  })}
                </Box>
                <FormControl size="small" sx={{ width: 220 }}>
                  <InputLabel>Sentiment Filter</InputLabel>
                  <Select
                    value={patternSentiment}
                    label="Sentiment Filter"
                    onChange={(e) => setPatternSentiment(e.target.value)}
                  >
                    <MenuItem value="BULLISH">Bullish Only</MenuItem>
                    <MenuItem value="BEARISH">Bearish Only</MenuItem>
                    <MenuItem value="ANY">Any Sentiment</MenuItem>
                  </Select>
                </FormControl>
              </Box>
            )}

            {/* 5. INDICATOR_CROSS */}
            {triggerType === 'INDICATOR_CROSS' && (
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Indicator</InputLabel>
                    <Select
                      value={indicatorType}
                      label="Indicator"
                      onChange={(e) => setIndicatorType(e.target.value)}
                    >
                      <MenuItem value="RSI">RSI (Relative Strength)</MenuItem>
                      <MenuItem value="EMA_CROSS">EMA Cross (Fast / Slow)</MenuItem>
                      <MenuItem value="VWAP_CROSS">Price vs VWAP Cross</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                {indicatorType === 'RSI' && (
                  <>
                    <Grid item xs={12} sm={4}>
                      <FormControl fullWidth size="small">
                        <InputLabel>Condition Operator</InputLabel>
                        <Select
                          value={rsiOperator}
                          label="Condition Operator"
                          onChange={(e) => setRsiOperator(e.target.value)}
                        >
                          <MenuItem value="GREATER_THAN">Greater Than (&gt; Overbought)</MenuItem>
                          <MenuItem value="LESS_THAN">Less Than (&lt; Oversold)</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <TextField
                        label="RSI Threshold Level"
                        type="number"
                        value={rsiThreshold}
                        onChange={(e) => setRsiThreshold(e.target.value)}
                        size="small"
                        fullWidth
                        inputProps={{ min: '0', max: '100', step: '1' }}
                      />
                    </Grid>
                  </>
                )}

                {indicatorType === 'EMA_CROSS' && (
                  <>
                    <Grid item xs={12} sm={2.6}>
                      <TextField
                        label="Fast EMA"
                        type="number"
                        value={emaFast}
                        onChange={(e) => setEmaFast(e.target.value)}
                        size="small"
                        fullWidth
                      />
                    </Grid>
                    <Grid item xs={12} sm={2.6}>
                      <TextField
                        label="Slow EMA"
                        type="number"
                        value={emaSlow}
                        onChange={(e) => setEmaSlow(e.target.value)}
                        size="small"
                        fullWidth
                      />
                    </Grid>
                    <Grid item xs={12} sm={2.8}>
                      <FormControl fullWidth size="small">
                        <InputLabel>Cross Direction</InputLabel>
                        <Select
                          value={crossDirection}
                          label="Cross Direction"
                          onChange={(e) => setCrossDirection(e.target.value)}
                        >
                          <MenuItem value="GOLDEN">Golden Cross (Above)</MenuItem>
                          <MenuItem value="DEATH">Death Cross (Below)</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                  </>
                )}
              </Grid>
            )}
          </Paper>

          {/* Section 3: Notification Dispatch Targets */}
          <Paper
            variant="outlined"
            sx={{
              p: 2.5,
              borderRadius: 2.5,
              bgcolor: (theme) => (theme.palette.mode === 'dark' ? 'rgba(30, 41, 59, 0.4)' : '#f8fafc'),
            }}
          >
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
              <Send size={16} /> Notification Dispatch Channels
            </Typography>

            <Box sx={{ display: 'flex', gap: 3, mb: 2 }}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={channels.includes('TELEGRAM')}
                    onChange={() => toggleChannel('TELEGRAM')}
                    color="primary"
                  />
                }
                label="Telegram Bot"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={channels.includes('WHATSAPP')}
                    onChange={() => toggleChannel('WHATSAPP')}
                    color="success"
                  />
                }
                label="WhatsApp"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={channels.includes('WEBHOOK')}
                    onChange={() => toggleChannel('WEBHOOK')}
                    color="warning"
                  />
                }
                label="Custom Webhook"
              />
            </Box>

            <Grid container spacing={2}>
              {channels.includes('TELEGRAM') && (
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="Telegram Chat ID (Optional)"
                    placeholder="e.g. -10012345678"
                    value={telegramChatId}
                    onChange={(e) => setTelegramChatId(e.target.value)}
                    size="small"
                    fullWidth
                    helperText="Leave empty to use global default"
                  />
                </Grid>
              )}
              {channels.includes('WHATSAPP') && (
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="WhatsApp Phone Number"
                    placeholder="e.g. +919876543210"
                    value={whatsappNumber}
                    onChange={(e) => setWhatsappNumber(e.target.value)}
                    size="small"
                    fullWidth
                    helperText="E.164 format with country code"
                  />
                </Grid>
              )}
              {channels.includes('WEBHOOK') && (
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="Webhook POST URL"
                    placeholder="https://api.myapp.com/events"
                    value={webhookUrl}
                    onChange={(e) => setWebhookUrl(e.target.value)}
                    size="small"
                    fullWidth
                    helperText="Target endpoint receiving JSON payload"
                  />
                </Grid>
              )}
            </Grid>
          </Paper>

          {/* Section 4: Live Simulation Preview Card */}
          {simulationResult && (
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                borderRadius: 2,
                bgcolor: simulationResult.matched
                  ? (theme) => (theme.palette.mode === 'dark' ? 'rgba(16, 185, 129, 0.1)' : '#f0fdf4')
                  : (theme) => (theme.palette.mode === 'dark' ? 'rgba(148, 163, 184, 0.08)' : '#f8fafc'),
                borderColor: simulationResult.matched ? '#10b981' : 'divider',
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {simulationResult.matched ? (
                    <CheckCircle2 size={18} color="#059669" />
                  ) : (
                    <Activity size={18} color="#94a3b8" />
                  )}
                  <Typography
                    sx={{
                      fontWeight: 700,
                      fontSize: '0.9rem',
                      color: simulationResult.matched ? '#059669' : 'text.secondary',
                    }}
                  >
                    {simulationResult.matched ? 'Condition Match Confirmed!' : 'Rule Condition Not Met'}
                  </Typography>
                </Box>
                <Chip
                  label={`${simulationResult.latency_ms}ms Live Eval`}
                  size="small"
                  sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}
                />
              </Box>

              <Typography variant="body2" sx={{ color: 'text.primary', mb: 1 }}>
                {simulationResult.evaluation_message}
              </Typography>

              {simulationResult.last_candle && (
                <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
                  Last Bar Close: {simulationResult.last_candle.close} | Vol: {simulationResult.last_candle.volume}
                </Typography>
              )}
            </Paper>
          )}

          {/* Dialog Action Buttons */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
            <Button
              type="button"
              variant="outlined"
              color="info"
              onClick={handleSimulateRule}
              disabled={isSimulating}
              startIcon={isSimulating ? <CircularProgress size={16} color="inherit" /> : <Play size={16} />}
              sx={{ textTransform: 'none', fontWeight: 700 }}
            >
              {isSimulating ? 'Evaluating Live...' : 'Dry-Run Simulator'}
            </Button>

            <Box sx={{ display: 'flex', gap: 1.5 }}>
              <Button onClick={onClose} variant="outlined" sx={{ textTransform: 'none', fontWeight: 600 }}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="contained"
                color="primary"
                disabled={isSubmitting}
                startIcon={isSubmitting ? <CircularProgress size={16} color="inherit" /> : <Plus size={16} />}
                sx={{ textTransform: 'none', fontWeight: 700, px: 3 }}
              >
                {isSubmitting ? 'Saving...' : isEditing ? 'Update Event WatchDog' : 'Create Event WatchDog'}
              </Button>
            </Box>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
