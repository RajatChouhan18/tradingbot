import React, { useState, useEffect, useMemo } from 'react';
import { 
  DollarSign, 
  TrendingUp, 
  TrendingDown, 
  ShieldCheck, 
  Clock, 
  RefreshCw, 
  Play, 
  Square, 
  Sliders, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  X, 
  Check, 
  Search, 
  Filter, 
  RotateCcw,
  Layers,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  Zap,
  Flame
} from 'lucide-react';
import { api, connectTelemetryStream } from '../api';

export default function PaperTradingView({ showToast }) {
  const [activeTab, setActiveTab] = useState('positions'); // 'positions', 'trades', 'settings'
  const [portfolio, setPortfolio] = useState(null);
  const [positions, setPositions] = useState([]);
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingPosition, setEditingPosition] = useState(null);
  const [editForm, setEditForm] = useState({ stop_loss: '', target: '', trailing_sl: '' });
  const [showResetModal, setShowResetModal] = useState(false);
  const [resetCapital, setResetCapital] = useState(1000000);
  const [actionInProgress, setActionInProgress] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Phase 7: Risk Management & Broker States
  const [riskStatus, setRiskStatus] = useState(null);
  const [brokers, setBrokers] = useState([]);
  const [activeBroker, setActiveBroker] = useState('PAPER');
  const [showRiskModal, setShowRiskModal] = useState(false);
  const [riskForm, setRiskForm] = useState({ max_daily_loss_pct: 3, max_open_positions: 5, consecutive_loss_limit: 3 });
  const [showEmergencyModal, setShowEmergencyModal] = useState(false);

  // Fetch portfolio, open positions, closed trades, risk status, and brokers
  const fetchAllData = async () => {
    try {
      const [portRes, posRes, trdRes, riskRes, brokerRes] = await Promise.all([
        api.getPaperPortfolio().catch(() => null),
        api.getPaperPositions().catch(() => []),
        api.getPaperTrades(100).catch(() => []),
        api.getRiskStatus().catch(() => null),
        api.getBrokers().catch(() => null),
      ]);
      if (portRes) setPortfolio(portRes);
      if (Array.isArray(posRes)) setPositions(posRes);
      if (Array.isArray(trdRes)) setTrades(trdRes);
      if (riskRes) {
        setRiskStatus(riskRes);
        setRiskForm({
          max_daily_loss_pct: riskRes.max_daily_loss_pct || 3,
          max_open_positions: riskRes.max_open_positions || 5,
          consecutive_loss_limit: riskRes.consecutive_loss_limit || 3,
        });
      }
      if (brokerRes) {
        setBrokers(brokerRes.brokers || []);
        setActiveBroker(brokerRes.active_broker || 'PAPER');
      }
    } catch (err) {
      console.error('Failed to load execution data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 10000);

    // Real-time SSE Telemetry connection for instant execution updates
    const stream = connectTelemetryStream({
      onPaperPositionOpened: () => {
        fetchAllData();
        if (showToast) showToast('⚡ Paper Trade Position Opened', 'info');
      },
      onPaperPositionClosed: (data) => {
        fetchAllData();
        const outcome = data?.trade?.outcome;
        const msg = `Position Closed [${data?.trade?.symbol}]: ${data?.trade?.reason} (${data?.trade?.pnl_pct}%)`;
        if (showToast) showToast(msg, outcome === 'WIN' ? 'success' : 'error');
      },
      onPaperPositionModified: () => {
        fetchAllData();
      },
      onCircuitBreakerTripped: (data) => {
        fetchAllData();
        if (showToast) showToast(`🚨 Circuit Breaker Tripped: ${data?.message || 'Trading Halted'}`, 'error');
      },
      onCircuitBreakerReset: () => {
        fetchAllData();
        if (showToast) showToast('✅ Circuit Breaker restored to NORMAL.', 'success');
      },
      onEmergencyHaltTripped: () => {
        fetchAllData();
        if (showToast) showToast('🛑 EMERGENCY KILL SWITCH ACTIVATED. All positions squared off.', 'error');
      },
      onCycleUpdate: () => {
        // Refetch MTM valuations after scan cycle
        api.getPaperPortfolio().then((p) => p && setPortfolio(p)).catch(() => {});
        api.getPaperPositions().then((pos) => Array.isArray(pos) && setPositions(pos)).catch(() => {});
        api.getRiskStatus().then((r) => r && setRiskStatus(r)).catch(() => {});
      },
    });

    return () => {
      clearInterval(interval);
      stream.close();
    };
  }, [showToast]);

  // Square Off Position Handler
  const handleSquareOff = async (positionId, symbol) => {
    if (!confirm(`Are you sure you want to square off the open position in ${symbol}?`)) return;
    setActionInProgress(true);
    try {
      await api.closePaperPosition(positionId);
      if (showToast) showToast(`Position in ${symbol} squared off successfully.`);
      await fetchAllData();
    } catch (err) {
      if (showToast) showToast(`Failed to square off: ${err.message}`, 'error');
    } finally {
      setActionInProgress(false);
    }
  };

  // Open Edit Brackets Modal
  const handleOpenEdit = (pos) => {
    setEditingPosition(pos);
    setEditForm({
      stop_loss: pos.stop_loss || '',
      target: pos.target || '',
      trailing_sl: pos.trailing_sl || '',
    });
  };

  // Submit Bracket Modifications
  const handleSubmitModify = async (e) => {
    e.preventDefault();
    if (!editingPosition) return;
    setActionInProgress(true);
    try {
      await api.modifyPaperPosition(editingPosition.position_id, {
        stop_loss: parseFloat(editForm.stop_loss),
        target: parseFloat(editForm.target),
        trailing_sl: editForm.trailing_sl ? parseFloat(editForm.trailing_sl) : null,
      });
      if (showToast) showToast(`Brackets updated for ${editingPosition.symbol}.`);
      setEditingPosition(null);
      await fetchAllData();
    } catch (err) {
      if (showToast) showToast(`Failed to update brackets: ${err.message}`, 'error');
    } finally {
      setActionInProgress(false);
    }
  };

  // Reset Account Handler
  const handleConfirmReset = async () => {
    setActionInProgress(true);
    try {
      await api.resetPaperAccount({ initial_capital: parseFloat(resetCapital) || 1000000 });
      if (showToast) showToast('Virtual paper trading portfolio reset to starting capital.');
      setShowResetModal(false);
      await fetchAllData();
    } catch (err) {
      if (showToast) showToast(`Reset failed: ${err.message}`, 'error');
    } finally {
      setActionInProgress(false);
    }
  };

  // Phase 7 Handlers
  const handleSelectBroker = async (bName) => {
    try {
      await api.selectBroker(bName);
      setActiveBroker(bName);
      if (showToast) showToast(`Execution Broker switched to ${bName}`);
      await fetchAllData();
    } catch (err) {
      if (showToast) showToast(`Failed switching broker: ${err.message}`, 'error');
    }
  };

  const handleEmergencyKillSwitch = async () => {
    setActionInProgress(true);
    try {
      await api.emergencySquareOff({ reason: 'Operator Panic Kill Switch via Dashboard' });
      setShowEmergencyModal(false);
      if (showToast) showToast('🛑 EMERGENCY KILL SWITCH ACTIVATED. All positions squared off.', 'error');
      await fetchAllData();
    } catch (err) {
      if (showToast) showToast(`Emergency square-off failed: ${err.message}`, 'error');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleResetBreaker = async () => {
    setActionInProgress(true);
    try {
      await api.resetCircuitBreaker();
      if (showToast) showToast('✅ Circuit Breaker restored to NORMAL.', 'success');
      await fetchAllData();
    } catch (err) {
      if (showToast) showToast(`Reset failed: ${err.message}`, 'error');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleSaveRiskConfig = async (e) => {
    e.preventDefault();
    setActionInProgress(true);
    try {
      await api.updateRiskConfig({
        max_daily_loss_pct: parseFloat(riskForm.max_daily_loss_pct) / 100.0,
        max_open_positions: parseInt(riskForm.max_open_positions, 10),
        consecutive_loss_limit: parseInt(riskForm.consecutive_loss_limit, 10),
      });
      setShowRiskModal(false);
      if (showToast) showToast('Risk guard parameters updated successfully.');
      await fetchAllData();
    } catch (err) {
      if (showToast) showToast(`Failed saving risk config: ${err.message}`, 'error');
    } finally {
      setActionInProgress(false);
    }
  };

  // Filtered positions & trades
  const filteredPositions = useMemo(() => {
    return positions.filter((p) => {
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      return p.symbol.toLowerCase().includes(q) || (p.algo_name || '').toLowerCase().includes(q);
    });
  }, [positions, searchQuery]);

  const filteredTrades = useMemo(() => {
    return trades.filter((t) => {
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      return t.symbol.toLowerCase().includes(q) || (t.algo_name || '').toLowerCase().includes(q);
    });
  }, [trades, searchQuery]);

  const currencySymbol = portfolio?.currency === 'USD' ? '$' : '₹';
  const unrealizedPnL = portfolio?.unrealized_pnl || 0;
  const realizedPnL = portfolio?.realized_pnl || 0;
  const isUnrealizedPos = unrealizedPnL >= 0;
  const isRealizedPos = realizedPnL >= 0;

  return (
    <div style={{ padding: '24px', maxWidth: '1600px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* ========================================================================= */}
      {/* 1. TOP ACTIONS & BROKER SELECTOR                                         */}
      {/* ========================================================================= */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>

        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          {/* Broker Selector */}
          <div style={{ display: 'flex', alignItems: 'center', background: 'rgba(15, 23, 42, 0.6)', border: '1px solid #334155', borderRadius: '6px', padding: '2px 4px' }}>
            <span style={{ fontSize: '0.7rem', color: '#94a3b8', padding: '0 6px', fontWeight: '700' }}>BROKER:</span>
            {['PAPER', 'ZERODHA', 'INTERACTIVE_BROKERS'].map((b) => (
              <button
                key={b}
                onClick={() => handleSelectBroker(b)}
                style={{
                  fontSize: '0.72rem',
                  fontWeight: '700',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  border: 'none',
                  background: activeBroker === b ? '#3b82f6' : 'transparent',
                  color: activeBroker === b ? '#ffffff' : '#94a3b8',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {b === 'INTERACTIVE_BROKERS' ? 'IBKR' : b}
              </button>
            ))}
          </div>

          <button
            onClick={() => setShowRiskModal(true)}
            className="btn btn-cancel"
            style={{ fontSize: '0.78rem', padding: '7px 12px' }}
            title="Configure Risk Guard & Circuit Breaker parameters"
          >
            <ShieldCheck style={{ width: '13px', height: '13px', color: '#38bdf8' }} />
            <span>Risk Guard</span>
          </button>

          <button
            onClick={fetchAllData}
            disabled={actionInProgress}
            className="btn btn-cancel"
            style={{ fontSize: '0.78rem', padding: '7px 12px' }}
          >
            <RefreshCw style={{ width: '13px', height: '13px' }} />
            <span>Refresh</span>
          </button>

          <button
            onClick={() => setShowEmergencyModal(true)}
            className="btn btn-stop"
            style={{
              fontSize: '0.78rem',
              padding: '7px 14px',
              background: 'linear-gradient(135deg, #ef4444 0%, #b91c1c 100%)',
              color: '#ffffff',
              border: '1px solid #f87171',
              boxShadow: '0 0 12px rgba(239, 68, 68, 0.4)',
            }}
            title="Immediately closes all positions and trips circuit breaker"
          >
            <AlertTriangle style={{ width: '13px', height: '13px' }} />
            <span>EMERGENCY KILL SWITCH</span>
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 1.5 RISK GUARD & CIRCUIT BREAKER TELEMETRY BAR (PHASE 7)                  */}
      {/* ========================================================================= */}
      {riskStatus && (
        <div className="glass-panel" style={{
          padding: '12px 18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '14px',
          borderLeft: riskStatus.status === 'NORMAL' ? '3px solid #10b981' : (riskStatus.status === 'WARNING' ? '3px solid #f59e0b' : '3px solid #ef4444'),
          background: riskStatus.status === 'NORMAL' ? 'rgba(15, 23, 42, 0.5)' : (riskStatus.status === 'WARNING' ? 'rgba(245, 158, 11, 0.08)' : 'rgba(239, 68, 68, 0.12)'),
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontWeight: '700' }}>CIRCUIT BREAKER:</span>
              <span style={{
                padding: '3px 8px',
                borderRadius: '4px',
                fontSize: '0.72rem',
                fontWeight: '800',
                fontFamily: 'monospace',
                background: riskStatus.status === 'NORMAL' ? 'rgba(16, 185, 129, 0.2)' : (riskStatus.status === 'WARNING' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(239, 68, 68, 0.25)'),
                color: riskStatus.status === 'NORMAL' ? '#34d399' : (riskStatus.status === 'WARNING' ? '#fbbf24' : '#f87171'),
              }}>
                {riskStatus.status === 'NORMAL' && '🟢 NORMAL (OPERATIONAL)'}
                {riskStatus.status === 'WARNING' && '🟡 WARNING (NEAR LOSS LIMIT)'}
                {riskStatus.status === 'TRIPPED_MAX_LOSS' && '🔴 TRIPPED: MAX LOSS BREACHED'}
                {riskStatus.status === 'TRIPPED_CONSECUTIVE' && '🔴 TRIPPED: CONSECUTIVE LOSSES'}
                {riskStatus.status === 'EMERGENCY_HALT' && '🛑 EMERGENCY HALT ACTIVE'}
              </span>
            </div>

            <div style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>
              <span style={{ color: '#94a3b8' }}>Daily Drawdown: </span>
              <span style={{ fontWeight: '700', color: riskStatus.drawdown_pct > 0 ? '#f87171' : '#34d399' }}>
                {currencySymbol}{riskStatus.current_drawdown?.toLocaleString('en-IN') || 0} ({riskStatus.drawdown_pct || 0}%)
              </span>
              <span style={{ color: '#64748b' }}> / Max {riskStatus.max_daily_loss_pct}%</span>
            </div>

            <div style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>
              <span style={{ color: '#94a3b8' }}>Open Exposure: </span>
              <span style={{ fontWeight: '700', color: riskStatus.active_positions_count >= riskStatus.max_open_positions ? '#f87171' : '#f8fafc' }}>
                {riskStatus.active_positions_count || 0} / {riskStatus.max_open_positions} Positions
              </span>
            </div>

            <div style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>
              <span style={{ color: '#94a3b8' }}>Consecutive Losses: </span>
              <span style={{ fontWeight: '700', color: riskStatus.consecutive_losses > 0 ? '#f87171' : '#f8fafc' }}>
                {riskStatus.consecutive_losses || 0} / {riskStatus.consecutive_loss_limit}
              </span>
            </div>
          </div>

          {riskStatus.status !== 'NORMAL' && (
            <button
              onClick={handleResetBreaker}
              disabled={actionInProgress}
              className="btn btn-primary"
              style={{ fontSize: '0.75rem', padding: '5px 12px', background: '#10b981' }}
            >
              <RotateCcw style={{ width: '12px', height: '12px' }} />
              <span>Reset Circuit Breaker</span>
            </button>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 2. INSTITUTIONAL PORTFOLIO RIBBON                                         */}
      {/* ========================================================================= */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        
        {/* Card 1: Total Account Equity */}
        <div className="glass-panel" style={{ padding: '18px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.75rem', fontWeight: '600', marginBottom: '6px' }}>
            <span>Total Account Equity</span>
            <DollarSign style={{ width: '15px', height: '15px', color: '#38bdf8' }} />
          </div>
          <div style={{ fontSize: '1.9rem', fontWeight: '800', color: '#ffffff', fontFamily: 'monospace', letterSpacing: '-0.03em' }}>
            {currencySymbol}{portfolio?.total_equity ? portfolio.total_equity.toLocaleString('en-IN') : '10,00,000'}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px', fontSize: '0.72rem', color: '#94a3b8' }}>
            <span>Starting Capital</span>
            <span>{currencySymbol}{portfolio?.initial_capital ? portfolio.initial_capital.toLocaleString('en-IN') : '10,00,000'}</span>
          </div>
        </div>

        {/* Card 2: Cash & Margin Utilization */}
        <div className="glass-panel" style={{ padding: '18px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.75rem', fontWeight: '600', marginBottom: '6px' }}>
            <span>Available Margin</span>
            <Zap style={{ width: '15px', height: '15px', color: '#f59e0b' }} />
          </div>
          <div style={{ fontSize: '1.9rem', fontWeight: '800', color: '#f8fafc', fontFamily: 'monospace', letterSpacing: '-0.03em' }}>
            {currencySymbol}{portfolio?.cash_balance ? portfolio.cash_balance.toLocaleString('en-IN') : '10,00,000'}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px', fontSize: '0.72rem', color: '#94a3b8' }}>
            <span>Used Margin</span>
            <span style={{ color: '#cbd5e1' }}>{currencySymbol}{portfolio?.used_margin ? portfolio.used_margin.toLocaleString('en-IN') : '0'}</span>
          </div>
        </div>

        {/* Card 3: Unrealized MTM PnL */}
        <div className="glass-panel" style={{ padding: '18px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.75rem', fontWeight: '600', marginBottom: '6px' }}>
            <span>Unrealized MTM PnL</span>
            {isUnrealizedPos ? (
              <ArrowUpRight style={{ width: '15px', height: '15px', color: '#34d399' }} />
            ) : (
              <ArrowDownRight style={{ width: '15px', height: '15px', color: '#f87171' }} />
            )}
          </div>
          <div style={{
            fontSize: '1.9rem',
            fontWeight: '800',
            color: isUnrealizedPos ? '#34d399' : '#f87171',
            fontFamily: 'monospace',
            letterSpacing: '-0.03em',
          }}>
            {isUnrealizedPos ? `+${currencySymbol}${unrealizedPnL.toFixed(2)}` : `${currencySymbol}${unrealizedPnL.toFixed(2)}`}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px', fontSize: '0.72rem', color: '#94a3b8' }}>
            <span>Active Positions</span>
            <span style={{ color: '#38bdf8', fontWeight: '700' }}>{positions.length} open</span>
          </div>
        </div>

        {/* Card 4: Realized PnL & Win Rate */}
        <div className="glass-panel" style={{ padding: '18px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.75rem', fontWeight: '600', marginBottom: '6px' }}>
            <span>Realized Return (PnL)</span>
            <ShieldCheck style={{ width: '15px', height: '15px', color: '#c084fc' }} />
          </div>
          <div style={{
            fontSize: '1.9rem',
            fontWeight: '800',
            color: isRealizedPos ? '#34d399' : '#f87171',
            fontFamily: 'monospace',
            letterSpacing: '-0.03em',
          }}>
            {isRealizedPos ? `+${currencySymbol}${realizedPnL.toFixed(2)}` : `${currencySymbol}${realizedPnL.toFixed(2)}`}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px', fontSize: '0.72rem', color: '#94a3b8' }}>
            <span>Win Rate: <strong style={{ color: '#34d399' }}>{portfolio?.win_rate_pct || 0}%</strong></span>
            <span>{portfolio?.closed_trades_count || 0} trades</span>
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 3. NAVIGATION SUB-TABS & SEARCH                                          */}
      {/* ========================================================================= */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        paddingBottom: '8px',
        flexWrap: 'wrap',
        gap: '12px',
      }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setActiveTab('positions')}
            className={activeTab === 'positions' ? 'btn btn-blue' : 'btn btn-cancel'}
            style={{ padding: '7px 16px', fontSize: '0.8rem' }}
          >
            Open Positions ({positions.length})
          </button>
          <button
            onClick={() => setActiveTab('trades')}
            className={activeTab === 'trades' ? 'btn btn-blue' : 'btn btn-cancel'}
            style={{ padding: '7px 16px', fontSize: '0.8rem' }}
          >
            Closed Trade History ({trades.length})
          </button>
        </div>

        {/* Search */}
        <div style={{ position: 'relative', width: '260px' }}>
          <Search style={{ position: 'absolute', left: '10px', top: '8px', width: '13px', height: '13px', color: '#64748b' }} />
          <input
            type="text"
            placeholder="Search symbol or strategy..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ width: '100%', paddingLeft: '30px', fontSize: '0.78rem', padding: '5px 10px 5px 30px' }}
          />
        </div>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: OPEN POSITIONS TABLE                                              */}
      {/* ========================================================================= */}
      {activeTab === 'positions' && (
        <div className="glass-panel" style={{ overflow: 'hidden' }}>
          <div style={{
            padding: '14px 20px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: '700', color: '#ffffff' }}>
              Active Mark-to-Market Positions ({filteredPositions.length})
            </h3>
            <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
              Auto-monitored against live tick highs/lows for Target &amp; Stop Loss triggers
            </span>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8125rem' }}>
              <thead>
                <tr style={{
                  background: 'rgba(15, 23, 42, 0.65)',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                  color: '#94a3b8',
                  fontSize: '0.7rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}>
                  <th style={{ padding: '12px 16px' }}>Position ID</th>
                  <th style={{ padding: '12px 14px' }}>Symbol</th>
                  <th style={{ padding: '12px 14px' }}>Side / Direction</th>
                  <th style={{ padding: '12px 14px' }}>Qty</th>
                  <th style={{ padding: '12px 14px' }}>Entry Price</th>
                  <th style={{ padding: '12px 14px' }}>Current Price (LTP)</th>
                  <th style={{ padding: '12px 14px' }}>Stop Loss / Target</th>
                  <th style={{ padding: '12px 14px' }}>Trailing SL</th>
                  <th style={{ padding: '12px 14px' }}>Unrealized PnL</th>
                  <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredPositions.length === 0 ? (
                  <tr>
                    <td colSpan="10" style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
                      No open positions at this moment. Trigger a strategy scan cycle to enter positions on confirmed setups.
                    </td>
                  </tr>
                ) : (
                  filteredPositions.map((pos) => {
                    const isLong = pos.side === 'BUY';
                    const pnlPts = pos.unrealized_pnl || 0;
                    const isWin = pnlPts >= 0;

                    return (
                      <tr
                        key={pos.position_id}
                        style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)', transition: 'background 0.15s' }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                      >
                        {/* ID & Strategy */}
                        <td style={{ padding: '12px 16px' }}>
                          <div style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: '#94a3b8' }}>
                            {pos.position_id}
                          </div>
                          <div style={{ fontSize: '0.68rem', color: '#cbd5e1' }}>
                            {pos.algo_name || 'AlgoTrade'}
                          </div>
                        </td>

                        {/* Symbol */}
                        <td style={{ padding: '12px 14px', fontWeight: '800', color: '#ffffff', fontFamily: 'monospace' }}>
                          {pos.symbol}
                        </td>

                        {/* Side & Direction */}
                        <td style={{ padding: '12px 14px' }}>
                          <span className={`badge ${isLong ? 'badge-call' : 'badge-put'}`}>
                            {isLong ? 'LONG / BUY' : 'SHORT / SELL'}
                          </span>
                        </td>

                        {/* Quantity */}
                        <td style={{ padding: '12px 14px', fontFamily: 'monospace', fontWeight: '600' }}>
                          {pos.quantity}
                        </td>

                        {/* Entry Price */}
                        <td style={{ padding: '12px 14px', fontFamily: 'monospace', color: '#cbd5e1' }}>
                          {currencySymbol}{pos.entry_price}
                        </td>

                        {/* Current Price */}
                        <td style={{ padding: '12px 14px', fontFamily: 'monospace', fontWeight: '700', color: '#ffffff' }}>
                          {currencySymbol}{pos.current_price}
                        </td>

                        {/* Stop Loss & Target */}
                        <td style={{ padding: '12px 14px', fontSize: '0.75rem', fontFamily: 'monospace' }}>
                          SL: <span style={{ color: '#f87171' }}>{currencySymbol}{pos.stop_loss}</span> | TGT: <span style={{ color: '#34d399' }}>{currencySymbol}{pos.target}</span>
                        </td>

                        {/* Trailing Stop Loss */}
                        <td style={{ padding: '12px 14px', fontSize: '0.75rem', fontFamily: 'monospace' }}>
                          {pos.trailing_sl ? (
                            <span style={{ color: '#fbbf24', fontWeight: '600' }}>
                              {currencySymbol}{pos.trailing_sl}
                            </span>
                          ) : (
                            <span style={{ color: '#64748b' }}>--</span>
                          )}
                        </td>

                        {/* Unrealized PnL */}
                        <td style={{ padding: '12px 14px' }}>
                          <div style={{ fontWeight: '800', color: isWin ? '#34d399' : '#f87171', fontFamily: 'monospace' }}>
                            {isWin ? `+${currencySymbol}${pos.unrealized_pnl}` : `${currencySymbol}${pos.unrealized_pnl}`}
                          </div>
                          <div style={{ fontSize: '0.68rem', color: isWin ? '#34d399' : '#f87171' }}>
                            ({isWin ? `+${pos.unrealized_pnl_pct}%` : `${pos.unrealized_pnl_pct}%`})
                          </div>
                        </td>

                        {/* Actions */}
                        <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                            {/* Edit Brackets */}
                            <button
                              onClick={() => handleOpenEdit(pos)}
                              className="btn btn-cancel"
                              style={{ padding: '4px 8px', fontSize: '0.72rem' }}
                              title="Modify SL & Target Brackets"
                            >
                              <Sliders style={{ width: '12px', height: '12px', color: '#38bdf8' }} />
                            </button>

                            {/* Square Off */}
                            <button
                              onClick={() => handleSquareOff(pos.position_id, pos.symbol)}
                              disabled={actionInProgress}
                              className="btn btn-stop"
                              style={{ padding: '4px 10px', fontSize: '0.72rem' }}
                              title="Market Square-off"
                            >
                              <Square style={{ width: '11px', height: '11px', fill: '#f87171' }} />
                              <span>Square Off</span>
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: CLOSED TRADE HISTORY                                               */}
      {/* ========================================================================= */}
      {activeTab === 'trades' && (
        <div className="glass-panel" style={{ overflow: 'hidden' }}>
          <div style={{
            padding: '14px 20px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: '700', color: '#ffffff' }}>
              Historical Closed Paper Executions ({filteredTrades.length})
            </h3>
            <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
              Synced with Prisma PostgreSQL pnl_trades table
            </span>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8125rem' }}>
              <thead>
                <tr style={{
                  background: 'rgba(15, 23, 42, 0.65)',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                  color: '#94a3b8',
                  fontSize: '0.7rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}>
                  <th style={{ padding: '12px 16px' }}>Trade Reference</th>
                  <th style={{ padding: '12px 14px' }}>Symbol &amp; Side</th>
                  <th style={{ padding: '12px 14px' }}>Entry Price</th>
                  <th style={{ padding: '12px 14px' }}>Exit Price</th>
                  <th style={{ padding: '12px 14px' }}>Outcome</th>
                  <th style={{ padding: '12px 14px' }}>Exit Reason</th>
                  <th style={{ padding: '12px 14px' }}>Net Points</th>
                  <th style={{ padding: '12px 14px' }}>Realized Return %</th>
                  <th style={{ padding: '12px 16px' }}>Exit Time</th>
                </tr>
              </thead>
              <tbody>
                {filteredTrades.length === 0 ? (
                  <tr>
                    <td colSpan="9" style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
                      No trades closed yet in this session.
                    </td>
                  </tr>
                ) : (
                  filteredTrades.map((trd, idx) => {
                    const isWin = trd.outcome === 'WIN';
                    return (
                      <tr
                        key={idx}
                        style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}
                      >
                        <td style={{ padding: '12px 16px', fontFamily: 'monospace', color: '#94a3b8', fontSize: '0.72rem' }}>
                          {trd.trade_id || trd.position_id}
                        </td>
                        <td style={{ padding: '12px 14px' }}>
                          <span style={{ fontWeight: '700', color: '#ffffff', fontFamily: 'monospace' }}>
                            {trd.symbol}
                          </span>
                          <span style={{ marginLeft: '6px', fontSize: '0.7rem', color: trd.side === 'BUY' ? '#34d399' : '#f87171' }}>
                            [{trd.side}]
                          </span>
                        </td>
                        <td style={{ padding: '12px 14px', fontFamily: 'monospace' }}>
                          {currencySymbol}{trd.entry_price}
                        </td>
                        <td style={{ padding: '12px 14px', fontFamily: 'monospace', fontWeight: '700', color: '#ffffff' }}>
                          {currencySymbol}{trd.exit_price}
                        </td>
                        <td style={{ padding: '12px 14px' }}>
                          <span className={`badge ${isWin ? 'badge-running' : 'badge-stopped'}`}>
                            {trd.outcome}
                          </span>
                        </td>
                        <td style={{ padding: '12px 14px', fontSize: '0.75rem', color: '#cbd5e1' }}>
                          {trd.reason || 'SQUARE_OFF'}
                        </td>
                        <td style={{ padding: '12px 14px', fontWeight: '700', color: isWin ? '#34d399' : '#f87171', fontFamily: 'monospace' }}>
                          {trd.pnl_points > 0 ? `+${trd.pnl_points}` : trd.pnl_points}
                        </td>
                        <td style={{ padding: '12px 14px', fontWeight: '800', color: isWin ? '#34d399' : '#f87171', fontFamily: 'monospace' }}>
                          {trd.pnl_pct > 0 ? `+${trd.pnl_pct}%` : `${trd.pnl_pct}%`}
                        </td>
                        <td style={{ padding: '12px 16px', fontSize: '0.72rem', color: '#94a3b8' }}>
                          {trd.exit_time || trd.timestamp}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 1: EDIT POSITION BRACKETS (SL, Target, Trailing Stop)              */}
      {/* ========================================================================= */}
      {editingPosition && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.8)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 70,
          padding: '20px',
        }}>
          <div className="glass-panel" style={{ width: '100%', maxWidth: '480px', padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '12px' }}>
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#ffffff' }}>
                  Modify Brackets: {editingPosition.symbol}
                </h3>
                <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  Entry: {currencySymbol}{editingPosition.entry_price} | LTP: {currencySymbol}{editingPosition.current_price}
                </p>
              </div>
              <button onClick={() => setEditingPosition(null)} className="btn btn-cancel" style={{ padding: '6px' }}>
                <X style={{ width: '16px', height: '16px' }} />
              </button>
            </div>

            <form onSubmit={handleSubmitModify}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '20px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '4px' }}>
                    Stop Loss Price ({currencySymbol})
                  </label>
                  <input
                    type="number"
                    step="0.05"
                    required
                    value={editForm.stop_loss}
                    onChange={(e) => setEditForm({ ...editForm, stop_loss: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '4px' }}>
                    Take Profit Target Price ({currencySymbol})
                  </label>
                  <input
                    type="number"
                    step="0.05"
                    required
                    value={editForm.target}
                    onChange={(e) => setEditForm({ ...editForm, target: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '4px' }}>
                    Trailing Stop Loss ({currencySymbol}, optional)
                  </label>
                  <input
                    type="number"
                    step="0.05"
                    value={editForm.trailing_sl}
                    onChange={(e) => setEditForm({ ...editForm, trailing_sl: e.target.value })}
                    placeholder="Leave blank for static SL"
                    style={{ width: '100%' }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button type="button" onClick={() => setEditingPosition(null)} className="btn btn-cancel">
                  Cancel
                </button>
                <button type="submit" disabled={actionInProgress} className="btn btn-execute">
                  <Check style={{ width: '14px', height: '14px' }} />
                  <span>Update Brackets</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 2: RESET PAPER TRADING ACCOUNT                                      */}
      {/* ========================================================================= */}
      {showResetModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.8)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 70,
          padding: '20px',
        }}>
          <div className="glass-panel" style={{ width: '100%', maxWidth: '440px', padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
              <AlertTriangle style={{ width: '22px', height: '22px', color: '#f87171' }} />
              <h3 style={{ fontSize: '1.15rem', fontWeight: '800', color: '#ffffff' }}>
                Reset Paper Account?
              </h3>
            </div>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.5, marginBottom: '16px' }}>
              This will close all active open positions, clear order history, and reset virtual cash balance to the specified capital.
            </p>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>
                Starting Virtual Capital ({currencySymbol})
              </label>
              <input
                type="number"
                step="10000"
                min="10000"
                value={resetCapital}
                onChange={(e) => setResetCapital(e.target.value)}
                style={{ width: '100%' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button onClick={() => setShowResetModal(false)} className="btn btn-cancel">
                Cancel
              </button>
              <button
                onClick={handleConfirmReset}
                disabled={actionInProgress}
                className="btn btn-stop"
              >
                <span>Confirm Reset</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 3: RISK GUARD & CIRCUIT BREAKER CONFIG (PHASE 7)                    */}
      {/* ========================================================================= */}
      {showRiskModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.8)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 70,
          padding: '20px',
        }}>
          <div className="glass-panel" style={{ width: '100%', maxWidth: '480px', padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck style={{ width: '20px', height: '20px', color: '#38bdf8' }} />
                <h3 style={{ fontSize: '1.15rem', fontWeight: '800', color: '#ffffff' }}>
                  Risk Guard &amp; Circuit Breaker
                </h3>
              </div>
              <button onClick={() => setShowRiskModal(false)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
                <X style={{ width: '18px', height: '18px' }} />
              </button>
            </div>

            <form onSubmit={handleSaveRiskConfig} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '4px' }}>
                  Maximum Daily Drawdown Limit (%)
                </label>
                <input
                  type="number"
                  step="0.5"
                  min="0.5"
                  max="50"
                  required
                  value={riskForm.max_daily_loss_pct}
                  onChange={(e) => setRiskForm({ ...riskForm, max_daily_loss_pct: e.target.value })}
                  style={{ width: '100%' }}
                />
                <span style={{ fontSize: '0.68rem', color: '#64748b' }}>If daily losses exceed this %, trading halts automatically.</span>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '4px' }}>
                  Maximum Open Positions (Concurrency)
                </label>
                <input
                  type="number"
                  step="1"
                  min="1"
                  max="50"
                  required
                  value={riskForm.max_open_positions}
                  onChange={(e) => setRiskForm({ ...riskForm, max_open_positions: e.target.value })}
                  style={{ width: '100%' }}
                />
                <span style={{ fontSize: '0.68rem', color: '#64748b' }}>Blocks new signals if open positions reach this threshold.</span>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '4px' }}>
                  Consecutive Loss Limit (Streak Guard)
                </label>
                <input
                  type="number"
                  step="1"
                  min="1"
                  max="10"
                  required
                  value={riskForm.consecutive_loss_limit}
                  onChange={(e) => setRiskForm({ ...riskForm, consecutive_loss_limit: e.target.value })}
                  style={{ width: '100%' }}
                />
                <span style={{ fontSize: '0.68rem', color: '#64748b' }}>Triggers 30-min cooling off period after consecutive losses.</span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '8px' }}>
                <button type="button" onClick={() => setShowRiskModal(false)} className="btn btn-cancel">
                  Cancel
                </button>
                <button type="submit" disabled={actionInProgress} className="btn btn-execute">
                  <Check style={{ width: '14px', height: '14px' }} />
                  <span>Save Risk Limits</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 4: EMERGENCY KILL SWITCH CONFIRMATION                               */}
      {/* ========================================================================= */}
      {showEmergencyModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.85)',
          backdropFilter: 'blur(10px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 80,
          padding: '20px',
        }}>
          <div className="glass-panel" style={{
            width: '100%',
            maxWidth: '460px',
            padding: '26px',
            border: '2px solid #ef4444',
            boxShadow: '0 0 30px rgba(239, 68, 68, 0.3)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
              <AlertTriangle style={{ width: '28px', height: '28px', color: '#ef4444' }} />
              <div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: '900', color: '#ef4444', letterSpacing: '-0.02em' }}>
                  ACTIVATE EMERGENCY KILL SWITCH?
                </h3>
                <span style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>Immediate Capital Liquidation</span>
              </div>
            </div>

            <p style={{ fontSize: '0.82rem', color: '#cbd5e1', lineHeight: 1.5, marginBottom: '20px' }}>
              This action will <strong>immediately close all open positions</strong> across all connected brokers (Paper and Live), cancel all pending orders, stop active AlgoTrades, and trip the circuit breaker into <strong>EMERGENCY_HALT</strong> mode.
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button onClick={() => setShowEmergencyModal(false)} className="btn btn-cancel">
                Cancel / Return
              </button>
              <button
                onClick={handleEmergencyKillSwitch}
                disabled={actionInProgress}
                className="btn btn-stop"
                style={{
                  background: '#ef4444',
                  color: '#ffffff',
                  fontWeight: '800',
                  boxShadow: '0 0 16px rgba(239, 68, 68, 0.6)',
                }}
              >
                <span>LIQUIDATE &amp; HALT NOW</span>
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
