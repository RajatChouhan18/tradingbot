import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Switch,
  Tooltip,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  InputAdornment,
  Grid,
  Card,
} from '@mui/material';
import {
  Plus,
  Search,
  RefreshCw,
  Edit2,
  Trash2,
  Eye,
  Activity,
  Send,
  Radio,
  Cpu,
} from 'lucide-react';
import { api } from '../../api';
import CreateEventTriggerModal from './CreateEventTriggerModal';
import EventDetailsModal from './EventDetailsModal';

const MARKETS = [
  { code: '', label: 'All Markets' },
  { code: 'INDIAN_EQUITY', label: 'Indian Equities (NSE)' },
  { code: 'US_EQUITY', label: 'US Equities (NASDAQ/NYSE)' },
  { code: 'CRYPTO', label: 'Cryptocurrency (Binance)' },
  { code: 'FOREX', label: 'Forex (FX_IDC)' },
  { code: 'MCX', label: 'MCX Commodities' },
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

const getAllDefaultSymbols = () => {
  const all = [];
  Object.values(DEFAULT_SYMBOLS_BY_MARKET).forEach((list) => {
    list.forEach((item) => {
      if (!all.some((x) => x.symbol === item.symbol)) {
        all.push(item);
      }
    });
  });
  return all;
};

const TRIGGER_TYPES = [
  { code: '', label: 'All Signal Types' },
  { code: 'PRICE_SPIKE', label: 'Price Spike / Crash' },
  { code: 'VOLUME_SPIKE', label: 'Volume Surge Multiplier' },
  { code: 'SR_BREAK', label: 'Support / Resistance Break' },
  { code: 'CANDLE_PATTERN', label: 'Candlestick Pattern' },
  { code: 'INDICATOR_CROSS', label: 'Indicator Cross (RSI/EMA)' },
];

const STATUSES = [
  { code: '', label: 'All Statuses' },
  { code: 'ACTIVE', label: 'Active Only' },
  { code: 'PAUSED', label: 'Paused Only' },
];

const getMarketChipInfo = (market) => {
  if (market === 'INDIAN_EQUITY') return { label: 'NSE', color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.12)' };
  if (market === 'US_EQUITY') return { label: 'NASDAQ', color: '#a855f7', bg: 'rgba(168, 85, 247, 0.12)' };
  if (market === 'CRYPTO') return { label: 'BINANCE', color: '#fbbf24', bg: 'rgba(251, 191, 36, 0.12)' };
  if (market === 'FOREX') return { label: 'FX', color: '#34d399', bg: 'rgba(52, 211, 153, 0.12)' };
  if (market === 'MCX') return { label: 'MCX', color: '#fb923c', bg: 'rgba(251, 146, 60, 0.12)' };
  return { label: market || 'MKT', color: '#94a3b8', bg: 'rgba(148, 163, 184, 0.12)' };
};

const getTriggerTypeChip = (type) => {
  switch (type) {
    case 'PRICE_SPIKE':
      return { label: 'Price Spike', color: 'warning' };
    case 'VOLUME_SPIKE':
      return { label: 'Volume Surge', color: 'info' };
    case 'SR_BREAK':
      return { label: 'S/R Breakout', color: 'secondary' };
    case 'CANDLE_PATTERN':
      return { label: 'Candle Pattern', color: 'primary' };
    case 'INDICATOR_CROSS':
      return { label: 'Indicator Cross', color: 'success' };
    default:
      return { label: type || 'Signal', color: 'default' };
  }
};

export default function EventTriggersScreen({ showToast }) {
  // Triggers List State
  const [triggers, setTriggers] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Reactive Filters (Instant onChange)
  const [selectedMarket, setSelectedMarket] = useState('');
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [catalogSymbols, setCatalogSymbols] = useState(getAllDefaultSymbols());
  const [selectedType, setSelectedType] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // Modals State
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editTrigger, setEditTrigger] = useState(null);
  const [detailsTriggerId, setDetailsTriggerId] = useState(null);

  // Delete Confirmation State
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Load catalog symbols for market filter
  const loadMarketSymbols = useCallback(async (mkt) => {
    if (!mkt) {
      // All markets
      try {
        const data = await api.listMarketSymbols();
        if (data && data.length > 0) {
          const list = data.map((item) => ({
            symbol: item.symbol,
            shortName: item.description || item.symbol,
            exchange: item.exchange || item.market,
          }));
          setCatalogSymbols(list);
          return;
        }
      } catch {}
      setCatalogSymbols(getAllDefaultSymbols());
      return;
    }

    try {
      const data = await api.listMarketSymbols({ market: mkt });
      const dynamicList = (data || []).map((item) => ({
        symbol: item.symbol,
        shortName: item.description || item.symbol,
        exchange: item.exchange || mkt,
      }));
      const fallback = DEFAULT_SYMBOLS_BY_MARKET[mkt] || [];
      setCatalogSymbols(dynamicList.length > 0 ? dynamicList : fallback);
    } catch {
      setCatalogSymbols(DEFAULT_SYMBOLS_BY_MARKET[mkt] || []);
    }
  }, []);

  const handleMarketChange = (newMarket) => {
    setSelectedMarket(newMarket);
    setSelectedSymbol(''); // Reset asset filter upon market switch
    loadMarketSymbols(newMarket);
  };

  // Load Event Triggers
  const loadTriggers = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = {};
      if (selectedMarket) params.market = selectedMarket;
      if (selectedSymbol) params.symbol = selectedSymbol;
      if (selectedType) params.trigger_type = selectedType;
      if (selectedStatus) params.status = selectedStatus;
      if (searchQuery.trim()) params.search = searchQuery.trim();

      const data = await api.listEventTriggers(params);
      setTriggers(data || []);
    } catch (err) {
      console.error('Failed to load event triggers:', err);
      if (showToast) showToast(err.message || 'Failed to fetch event triggers', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [selectedMarket, selectedSymbol, selectedType, selectedStatus, searchQuery, showToast]);

  useEffect(() => {
    loadTriggers();
  }, [loadTriggers]);

  useEffect(() => {
    loadMarketSymbols('');
  }, [loadMarketSymbols]);

  // Quick Status Toggle
  const handleToggleStatus = async (trigger) => {
    const nextStatus = trigger.status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE';
    try {
      const updated = await api.toggleEventTriggerStatus(trigger.id, nextStatus);
      setTriggers((prev) => prev.map((t) => (t.id === trigger.id ? { ...t, status: updated.status } : t)));
      if (showToast) {
        showToast(
          `Event WatchDog '${trigger.name}' is now ${updated.status}`,
          updated.status === 'ACTIVE' ? 'success' : 'info'
        );
      }
    } catch (err) {
      if (showToast) showToast(err.message || 'Failed to toggle event watchdog status', 'error');
    }
  };

  // Soft Delete Trigger
  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await api.deleteEventTrigger(deleteTarget.id);
      setTriggers((prev) => prev.filter((t) => t.id !== deleteTarget.id));
      if (showToast) showToast(`Event WatchDog '${deleteTarget.name}' soft-deleted.`, 'success');
      setDeleteTarget(null);
    } catch (err) {
      if (showToast) showToast(err.message || 'Failed to delete event watchdog', 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  // Calculate Metrics
  const totalWatchers = triggers.length;
  const activeWatchers = triggers.filter((t) => t.status === 'ACTIVE').length;
  const totalEventsFired = triggers.reduce((sum, t) => sum + (t.trigger_count || 0), 0);

  // Formatter for Rule Thresholds
  const formatRuleSummary = (trigger) => {
    const type = trigger.trigger_type;
    const cfg = trigger.threshold_config || {};

    if (type === 'PRICE_SPIKE') {
      return `Spike > ${cfg.spike_pct || 1.5}% (${cfg.lookback_bars || 3} bars • ${cfg.direction || 'ANY'})`;
    }
    if (type === 'VOLUME_SPIKE') {
      return `Volume > ${cfg.volume_multiplier || 2.0}x SMA${cfg.sma_period || 20}`;
    }
    if (type === 'SR_BREAK') {
      return `${cfg.break_type || 'BREAKOUT'} @ ${Number(cfg.level || 0).toFixed(2)}`;
    }
    if (type === 'CANDLE_PATTERN') {
      const pats = cfg.patterns || [];
      return pats.length > 0 ? pats.slice(0, 2).join(', ') + (pats.length > 2 ? ` +${pats.length - 2}` : '') : 'Patterns';
    }
    if (type === 'INDICATOR_CROSS') {
      if (cfg.indicator === 'RSI') {
        return `RSI ${cfg.rsi_operator === 'GREATER_THAN' ? '>' : '<'} ${cfg.rsi_threshold || 70}`;
      }
      if (cfg.indicator === 'EMA_CROSS') {
        return `EMA ${cfg.ema_fast || 9}/${cfg.ema_slow || 21} (${cfg.cross_direction || 'GOLDEN'})`;
      }
      return `${cfg.indicator || 'Indicator'}`;
    }
    return type;
  };

  return (
    <Box sx={{ p: { xs: 2, md: 3 }, display: 'flex', flexDirection: 'column', gap: 2.5 }}>
      {/* Compact Page Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 700 }}>
          Event WatchDog
        </Typography>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Button
            variant="contained"
            color="primary"
            startIcon={<Plus size={18} />}
            onClick={() => {
              setEditTrigger(null);
              setCreateModalOpen(true);
            }}
            sx={{ fontWeight: 700, textTransform: 'none', px: 2.5, borderRadius: 2 }}
          >
            New Event WatchDog
          </Button>
        </Box>
      </Box>

      {/* Top KPI Metrics Row (2-column layout per card: Icon column + Title/Value column) */}
      <Grid container spacing={1.5}>
        <Grid item xs={12} sm={6} md={3}>
          <Paper
            variant="outlined"
            sx={{
              p: 1.5,
              borderRadius: 2,
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              height: '100%',
            }}
          >
            {/* Column 1: SVG Icon */}
            <Box sx={{ p: 1.2, borderRadius: 1.5, bgcolor: 'rgba(37, 99, 235, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <Radio size={22} color="#2563EB" />
            </Box>
            {/* Column 2: Title & Value */}
            <Box sx={{ display: 'flex', flexDirection: 'column' }}>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700, textTransform: 'uppercase', fontSize: '0.68rem', letterSpacing: '0.02em' }}>
                TOTAL
              </Typography>
              <Typography variant="h5" sx={{ fontWeight: 800, fontFamily: 'monospace', mt: 0.2 }}>
                {totalWatchers}
              </Typography>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Paper
            variant="outlined"
            sx={{
              p: 1.5,
              borderRadius: 2,
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              height: '100%',
            }}
          >
            {/* Column 1: SVG Icon */}
            <Box sx={{ p: 1.2, borderRadius: 1.5, bgcolor: 'rgba(50, 215, 75, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <Activity size={22} color="#32D74B" />
            </Box>
            {/* Column 2: Title & Value */}
            <Box sx={{ display: 'flex', flexDirection: 'column' }}>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700, textTransform: 'uppercase', fontSize: '0.68rem', letterSpacing: '0.02em' }}>
                ACTIVE
              </Typography>
              <Typography variant="h5" sx={{ fontWeight: 800, fontFamily: 'monospace', color: '#32D74B', mt: 0.2 }}>
                {activeWatchers}
              </Typography>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Paper
            variant="outlined"
            sx={{
              p: 1.5,
              borderRadius: 2,
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              height: '100%',
            }}
          >
            {/* Column 1: SVG Icon */}
            <Box sx={{ p: 1.2, borderRadius: 1.5, bgcolor: 'rgba(245, 158, 11, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <Send size={22} color="#f59e0b" />
            </Box>
            {/* Column 2: Title & Value */}
            <Box sx={{ display: 'flex', flexDirection: 'column' }}>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700, textTransform: 'uppercase', fontSize: '0.68rem', letterSpacing: '0.02em' }}>
                LIFETIME ALERTS
              </Typography>
              <Typography variant="h5" sx={{ fontWeight: 800, fontFamily: 'monospace', color: '#f59e0b', mt: 0.2 }}>
                {totalEventsFired}
              </Typography>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Paper
            variant="outlined"
            sx={{
              p: 1.5,
              borderRadius: 2,
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              height: '100%',
            }}
          >
            {/* Column 1: SVG Icon */}
            <Box sx={{ p: 1.2, borderRadius: 1.5, bgcolor: 'rgba(50, 215, 75, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <Cpu size={22} color="#32D74B" />
            </Box>
            {/* Column 2: Title & Value */}
            <Box sx={{ display: 'flex', flexDirection: 'column' }}>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700, textTransform: 'uppercase', fontSize: '0.68rem', letterSpacing: '0.02em' }}>
                WORKER
              </Typography>
              <Typography variant="subtitle2" sx={{ fontWeight: 800, color: '#32D74B', mt: 0.2, fontFamily: 'monospace' }}>
                ● ONLINE (5s Loop)
              </Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Universal Reactive Filters Ribbon (MarketView Sizing & Style) */}
      <Card sx={{ p: 1.2, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
        <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center', flexWrap: 'wrap', width: '100%' }}>
          {/* Search Input */}
          <TextField
            placeholder="Search WatchDog or symbol..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            size="small"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search size={15} color="#98989D" />
                </InputAdornment>
              ),
            }}
            sx={{
              minWidth: 200,
              flex: { xs: '1 1 180px', sm: '1 1 220px' },
              '& .MuiInputBase-input': { fontSize: '0.8rem', py: 0.8 },
            }}
          />

          {/* Market Select */}
          <FormControl size="small" sx={{ minWidth: 150, flex: { xs: '1 1 140px', sm: '0 0 160px' } }}>
            <InputLabel id="event-market-select-label" sx={{ fontSize: '0.8rem' }}>
              Market
            </InputLabel>
            <Select
              labelId="event-market-select-label"
              id="event-market-select"
              value={selectedMarket}
              label="Market"
              onChange={(e) => handleMarketChange(e.target.value)}
              renderValue={(selected) => {
                if (!selected) return 'All Markets';
                const m = MARKETS.find((x) => x.code === selected);
                return m ? m.label : selected;
              }}
              sx={{ fontSize: '0.8rem', fontWeight: 600, borderRadius: 1.8 }}
            >
              <MenuItem value="" sx={{ fontSize: '0.8rem' }}>
                All Markets
              </MenuItem>
              {MARKETS.filter((m) => m.code !== '').map((m) => (
                <MenuItem key={m.code} value={m.code} sx={{ fontSize: '0.8rem', py: 0.7 }}>
                  {m.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Asset / Symbol Select (Matching MarketView Module filter) */}
          <FormControl size="small" sx={{ minWidth: 160, flex: { xs: '1 1 150px', sm: '0 0 180px' } }}>
            <InputLabel id="event-asset-select-label" sx={{ fontSize: '0.8rem' }}>
              Asset ({catalogSymbols.length})
            </InputLabel>
            <Select
              labelId="event-asset-select-label"
              id="event-asset-select"
              value={selectedSymbol}
              displayEmpty
              label={`Asset (${catalogSymbols.length})`}
              onChange={(e) => setSelectedSymbol(e.target.value)}
              renderValue={(selected) => {
                if (!selected) return <span style={{ color: '#98989D' }}>All Assets</span>;
                return (
                  <Typography sx={{ fontFamily: 'monospace', fontWeight: 800, fontSize: '0.8rem', color: '#60a5fa', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {selected}
                  </Typography>
                );
              }}
              MenuProps={{
                PaperProps: {
                  sx: {
                    maxHeight: 340,
                  },
                },
              }}
              sx={{
                fontSize: '0.8rem',
                fontWeight: 700,
                borderRadius: 1.8,
                fontFamily: 'monospace',
              }}
            >
              <MenuItem value="" sx={{ color: '#98989D', fontSize: '0.8rem' }}>
                All Assets (Select Asset)
              </MenuItem>
              {catalogSymbols.map((item) => (
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
                    label={item.exchange || item.market}
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

          {/* Trigger / Signal Type Select */}
          <FormControl size="small" sx={{ minWidth: 170, flex: { xs: '1 1 150px', sm: '0 0 190px' } }}>
            <InputLabel id="event-type-select-label" sx={{ fontSize: '0.8rem' }}>
              Trigger Type
            </InputLabel>
            <Select
              labelId="event-type-select-label"
              id="event-type-select"
              value={selectedType}
              label="Trigger Type"
              onChange={(e) => setSelectedType(e.target.value)}
              renderValue={(selected) => {
                if (!selected) return 'All Signal Types';
                const t = TRIGGER_TYPES.find((x) => x.code === selected);
                return t ? t.label : selected;
              }}
              sx={{ fontSize: '0.8rem', fontWeight: 600, borderRadius: 1.8 }}
            >
              <MenuItem value="" sx={{ fontSize: '0.8rem' }}>
                All Signal Types
              </MenuItem>
              {TRIGGER_TYPES.filter((t) => t.code !== '').map((t) => (
                <MenuItem key={t.code} value={t.code} sx={{ fontSize: '0.8rem', py: 0.7 }}>
                  {t.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Status Select */}
          <FormControl size="small" sx={{ minWidth: 120, flex: { xs: '1 1 110px', sm: '0 0 130px' } }}>
            <InputLabel id="event-status-select-label" sx={{ fontSize: '0.8rem' }}>
              Status
            </InputLabel>
            <Select
              labelId="event-status-select-label"
              id="event-status-select"
              value={selectedStatus}
              label="Status"
              onChange={(e) => setSelectedStatus(e.target.value)}
              renderValue={(selected) => {
                if (!selected) return 'All Statuses';
                const s = STATUSES.find((x) => x.code === selected);
                return s ? s.label : selected;
              }}
              sx={{ fontSize: '0.8rem', fontWeight: 600, borderRadius: 1.8 }}
            >
              <MenuItem value="" sx={{ fontSize: '0.8rem' }}>
                All Statuses
              </MenuItem>
              {STATUSES.filter((s) => s.code !== '').map((s) => (
                <MenuItem key={s.code} value={s.code} sx={{ fontSize: '0.8rem', py: 0.7 }}>
                  {s.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Side-by-side Refresh Action Button */}
          <Tooltip title="Refresh WatchDogs">
            <IconButton
              onClick={loadTriggers}
              size="small"
              disabled={isLoading}
              sx={{ p: 0.9, borderRadius: 1.8, border: '1px solid', borderColor: 'divider', flexShrink: 0 }}
            >
              <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
            </IconButton>
          </Tooltip>
        </Box>
      </Card>

      {/* Main High-Density Data Table */}
      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2.5 }}>
        <Table size="medium">
          <TableHead>
            <TableRow>
              {/* Column 1: Event WatchDog */}
              <TableCell sx={{ width: '18%', minWidth: 140, fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase' }}>
                Event WatchDog
              </TableCell>
              {/* Column 2: Asset / Symbol (Decreased by 20% to ~22%) */}
              <TableCell sx={{ width: '22%', minWidth: 175, fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase' }}>
                Asset / Symbol
              </TableCell>
              {/* Column 3: Trigger Type */}
              <TableCell sx={{ width: '12%', minWidth: 110, fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase' }}>
                Trigger Type
              </TableCell>
              {/* Column 4: Rule Condition */}
              <TableCell sx={{ width: '20%', minWidth: 160, fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase' }}>
                Rule Condition
              </TableCell>
              {/* Column 5: Channels */}
              <TableCell sx={{ width: '10%', minWidth: 90, fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase' }}>
                Channels
              </TableCell>
              {/* Column 6: Fired Events */}
              <TableCell sx={{ width: '8%', minWidth: 75, fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>
                Fired Events
              </TableCell>
              {/* Column 7: Status & Actions */}
              <TableCell sx={{ width: '10%', minWidth: 100, fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase', textAlign: 'right' }}>
                Status & Actions
              </TableCell>
            </TableRow>
          </TableHead>

          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 6 }}>
                  <CircularProgress size={32} />
                  <Typography variant="body2" sx={{ color: 'text.secondary', mt: 1 }}>
                    Loading Event WatchDogs...
                  </Typography>
                </TableCell>
              </TableRow>
            ) : triggers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 6 }}>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    No Event WatchDogs found.
                  </Typography>
                  <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
                    Click 'New Event WatchDog' to create your first signal evaluator.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              triggers.map((trigger) => {
                const marketChip = getMarketChipInfo(trigger.market);
                const typeChip = getTriggerTypeChip(trigger.trigger_type);

                return (
                  <TableRow key={trigger.id} hover>
                    {/* Column 1: Event WatchDog Name */}
                    <TableCell sx={{ width: '18%' }}>
                      <Typography variant="body2" sx={{ fontWeight: 700, color: 'text.primary' }}>
                        {trigger.name || `WatchDog #${trigger.id}`}
                      </Typography>
                    </TableCell>

                    {/* Column 2: Asset / Symbol with {asset_name} {Market_name} {candle_timeframe} */}
                    <TableCell sx={{ width: '22%' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8, flexWrap: 'wrap' }}>
                        <Typography variant="body2" sx={{ fontWeight: 800, fontFamily: 'monospace', color: '#60a5fa' }}>
                          {trigger.symbol}
                        </Typography>
                        <Chip
                          label={marketChip.label}
                          size="small"
                          sx={{
                            fontSize: '0.65rem',
                            height: 20,
                            fontWeight: 700,
                            color: marketChip.color,
                            bgcolor: marketChip.bg,
                            border: `1px solid ${marketChip.color}40`,
                          }}
                        />
                        <Chip
                          label={trigger.timeframe}
                          size="small"
                          color="primary"
                          variant="outlined"
                          sx={{ fontSize: '0.65rem', height: 20, fontWeight: 700 }}
                        />
                      </Box>
                      {trigger.description && (
                        <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mt: 0.3 }}>
                          {trigger.description}
                        </Typography>
                      )}
                    </TableCell>

                    {/* Column 3: Trigger Type */}
                    <TableCell sx={{ width: '12%' }}>
                      <Chip
                        label={typeChip.label}
                        size="small"
                        color={typeChip.color}
                        variant="outlined"
                        sx={{ fontWeight: 700, fontSize: '0.72rem', height: 22 }}
                      />
                    </TableCell>

                    {/* Column 4: Rule Condition */}
                    <TableCell sx={{ width: '20%' }}>
                      <Tooltip title={JSON.stringify(trigger.threshold_config || {}, null, 2)} arrow>
                        <Chip
                          label={formatRuleSummary(trigger)}
                          size="small"
                          color="info"
                          variant="outlined"
                          sx={{ fontWeight: 600, fontSize: '0.75rem' }}
                        />
                      </Tooltip>
                    </TableCell>

                    {/* Column 5: Channels */}
                    <TableCell sx={{ width: '10%' }}>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                        {(trigger.channels || []).map((ch) => (
                          <Chip
                            key={ch}
                            label={ch}
                            size="small"
                            sx={{ height: 20, fontSize: '0.65rem', fontWeight: 700 }}
                          />
                        ))}
                      </Box>
                    </TableCell>

                    {/* Column 6: Fired Events */}
                    <TableCell sx={{ width: '8%', whiteSpace: 'nowrap' }}>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace', fontWeight: 700 }}>
                        {trigger.trigger_count}
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>
                        {trigger.last_triggered_at
                          ? new Date(trigger.last_triggered_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                          : 'Never'}
                      </Typography>
                    </TableCell>

                    {/* Column 7: Status & Actions */}
                    <TableCell align="right" sx={{ width: '10%' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 1 }}>
                        {/* Status Switch with Tooltip */}
                        <Tooltip title={`Status: ${trigger.status}`} arrow>
                          <Switch
                            size="small"
                            checked={trigger.status === 'ACTIVE'}
                            onChange={() => handleToggleStatus(trigger)}
                            color="success"
                          />
                        </Tooltip>

                        {/* Action Icon Buttons */}
                        <Tooltip title="View Execution Logs & Audit">
                          <IconButton
                            size="small"
                            color="info"
                            onClick={() => setDetailsTriggerId(trigger.id)}
                            sx={{ p: 0.6 }}
                          >
                            <Eye size={17} />
                          </IconButton>
                        </Tooltip>

                        <Tooltip title="Edit Event WatchDog">
                          <IconButton
                            size="small"
                            onClick={() => {
                              setEditTrigger(trigger);
                              setCreateModalOpen(true);
                            }}
                            sx={{ p: 0.6 }}
                          >
                            <Edit2 size={17} />
                          </IconButton>
                        </Tooltip>

                        <Tooltip title="Soft-Delete Event WatchDog">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => setDeleteTarget(trigger)}
                            sx={{ p: 0.6 }}
                          >
                            <Trash2 size={17} />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Create / Edit Modal */}
      {createModalOpen && (
        <CreateEventTriggerModal
          open={createModalOpen}
          onClose={() => setCreateModalOpen(false)}
          onTriggerSaved={loadTriggers}
          editTrigger={editTrigger}
          showToast={showToast}
        />
      )}

      {/* Audit & Execution Logs Modal */}
      {detailsTriggerId && (
        <EventDetailsModal
          open={Boolean(detailsTriggerId)}
          onClose={() => setDetailsTriggerId(null)}
          triggerId={detailsTriggerId}
          showToast={showToast}
        />
      )}

      {/* Soft Delete Confirmation Dialog */}
      <Dialog
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        PaperProps={{ sx: { borderRadius: 2.5, p: 1 } }}
      >
        <DialogTitle sx={{ fontWeight: 700 }}>Confirm Soft-Delete</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            Are you sure you want to delete Event WatchDog <strong>{deleteTarget?.name}</strong>?
          </Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mt: 1 }}>
            Under institutional zero data loss policy, all historical execution logs and telemetry will remain preserved in the audit database.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDeleteTarget(null)} variant="outlined">
            Cancel
          </Button>
          <Button
            onClick={handleConfirmDelete}
            color="error"
            variant="contained"
            disabled={isDeleting}
            startIcon={isDeleting ? <CircularProgress size={16} color="inherit" /> : <Trash2 size={16} />}
          >
            {isDeleting ? 'Deleting...' : 'Confirm Soft-Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
