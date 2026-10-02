import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  IconButton,
  Tooltip,
  CircularProgress,
  Alert,
  Switch,
  TextField,
  InputAdornment,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Search,
  Plus,
  Trash2,
  AlertTriangle,
  RotateCcw,
  Layers,
} from 'lucide-react';

import { api } from '../../api';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../ThemeContext';
import AddAssetModal from './AddAssetModal';

const ASSET_TYPE_STYLES = {
  STOCK: { bg: 'rgba(37, 99, 235, 0.15)', color: '#60A5FA', border: 'rgba(37, 99, 235, 0.35)' },
  INDEX: { bg: 'rgba(99, 102, 241, 0.15)', color: '#818CF8', border: 'rgba(99, 102, 241, 0.35)' },
  CRYPTO: { bg: 'rgba(255, 159, 10, 0.12)', color: '#FF9F0A', border: 'rgba(255, 159, 10, 0.3)' },
  FOREX: { bg: 'rgba(50, 215, 75, 0.12)', color: '#32D74B', border: 'rgba(50, 215, 75, 0.3)' },
  COMMODITY: { bg: 'rgba(255, 69, 58, 0.12)', color: '#FF453A', border: 'rgba(255, 69, 58, 0.3)' },
};

const MARKET_FILTER_OPTIONS = [
  { value: 'NSE', label: 'NSE (Indian Equities & Indices)' },
  { value: 'BSE', label: 'BSE (Bombay Stock Exchange)' },
  { value: 'US_EQUITY', label: 'Dow Jones & US Equities (NASDAQ / NYSE)' },
  { value: 'CRYPTO', label: 'Cryptocurrency (Binance)' },
  { value: 'FOREX', label: 'Foreign Exchange (FX)' },
  { value: 'MCX', label: 'MCX Commodities' },
  { value: 'ALL', label: 'All Markets' },
];

