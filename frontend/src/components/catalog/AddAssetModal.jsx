import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
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
  List,
  ListItemButton,
  ListItemText,
  Paper,
  InputAdornment,
  IconButton,
} from '@mui/material';
import { Search, CheckCircle2, AlertTriangle, Layers, Plus, X } from 'lucide-react';
import { api } from '../../api';

const MARKETS = [
  { code: 'INDIAN_EQUITY', label: 'Indian Equities & Indices (NSE / BSE)' },
  { code: 'US_EQUITY', label: 'US Equities & ETFs (NASDAQ / NYSE)' },
  { code: 'CRYPTO', label: 'Cryptocurrency (Binance)' },
  { code: 'FOREX', label: 'Foreign Exchange (FX_IDC)' },
  { code: 'MCX', label: 'MCX Commodities (India)' },
];

export default function AddAssetModal({ open, onClose, onAssetAdded, showToast }) {
  const [market, setMarket] = useState('INDIAN_EQUITY');
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Clear state on open/close
  useEffect(() => {
    if (open) {
      setQuery('');
      setSearchResults([]);
      setSelectedAsset(null);
      setErrorMsg(null);
      setIsSearching(false);
    }
  }, [open]);

  // Handle live search suggestions with debounce
  useEffect(() => {
    const q = query.trim();
    if (q.length < 2 || selectedAsset) {
      setSearchResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      setErrorMsg(null);
      try {
        const results = await api.searchCatalogAssets(q, market);
        if (results && results.length > 0) {
          setSearchResults(results);
          setErrorMsg(null);
        } else {
          setSearchResults([]);
        }
      } catch (err) {
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [query, market, selectedAsset]);

  const handleSelectAsset = (asset) => {
    setSelectedAsset(asset);
    setQuery(asset.symbol);
    setSearchResults([]);
    setErrorMsg(null);
  };

  const handleManualVerify = async () => {
    const q = query.trim();
    if (!q) return;
    setIsSearching(true);
    setErrorMsg(null);
    setSelectedAsset(null);
    try {
      const res = await api.verifyCatalogAsset({ query: q, market });
      if (res.verified && res.asset) {
        setSelectedAsset(res.asset);
        setErrorMsg(null);
      } else {
        setSelectedAsset(null);
        setErrorMsg(
          res.error ||
            `Asset '${q}' could not be found or verified on TradingView for ${market}. Please check the symbol or company name.`
        );
      }
    } catch (err) {
      setErrorMsg(err.message || 'Verification service failed.');
    } finally {
      setIsSearching(false);
    }
  };

  const handleCommitAsset = async () => {
    if (!selectedAsset) return;
    setIsSubmitting(true);
    try {
      const payload = {
        symbol: selectedAsset.symbol,
        shortName: selectedAsset.name.split(' ')[0] || selectedAsset.symbol,
        fullName: selectedAsset.name,
        market: selectedAsset.market || market,
        exchange: selectedAsset.exchange,
        assetType: selectedAsset.assetType,
        decimalPlaces: selectedAsset.decimalPlaces,
        lotSize: selectedAsset.assetType === 'FOREX' ? 1000 : 1,
        tickSize: selectedAsset.decimalPlaces === 4 ? 0.05 : 0.0001,
        tvSymbol: selectedAsset.tvSymbol,
      };

      const created = await api.addCatalogAsset(payload);
      if (showToast) showToast(`Asset '${created.symbol}' verified and added successfully!`, 'success');
      onAssetAdded(created);
      onClose();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to add asset to catalog.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            borderRadius: 3,
            p: 1,
            bgcolor: 'background.paper',
            color: 'text.primary',
            boxShadow: 24,
          },
        },
      }}
    >
      <DialogTitle
        sx={{
          pb: 1.5,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={{
              p: 1,
              borderRadius: 2,
              bgcolor: 'primary.main',
              color: 'primary.contrastText',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Layers size={20} />
          </Box>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700, color: 'text.primary', lineHeight: 1.2 }}>
              Add Market Asset
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              Real-time TradingView Symbol Search & Precision Verification
            </Typography>
          </Box>
        </Box>
        <IconButton size="small" onClick={onClose} sx={{ color: 'text.secondary' }}>
          <X size={18} />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ pt: 2, pb: 3 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, mt: 1 }}>
          {/* Target Market Selector */}
          <FormControl fullWidth size="small">
            <InputLabel>Target Market</InputLabel>
            <Select
              value={market}
              label="Target Market"
              onChange={(e) => {
                setMarket(e.target.value);
                setSelectedAsset(null);
                setSearchResults([]);
                setErrorMsg(null);
              }}
            >
              {MARKETS.map((m) => (
                <MenuItem key={m.code} value={m.code}>
                  {m.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Search Query Input */}
          <TextField
            fullWidth
            size="small"
            label="Company Name or Symbol"
            placeholder="e.g. Tata Motors, RELIANCE, Apple, BTCUSDT..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedAsset(null);
              setErrorMsg(null);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                handleManualVerify();
              }
            }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search size={18} color="#94a3b8" />
                </InputAdornment>
              ),
              endAdornment: isSearching && (
                <InputAdornment position="end">
                  <CircularProgress size={16} />
                </InputAdornment>
              ),
            }}
          />

          {/* Action Row: Verify and Cancel Buttons on the Same Row */}
          <Box sx={{ display: 'flex', gap: 1.5, justifyContent: 'flex-end', alignItems: 'center' }}>
            <Button
              variant="outlined"
              onClick={onClose}
              color="inherit"
              sx={{ textTransform: 'none', fontWeight: 600, px: 2.5 }}
            >
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={handleManualVerify}
              disabled={isSearching || !query.trim()}
              startIcon={isSearching ? <CircularProgress size={16} color="inherit" /> : <Search size={16} />}
              sx={{ textTransform: 'none', fontWeight: 700, px: 3 }}
            >
              {isSearching ? 'Verifying...' : 'Verify'}
            </Button>
          </Box>

          {/* Autocomplete Search Suggestions List */}
          {searchResults.length > 0 && !selectedAsset && (
            <Paper
              variant="outlined"
              sx={{
                maxHeight: 220,
                overflowY: 'auto',
                borderRadius: 2,
                mt: -1,
              }}
            >
              <List dense disablePadding>
                {searchResults.map((item, idx) => (
                  <ListItemButton
                    key={`${item.exchange}-${item.symbol}-${idx}`}
                    onClick={() => handleSelectAsset(item)}
                    sx={{
                      borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
                      '&:hover': { bgcolor: 'action.hover' },
                    }}
                  >
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography sx={{ fontWeight: 800, color: 'text.primary', fontSize: '0.875rem', fontFamily: 'monospace' }}>
                            {item.symbol}
                          </Typography>
                          <Chip
                            label={item.exchange}
                            size="small"
                            sx={{ height: 18, fontSize: '0.65rem', fontWeight: 600 }}
                          />
                          <Chip
                            label={item.assetType}
                            size="small"
                            color="primary"
                            variant="outlined"
                            sx={{ height: 18, fontSize: '0.65rem', fontWeight: 600 }}
                          />
                        </Box>
                      }
                      secondary={
                        <Typography sx={{ color: 'text.secondary', fontSize: '0.75rem', mt: 0.25 }} noWrap>
                          {item.name}
                        </Typography>
                      }
                    />
                  </ListItemButton>
                ))}
              </List>
            </Paper>
          )}

          {/* Verification Success Screen with Clear High-Contrast Text */}
          {selectedAsset && (
            <Paper
              variant="outlined"
              sx={{
                p: 2.5,
                borderRadius: 2,
                bgcolor: (theme) => (theme.palette.mode === 'dark' ? 'rgba(16, 185, 129, 0.12)' : '#f0fdf4'),
                borderColor: '#10b981',
                mt: 1,
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <CheckCircle2 size={20} color="#059669" />
                <Typography sx={{ fontWeight: 700, color: '#059669', fontSize: '0.95rem' }}>
                  Verified on TradingView
                </Typography>
              </Box>

              <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 2 }}>
                <Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700, display: 'block', mb: 0.5 }}>
                    CANONICAL SYMBOL
                  </Typography>
                  <Typography variant="body1" sx={{ fontWeight: 800, fontFamily: 'monospace', color: 'text.primary' }}>
                    {selectedAsset.symbol}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700, display: 'block', mb: 0.5 }}>
                    EXCHANGE
                  </Typography>
                  <Chip label={selectedAsset.exchange} size="small" sx={{ fontWeight: 700 }} />
                </Box>
                <Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700, display: 'block', mb: 0.5 }}>
                    ASSET NAME
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }} noWrap>
                    {selectedAsset.name}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700, display: 'block', mb: 0.5 }}>
                    DECIMAL PRECISION
                  </Typography>
                  <Chip
                    label={`${selectedAsset.decimalPlaces} Decimals (${selectedAsset.decimalPlaces === 4 ? '0.0001' : '0.000001'})`}
                    size="small"
                    color={selectedAsset.decimalPlaces === 4 ? 'primary' : 'warning'}
                    sx={{ fontWeight: 700 }}
                  />
                </Box>
              </Box>

              <Button
                variant="contained"
                color="success"
                fullWidth
                size="large"
                onClick={handleCommitAsset}
                disabled={isSubmitting}
                startIcon={isSubmitting ? <CircularProgress size={18} color="inherit" /> : <Plus size={18} />}
                sx={{ mt: 2.5, fontWeight: 700, textTransform: 'none' }}
              >
                {isSubmitting ? 'Adding Asset...' : 'Confirm & Add to Catalog'}
              </Button>
            </Paper>
          )}

          {/* User-Friendly Verification Error Alert */}
          {errorMsg && (
            <Alert
              severity="error"
              icon={<AlertTriangle size={18} />}
              sx={{ borderRadius: 2, fontSize: '0.85rem' }}
            >
              {errorMsg}
            </Alert>
          )}
        </Box>
      </DialogContent>
    </Dialog>
  );
}