export default function MarketCatalogScreen({ showToast }) {
  const { isEnterprise } = useTheme();
  const { hasPermission } = useAuth();

  const canEdit = hasPermission('CATALOG', 'edit');
  const canDelete = hasPermission('CATALOG', 'delete');

  const [symbols, setSymbols] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters (Default Market: 'NSE')
  const [marketFilter, setMarketFilter] = useState('NSE');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Pagination (Default: 20 rows per page)
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(20);

  // Modals & Action States
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [deleteCandidate, setDeleteCandidate] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [togglingSymbol, setTogglingSymbol] = useState(null);

  const fetchCatalogData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getCatalogSymbols({ limit: 500 }).catch(() => []);
      const symbolList = Array.isArray(res) ? res : (res?.symbols || []);
      setSymbols(symbolList);
    } catch (err) {
      console.error('Error fetching catalog data:', err);
      setError(err.message || 'Failed to load market catalog data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCatalogData();
  }, [fetchCatalogData]);

  // Handle active/inactive toggle
  const handleToggleStatus = async (symbolObj) => {
    if (!canEdit) {
      if (showToast) showToast('Permission denied: You do not have edit rights for Catalog.', 'error');
      return;
    }

    const nextStatus = !symbolObj.isActive;
    setTogglingSymbol(symbolObj.symbol);
    try {
      await api.toggleSymbolStatus(symbolObj.symbol, nextStatus);
      setSymbols((prev) =>
        prev.map((s) => (s.symbol === symbolObj.symbol ? { ...s, isActive: nextStatus } : s))
      );
      if (showToast) {
        showToast(
          `Asset ${symbolObj.symbol} is now ${nextStatus ? 'ACTIVE' : 'INACTIVE'}.`,
          'success'
        );
      }
    } catch (err) {
      if (showToast) showToast(err.message || 'Failed to update asset status', 'error');
    } finally {
      setTogglingSymbol(null);
    }
  };

  // Handle delete execution
  const handleConfirmDelete = async () => {
    if (!deleteCandidate || !canDelete) return;
    setIsDeleting(true);
    try {
      await api.deleteCatalogSymbol(deleteCandidate.symbol);
      setSymbols((prev) => prev.filter((s) => s.symbol !== deleteCandidate.symbol));
      if (showToast) {
        showToast(`Asset '${deleteCandidate.symbol}' deleted from catalog.`, 'success');
      }
      setDeleteCandidate(null);
    } catch (err) {
      if (showToast) showToast(err.message || 'Failed to delete symbol', 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  // Reset Filters to defaults (Market: 'NSE', Status: 'ALL', Search: '')
  const handleResetFilters = () => {
    setMarketFilter('NSE');
    setStatusFilter('ALL');
    setSearchQuery('');
    setPage(0);
  };

  // Filtered symbols across all markets
  const filteredSymbols = useMemo(() => {
    return symbols.filter((item) => {
      // Market filter
      if (marketFilter !== 'ALL') {
        const group = (item.marketGroup?.code || item.marketGroupId || item.groupId || '').toUpperCase();
        const exch = (item.exchange || '').toUpperCase();
        const mkt = (item.market || '').toUpperCase();
        const type = (item.assetType || '').toUpperCase();

        if (marketFilter === 'NSE') {
          if (
            group !== 'NSE' &&
            exch !== 'NSE' &&
            mkt !== 'INDIAN_EQUITY' &&
            group !== 'INDIAN_EQUITY'
          )
            return false;
        } else if (marketFilter === 'BSE') {
          if (group !== 'BSE' && exch !== 'BSE') return false;
        } else if (marketFilter === 'US_EQUITY') {
          if (
            group !== 'US_EQUITY' &&
            mkt !== 'US_EQUITY' &&
            exch !== 'NASDAQ' &&
            exch !== 'NYSE' &&
            exch !== 'DJI'
          )
            return false;
        } else if (marketFilter === 'CRYPTO') {
          if (group !== 'CRYPTO' && type !== 'CRYPTO' && mkt !== 'CRYPTO' && exch !== 'BINANCE')
            return false;
        } else if (marketFilter === 'FOREX') {
          if (group !== 'FOREX' && type !== 'FOREX' && mkt !== 'FOREX' && exch !== 'FX_IDC')
            return false;
        } else if (marketFilter === 'MCX') {
          if (group !== 'MCX' && type !== 'COMMODITY' && mkt !== 'MCX' && exch !== 'MCX')
            return false;
        }
      }

      // Status filter
      if (statusFilter === 'ACTIVE' && !item.isActive) return false;
      if (statusFilter === 'INACTIVE' && item.isActive) return false;

      // Text search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const sym = (item.symbol || '').toLowerCase();
        const name = (item.fullName || item.name || item.shortName || '').toLowerCase();
        const exch = (item.exchange || '').toLowerCase();
        if (!sym.includes(q) && !name.includes(q) && !exch.includes(q)) {
          return false;
        }
      }

      return true;
    });
  }, [symbols, marketFilter, statusFilter, searchQuery]);

  const paginatedSymbols = useMemo(() => {
    const start = page * rowsPerPage;
    return filteredSymbols.slice(start, start + rowsPerPage);
  }, [filteredSymbols, page, rowsPerPage]);

  return (
    <Box sx={{ p: 3, maxWidth: '1600px', margin: '0 auto' }}>
      {/* Action Bar */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'flex-end',
          alignItems: 'center',
          mb: 2.5,
        }}
      >
        <Button
          variant="contained"
          disabled={!canEdit}
          onClick={() => setIsAddModalOpen(true)}
          startIcon={<Plus className="w-4 h-4" />}
          sx={{
            bgcolor: isEnterprise ? '#82B440' : '#2563EB',
            color: '#FFFFFF',
            textTransform: 'none',
            fontWeight: 700,
            px: 2.5,
            py: 0.9,
            borderRadius: 2,
            boxShadow: '0 4px 14px rgba(37, 99, 235, 0.3)',
            '&:hover': {
              bgcolor: isEnterprise ? '#6e9b34' : '#1D4ED8',
            },
          }}
        >
          Add New Asset
        </Button>
      </Box>

      {/* Main Content Paper Container */}
      <Paper
        sx={{
          bgcolor: 'var(--bg-card, #1E1E1E)',
          border: '1px solid var(--border-color, #2C2C2E)',
          borderRadius: 4,
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.35)',
          overflow: 'hidden',
        }}
      >
        {/* Filter Bar on top of the table: Market, Status, Search, and Reset Filter sitting on the same row */}
        <Box
          sx={{
            p: 2,
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            flexWrap: 'wrap',
            bgcolor: 'var(--bg-secondary, #181818)',
            borderBottom: '1px solid var(--border-color, #2C2C2E)',
          }}
        >
          {/* Market Filter (Default: NSE) */}
          <FormControl size="small" sx={{ minWidth: 260 }}>
            <InputLabel sx={{ color: 'var(--text-muted, #98989D)', fontSize: '0.85rem' }}>Market</InputLabel>
            <Select
              value={marketFilter}
              label="Market"
              onChange={(e) => {
                setMarketFilter(e.target.value);
                setPage(0);
              }}
              sx={{
                color: 'var(--text-main, #FFFFFF)',
                bgcolor: 'transparent',
                '& .MuiOutlinedInput-notchedOutline': { borderColor: 'var(--border-color, #2C2C2E)' },
                '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'var(--border-hover, #3A3A3C)' },
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: 'var(--accent, #00E5FF)' },
              }}
            >
              {MARKET_FILTER_OPTIONS.map((opt) => (
                <MenuItem key={opt.value} value={opt.value}>
                  {opt.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Status Filter */}
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel sx={{ color: 'var(--text-muted, #98989D)', fontSize: '0.85rem' }}>Status</InputLabel>
            <Select
              value={statusFilter}
              label="Status"
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(0);
              }}
              sx={{
                color: 'var(--text-main, #FFFFFF)',
                bgcolor: 'transparent',
                '& .MuiOutlinedInput-notchedOutline': { borderColor: 'var(--border-color, #2C2C2E)' },
                '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'var(--border-hover, #3A3A3C)' },
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: 'var(--accent, #00E5FF)' },
              }}
            >
              <MenuItem value="ALL">All Statuses</MenuItem>
              <MenuItem value="ACTIVE">Active Only</MenuItem>
              <MenuItem value="INACTIVE">Inactive Only</MenuItem>
            </Select>
          </FormControl>

          {/* Symbol / Name Search Input */}
          <TextField
            placeholder="Search by symbol or name..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(0);
            }}
            size="small"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search className="w-4 h-4 text-[#98989D]" />
                </InputAdornment>
              ),
            }}
            sx={{
              flex: 1,
              minWidth: 220,
              '& .MuiOutlinedInput-root': {
                color: 'var(--text-main, #FFFFFF)',
                bgcolor: 'transparent',
                '& fieldset': { borderColor: 'var(--border-color, #2C2C2E)' },
                '&:hover fieldset': { borderColor: 'var(--border-hover, #3A3A3C)' },
                '&.Mui-focused fieldset': { borderColor: 'var(--accent, #00E5FF)' },
              },
              '& .MuiInputBase-input::placeholder': {
                color: 'var(--text-muted, #98989D)',
                opacity: 1,
              },
            }}
          />

          {/* Reset Filter Button sits in the same row as filters */}
          <Button
            variant="outlined"
            size="small"
            onClick={handleResetFilters}
            startIcon={<RotateCcw className="w-3.5 h-3.5" />}
            sx={{
              borderColor: 'var(--border-color, #2C2C2E)',
              color: 'var(--text-muted, #98989D)',
              textTransform: 'none',
              fontWeight: 600,
              height: 40,
              px: 2,
              borderRadius: 2,
              '&:hover': {
                borderColor: 'var(--border-hover, #3A3A3C)',
                color: 'var(--text-main, #FFFFFF)',
                bgcolor: 'var(--bg-card-hover, #252525)',
              },
            }}
          >
            Reset Filters
          </Button>
        </Box>

        {/* Error Alert */}
        {error && (
          <Alert severity="error" sx={{ m: 2.5 }}>
            {error}
          </Alert>
        )}

        {/* Table View */}
        <TableContainer>
          <Table sx={{ minWidth: 900 }}>
            <TableHead>
              <TableRow sx={{ bgcolor: 'var(--bg-secondary, #181818)' }}>
                <TableCell sx={{ color: 'var(--text-muted, #98989D)', fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase', borderBottom: '1px solid var(--border-color, #2C2C2E)' }}>
                  Symbol / Company
                </TableCell>
                <TableCell sx={{ color: 'var(--text-muted, #98989D)', fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase', borderBottom: '1px solid var(--border-color, #2C2C2E)' }}>
                  Exchange / Market
                </TableCell>
                <TableCell sx={{ color: 'var(--text-muted, #98989D)', fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase', borderBottom: '1px solid var(--border-color, #2C2C2E)' }}>
                  Asset Type
                </TableCell>
                <TableCell sx={{ color: 'var(--text-muted, #98989D)', fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase', borderBottom: '1px solid var(--border-color, #2C2C2E)' }}>
                  Precision & Tick
                </TableCell>
                <TableCell sx={{ color: 'var(--text-muted, #98989D)', fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase', borderBottom: '1px solid var(--border-color, #2C2C2E)' }}>
                  Lot Size
                </TableCell>
                <TableCell sx={{ color: 'var(--text-muted, #98989D)', fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase', borderBottom: '1px solid var(--border-color, #2C2C2E)' }}>
                  Origin
                </TableCell>
                <TableCell sx={{ color: 'var(--text-muted, #98989D)', fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase', borderBottom: '1px solid var(--border-color, #2C2C2E)' }}>
                  Trading Status
                </TableCell>
                <TableCell align="right" sx={{ color: 'var(--text-muted, #98989D)', fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase', borderBottom: '1px solid var(--border-color, #2C2C2E)' }}>
                  Actions
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 8, borderBottom: '1px solid var(--border-color, #2C2C2E)' }}>
                    <CircularProgress size={32} sx={{ color: '#2563EB' }} />
                    <Typography variant="body2" sx={{ mt: 1.5, color: 'var(--text-muted, #98989D)' }}>
                      Loading market catalog directory...
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : paginatedSymbols.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 8, borderBottom: '1px solid var(--border-color, #2C2C2E)' }}>
                    <Typography variant="body1" sx={{ color: 'var(--text-main, #FFFFFF)', fontWeight: 700, fontSize: '1rem' }}>
                      No market assets match the selected filter criteria.
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'var(--text-muted, #98989D)', mt: 0.5, display: 'block' }}>
                      Try selecting a different market (e.g. All Markets) or resetting filters.
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                paginatedSymbols.map((item) => {
                  const typeStyle = ASSET_TYPE_STYLES[item.assetType] || {
                    bg: 'rgba(0, 229, 255, 0.12)',
                    color: '#00E5FF',
                    border: 'rgba(0, 229, 255, 0.3)',
                  };

                  const isTogglingThis = togglingSymbol === item.symbol;
                  const displayName = item.fullName || item.name || item.shortName || item.symbol;

                  return (
                    <TableRow
                      key={item.id || item.symbol}
                      hover
                      sx={{
                        '&:hover': { bgcolor: 'var(--bg-card-hover, #252525)' },
                        borderBottom: '1px solid var(--border-color, #2C2C2E)',
                      }}
                    >
                      {/* Symbol & Company Name */}
                      <TableCell sx={{ borderBottom: '1px solid var(--border-color, #2C2C2E)' }}>
                        <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography
                              variant="body2"
                              sx={{
                                fontWeight: 800,
                                color: 'var(--text-main, #FFFFFF)',
                                fontFamily: "'JetBrains Mono', monospace",
                                fontSize: '0.95rem',
                              }}
                            >
                              {item.symbol}
                            </Typography>
                            {item.isPreseeded && (
                              <Chip
                                label="BENCHMARK"
                                size="small"
                                sx={{
                                  fontSize: '0.65rem',
                                  height: 18,
                                  bgcolor: 'rgba(50, 215, 75, 0.15)',
                                  color: '#32D74B',
                                  fontWeight: 700,
                                  border: '1px solid rgba(50, 215, 75, 0.3)',
                                }}
                              />
                            )}
                          </Box>
                          <Typography variant="caption" sx={{ color: 'var(--text-muted, #98989D)', mt: 0.25 }}>
                            {displayName}
                          </Typography>
                        </Box>
                      </TableCell>

                      {/* Exchange & Market Group */}
                      <TableCell sx={{ borderBottom: '1px solid var(--border-color, #2C2C2E)' }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Chip
                            label={item.exchange}
                            size="small"
                            sx={{
                              fontWeight: 700,
                              fontSize: '0.7rem',
                              height: 20,
                              bgcolor: 'var(--border-color, #2C2C2E)',
                              color: 'var(--text-main, #FFFFFF)',
                              border: '1px solid #3A3A3C',
                            }}
                          />
                          <Typography variant="caption" sx={{ color: 'var(--text-muted, #98989D)' }}>
                            {item.marketGroup?.name || item.marketGroupId || item.groupId || item.market}
                          </Typography>
                        </Box>
                      </TableCell>

                      {/* Asset Type */}
                      <TableCell sx={{ borderBottom: '1px solid var(--border-color, #2C2C2E)' }}>
                        <Chip
                          label={item.assetType}
                          size="small"
                          sx={{
                            bgcolor: typeStyle.bg,
                            color: typeStyle.color,
                            border: `1px solid ${typeStyle.border}`,
                            fontWeight: 700,
                            fontSize: '0.7rem',
                            height: 22,
                          }}
                        />
                      </TableCell>

                      {/* Precision & Tick Size */}
                      <TableCell sx={{ borderBottom: '1px solid var(--border-color, #2C2C2E)' }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Chip
                            label={`${item.decimalPlaces} Decimals`}
                            size="small"
                            sx={{
                              bgcolor: item.decimalPlaces === 4 ? 'rgba(37, 99, 235, 0.15)' : 'rgba(255, 159, 10, 0.12)',
                              color: item.decimalPlaces === 4 ? '#60A5FA' : '#FF9F0A',
                              fontWeight: 700,
                              fontSize: '0.7rem',
                              height: 20,
                            }}
                          />
                          <Typography
                            variant="caption"
                            sx={{
                              color: 'var(--text-muted, #98989D)',
                              fontFamily: "'JetBrains Mono', monospace",
                            }}
                          >
                            Tick: {item.tickSize}
                          </Typography>
                        </Box>
                      </TableCell>

                      {/* Lot Size */}
                      <TableCell sx={{ borderBottom: '1px solid var(--border-color, #2C2C2E)' }}>
                        <Typography
                          variant="body2"
                          sx={{
                            fontFamily: "'JetBrains Mono', monospace",
                            color: 'var(--text-main, #FFFFFF)',
                            fontSize: '0.85rem',
                          }}
                        >
                          {item.lotSize}
                        </Typography>
                      </TableCell>

                      {/* Origin / Preseeded */}
                      <TableCell sx={{ borderBottom: '1px solid var(--border-color, #2C2C2E)' }}>
                        <Typography variant="caption" sx={{ color: 'var(--text-muted, #98989D)' }}>
                          {item.createdBy === 'SYSTEM_SEEDER' || item.isPreseeded ? 'System Seed' : 'User Added'}
                        </Typography>
                      </TableCell>

                      {/* Active Status Switch */}
                      <TableCell sx={{ borderBottom: '1px solid var(--border-color, #2C2C2E)' }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {isTogglingThis ? (
                            <CircularProgress size={16} sx={{ color: '#00E5FF' }} />
                          ) : (
                            <Switch
                              checked={Boolean(item.isActive)}
                              onChange={() => handleToggleStatus(item)}
                              disabled={!canEdit || isTogglingThis}
                              size="small"
                              sx={{
                                '& .MuiSwitch-switchBase.Mui-checked': {
                                  color: '#32D74B',
                                },
                                '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                                  backgroundColor: '#32D74B',
                                },
                              }}
                            />
                          )}
                          <Typography
                            variant="caption"
                            sx={{
                              fontWeight: 700,
                              color: item.isActive ? '#32D74B' : 'var(--text-dim, #6E6E73)',
                            }}
                          >
                            {item.isActive ? 'Active' : 'Inactive'}
                          </Typography>
                        </Box>
                      </TableCell>

                      {/* Actions */}
                      <TableCell align="right" sx={{ borderBottom: '1px solid var(--border-color, #2C2C2E)' }}>
                        <Tooltip title={canDelete ? 'Delete symbol from catalog' : 'Requires Delete permission'}>
                          <span>
                            <IconButton
                              size="small"
                              disabled={!canDelete}
                              onClick={() => setDeleteCandidate(item)}
                              sx={{
                                color: 'rgba(255, 69, 58, 0.75)',
                                '&:hover': { color: '#FF453A', bgcolor: 'rgba(255, 69, 58, 0.12)' },
                              }}
                            >
                              <Trash2 className="w-4 h-4" />
                            </IconButton>
                          </span>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Pagination Bar: Default 20 rows per page */}
        <TablePagination
          rowsPerPageOptions={[20, 50, 100]}
          component="div"
          count={filteredSymbols.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={(e, newPage) => setPage(newPage)}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
          sx={{
            color: 'var(--text-muted, #98989D)',
            borderTop: '1px solid var(--border-color, #2C2C2E)',
            bgcolor: 'var(--bg-secondary, #181818)',
            '& .MuiTablePagination-selectIcon': { color: 'var(--text-muted, #98989D)' },
          }}
        />
      </Paper>

      {/* Add Asset Modal */}
      <AddAssetModal
        open={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAssetAdded={(created) => {
          if (created) {
            setSymbols((prev) => {
              const exists = prev.some((s) => s.symbol === created.symbol);
              if (!exists) return [created, ...prev];
              return prev.map((s) => (s.symbol === created.symbol ? created : s));
            });
          }
          fetchCatalogData();
          if (showToast) showToast(`Asset '${created?.symbol || ''}' added to catalog!`, 'success');
        }}
        showToast={showToast}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={Boolean(deleteCandidate)}
        onClose={() => !isDeleting && setDeleteCandidate(null)}
        slotProps={{
          paper: {
            sx: {
              bgcolor: 'var(--bg-card, #1E1E1E)',
              color: 'var(--text-main, #FFFFFF)',
              border: '1px solid var(--border-color, #2C2C2E)',
              borderRadius: 3,
              minWidth: 420,
              p: 1,
            },
          },
        }}
      >
        <DialogTitle sx={{ color: '#FF453A', display: 'flex', alignItems: 'center', gap: 1 }}>
          <AlertTriangle className="w-5 h-5" />
          Confirm Asset Deletion
        </DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ color: 'var(--text-muted, #98989D)', mb: 2 }}>
            Are you sure you want to permanently delete{' '}
            <strong style={{ color: '#FFFFFF' }}>
              {deleteCandidate?.symbol} ({deleteCandidate?.fullName || deleteCandidate?.name})
            </strong>{' '}
            from exchange <strong style={{ color: '#FFFFFF' }}>{deleteCandidate?.exchange}</strong>?
          </DialogContentText>
          <Alert
            severity="warning"
            sx={{
              borderRadius: 2,
              bgcolor: 'rgba(255, 159, 10, 0.12)',
              color: '#FF9F0A',
              border: '1px solid rgba(255, 159, 10, 0.3)',
              '& .MuiAlert-icon': { color: '#FF9F0A' },
            }}
          >
            This will remove the symbol from active discovery and cascade to candle records while
            preserving institutional audit trails.
          </Alert>
        </DialogContent>
        <DialogActions sx={{ p: 2, gap: 1 }}>
          <Button
            onClick={() => setDeleteCandidate(null)}
            disabled={isDeleting}
            sx={{ textTransform: 'none', color: 'var(--text-muted, #98989D)' }}
          >
            Cancel
          </Button>
          <Button
            onClick={handleConfirmDelete}
            disabled={isDeleting}
            variant="contained"
            color="error"
            startIcon={isDeleting ? <CircularProgress size={16} /> : <Trash2 className="w-4 h-4" />}
            sx={{ textTransform: 'none', fontWeight: 700, bgcolor: '#FF453A', '&:hover': { bgcolor: '#E03126' } }}
          >
            {isDeleting ? 'Deleting...' : 'Delete Asset'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
