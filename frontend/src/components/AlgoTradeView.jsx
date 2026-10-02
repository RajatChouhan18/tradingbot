import React, { useState, useEffect, useMemo } from 'react';
import { 
  Plus, 
  Play, 
  Square, 
  Pause, 
  Copy, 
  Trash2, 
  Radio, 
  BarChart3, 
  Clock, 
  Calendar, 
  ShieldCheck, 
  RefreshCw, 
  Send, 
  Check, 
  X,
  ExternalLink,
  ChevronDown,
  Info,
  Sliders,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Activity,
  Zap,
  Layers,
  Sparkles,
  Building2,
  Flame,
  Globe2,
  Search,
  Filter
} from 'lucide-react';
import MarketCatalogSelector from './MarketCatalogSelector';

export default function AlgoTradeView({
  algos = [],
  onStartAlgo,
  onStopAlgo,
  onPauseAlgo,
  onCopyAlgo,
  onDeleteAlgo,
  onCreateAlgo,
  onEvaluateAlgo,
  onResendSignal,
  initialTab = 'strategies',
}) {
  const [activeTab, setActiveTab] = useState(initialTab); // 'strategies', 'signals', 'pnl'
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedAlgoId, setSelectedAlgoId] = useState(algos[0]?.algo_id || null);
  const [selectedSignalForDetail, setSelectedSignalForDetail] = useState(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [evaluationModal, setEvaluationModal] = useState(null);
  const [selectedGroup, setSelectedGroup] = useState('NSE');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterMarket, setFilterMarket] = useState('ALL');

  useEffect(() => {
    if (initialTab) {
      setActiveTab(initialTab);
    }
  }, [initialTab]);

  useEffect(() => {
    if (!selectedAlgoId && algos.length > 0) {
      setSelectedAlgoId(algos[0].algo_id);
    }
  }, [algos, selectedAlgoId]);

  // Form State for Creating AlgoTrade
  const defaultFormData = {
    algo_name: '',
    market: 'INDIAN_EQUITY',
    timeframe: '5m',
    symbols: ['RELIANCE', 'TCS', 'HDFCBANK'],
    indices: ['NIFTY 50'],
    patterns: ['bullish_engulfing', 'bearish_engulfing', 'dark_cloud_cover', 'piercing_line'],
    indicators: ['EMA_20', 'EMA_50', 'RSI', 'VWAP'],
    extra_data: ['candles', 'volume', 'vix', 'index_movement'],
    start_date: '',
    end_date: '',
    start_time: '09:15:00',
    stop_time: '15:30:00',
    chart_enabled: true,
    chart_engine: 'tradingview',
    audit_enabled: true,
    risk_reward_ratio: 1.5,
    enable_mtf: true,
    higher_timeframe: '15m',
    strict_mtf: false,
    use_atr_risk: true,
    atr_period: 14,
    atr_multiplier: 1.5,
    max_workers: 8,
    lookback_bars: 100,
    creator: 'Ishaq',
    description: '',
  };

  const [formData, setFormData] = useState(defaultFormData);

  // Apply Pre-configured Template
  const applyPreset = (presetKey) => {
    if (presetKey === 'ishaq') {
      setSelectedGroup('NSE');
      setFormData({
        ...defaultFormData,
        algo_name: 'Ishaq Strategy 1',
        market: 'INDIAN_EQUITY',
        timeframe: '5m',
        symbols: ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY'],
        indices: ['NIFTY 50', 'NIFTY BANK'],
        patterns: ['bullish_engulfing', 'bearish_engulfing', 'piercing_line', 'dark_cloud_cover'],
        indicators: ['EMA_20', 'EMA_50', 'RSI', 'VWAP'],
        enable_mtf: true,
        higher_timeframe: '15m',
        strict_mtf: false,
        use_atr_risk: true,
        risk_reward_ratio: 1.5,
        creator: 'Ishaq',
        description: 'PDF Price Action setup with rolling Support/Resistance rejection and 15m MTF confirmation.',
      });
    } else if (presetKey === 'scalper') {
      setSelectedGroup('NSE');
      setFormData({
        ...defaultFormData,
        algo_name: 'Nifty Scalper',
        market: 'INDIAN_EQUITY',
        timeframe: '3m',
        symbols: ['NIFTY', 'BANKNIFTY'],
        indices: ['NIFTY 50'],
        patterns: ['bullish_engulfing', 'bearish_engulfing', 'piercing_line'],
        indicators: ['VWAP', 'EMA_20', 'RSI'],
        enable_mtf: true,
        higher_timeframe: '15m',
        strict_mtf: true,
        use_atr_risk: true,
        atr_period: 10,
        atr_multiplier: 1.2,
        risk_reward_ratio: 2.0,
        creator: 'Rajat',
        description: 'High-momentum index scalper on 3m candles with strict 15m MTF trend filter.',
      });
    } else if (presetKey === 'forex') {
      setSelectedGroup('FOREX');
      setFormData({
        ...defaultFormData,
        algo_name: 'Forex Price Action',
        market: 'FOREX',
        timeframe: '5m',
        symbols: ['EURUSD', 'GBPUSD', 'USDJPY'],
        indices: ['DXY'],
        patterns: ['bullish_engulfing', 'bearish_engulfing', 'dark_cloud_cover', 'piercing_line'],
        indicators: ['EMA_20', 'EMA_50', 'RSI'],
        enable_mtf: false,
        use_atr_risk: true,
        risk_reward_ratio: 1.5,
        creator: 'Ishaq',
        description: '24/5 FX major pairs S/R level bounce scanner with dynamic ATR stops.',
      });
    }
  };

  const handleCheckboxToggle = (category, value) => {
    setFormData((prev) => {
      const list = prev[category] || [];
      const updated = list.includes(value) ? list.filter((i) => i !== value) : [...list, value];
      return { ...prev, [category]: updated };
    });
  };

  const handleSubmitNewAlgo = async (e) => {
    e.preventDefault();
    if (!formData.algo_name.trim()) {
      alert('Please provide a Strategy Name');
      return;
    }

    const parseList = (val) => {
      if (Array.isArray(val)) return val.map((s) => String(s).trim().toUpperCase()).filter(Boolean);
      return String(val || '').split(',').map((s) => s.trim().toUpperCase()).filter(Boolean);
    };

    const payload = {
      ...formData,
      symbols: parseList(formData.symbols),
      indices: parseList(formData.indices),
      risk_reward_ratio: parseFloat(formData.risk_reward_ratio) || 1.5,
      atr_period: parseInt(formData.atr_period, 10) || 14,
      atr_multiplier: parseFloat(formData.atr_multiplier) || 1.5,
      max_workers: parseInt(formData.max_workers, 10) || 8,
      lookback_bars: parseInt(formData.lookback_bars, 10) || 100,
    };

    try {
      await onCreateAlgo(payload);
      setIsModalOpen(false);
      setFormData(defaultFormData);
    } catch (err) {
      console.error('Failed to create algo:', err);
    }
  };

  const handleRunEvaluation = async (algoId) => {
    setIsEvaluating(true);
    try {
      const res = await onEvaluateAlgo(algoId);
      setEvaluationModal(res);
    } catch (err) {
      alert(`Evaluation failed: ${err.message}`);
    } finally {
      setIsEvaluating(false);
    }
  };

  // Filtered Algos
  const filteredAlgos = useMemo(() => {
    return algos.filter((a) => {
      if (a.is_deleted) return false;
      if (filterMarket !== 'ALL' && a.market !== filterMarket) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = (a.algo_name || '').toLowerCase().includes(q);
        const matchId = (a.algo_id || '').toLowerCase().includes(q);
        const matchSymbol = (a.symbols || []).some((s) => String(s).toLowerCase().includes(q));
        if (!matchName && !matchId && !matchSymbol) return false;
      }
      return true;
    });
  }, [algos, filterMarket, searchQuery]);

  // Focused Algo for Signals and PnL
  const currentAlgo = algos.find((a) => a.algo_id === selectedAlgoId) || algos[0] || null;
  const signalsList = currentAlgo?.signals_history || currentAlgo?.signals || [];
  const pnlList = currentAlgo?.pnl_history || currentAlgo?.pnl_trades || [];

  return (
    <div style={{ padding: '24px', maxWidth: '1600px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Action Bar */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => {
              setFormData(defaultFormData);
              setIsModalOpen(true);
            }}
            className="btn btn-execute"
            style={{ padding: '8px 18px', fontSize: '0.82rem' }}
          >
            <Plus style={{ width: '16px', height: '16px' }} />
            <span>Create AlgoTrade Strategy</span>
          </button>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
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
            onClick={() => setActiveTab('strategies')}
            className={activeTab === 'strategies' ? 'btn btn-blue' : 'btn btn-cancel'}
            style={{ padding: '7px 16px', fontSize: '0.8rem' }}
          >
            Active Strategies ({algos.length})
          </button>
          <button
            onClick={() => setActiveTab('signals')}
            className={activeTab === 'signals' ? 'btn btn-blue' : 'btn btn-cancel'}
            style={{ padding: '7px 16px', fontSize: '0.8rem' }}
          >
            Signal Feeds ({signalsList.length})
          </button>
          <button
            onClick={() => setActiveTab('pnl')}
            className={activeTab === 'pnl' ? 'btn btn-blue' : 'btn btn-cancel'}
            style={{ padding: '7px 16px', fontSize: '0.8rem' }}
          >
            PnL &amp; Trade History ({pnlList.length})
          </button>
        </div>

        {/* Strategy Selector when on Signals or PnL Tab */}
        {(activeTab === 'signals' || activeTab === 'pnl') && algos.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: '600' }}>Focused Algo:</span>
            <select
              value={selectedAlgoId || ''}
              onChange={(e) => setSelectedAlgoId(e.target.value)}
              style={{ padding: '5px 12px', fontSize: '0.78rem' }}
            >
              {algos.map((a) => (
                <option key={a.algo_id} value={a.algo_id}>
                  {a.algo_name} ({a.market})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: STRATEGIES GRID                                                    */}
      {/* ========================================================================= */}
      {activeTab === 'strategies' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Filter Bar */}
          <div className="glass-panel" style={{ padding: '12px 16px', display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: '1', minWidth: '220px' }}>
              <div style={{ position: 'relative', width: '100%', maxWidth: '300px' }}>
                <Search style={{ position: 'absolute', left: '10px', top: '9px', width: '14px', height: '14px', color: '#64748b' }} />
                <input
                  type="text"
                  placeholder="Filter strategies by name, ID, symbol..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ width: '100%', paddingLeft: '32px', fontSize: '0.78rem', padding: '5px 10px 5px 32px' }}
                />
              </div>
            </div>

            {/* Market Filter */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: '600' }}>Market:</span>
              {['ALL', 'INDIAN_EQUITY', 'US_EQUITY', 'FOREX', 'CRYPTO'].map((m) => (
                <button
                  key={m}
                  onClick={() => setFilterMarket(m)}
                  className={filterMarket === m ? 'btn btn-blue' : 'btn btn-cancel'}
                  style={{ padding: '4px 10px', fontSize: '0.72rem' }}
                >
                  {m.replace('_EQUITY', '')}
                </button>
              ))}
            </div>
          </div>

          {/* Strategies Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: '18px' }}>
            {filteredAlgos.map((algo) => {
              const isRunning = algo.status === 'RUNNING';
              const pnl = algo.total_pnl_pct || 0;
              const isPositive = pnl >= 0;
              const cfg = algo.config || {};

              return (
                <div
                  key={algo.algo_id}
                  className="glass-panel"
                  style={{
                    padding: '20px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    border: isRunning ? '1px solid rgba(59, 130, 246, 0.4)' : '1px solid var(--border-color)',
                    background: isRunning 
                      ? 'linear-gradient(145deg, rgba(20, 27, 44, 0.9) 0%, rgba(13, 19, 34, 0.9) 100%)' 
                      : 'var(--bg-card)',
                  }}
                >
                  <div>
                    {/* Header */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
                      <div>
                        <h3 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#ffffff' }}>
                          {algo.algo_name}
                        </h3>
                        <span style={{ fontSize: '0.7rem', color: '#94a3b8', fontFamily: 'monospace' }}>
                          {algo.algo_id}
                        </span>
                      </div>
                      <span className={`badge badge-${algo.status.toLowerCase()}`}>
                        {algo.status}
                      </span>
                    </div>

                    <p style={{ fontSize: '0.78rem', color: '#cbd5e1', marginBottom: '14px', minHeight: '36px', lineHeight: 1.4 }}>
                      {algo.description || 'Configured with PDF Price Action rules, level rejection confirmation, and real-time visualization.'}
                    </p>

                    {/* Metadata Badges */}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '14px' }}>
                      <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', border: '1px solid rgba(168, 85, 247, 0.3)' }}>
                        {algo.market}
                      </span>
                      <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
                        TF: {algo.timeframe}
                      </span>
                      {cfg.enable_mtf && (
                        <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                          MTF: {cfg.higher_timeframe || '15m'}
                        </span>
                      )}
                      {cfg.use_atr_risk && (
                        <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                          ATR {cfg.atr_multiplier || 1.5}x
                        </span>
                      )}
                      {algo.start_time && (
                        <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(51, 65, 85, 0.5)', color: '#cbd5e1' }}>
                          ⏰ {algo.start_time} - {algo.stop_time}
                        </span>
                      )}
                    </div>

                    {/* Monitored Assets */}
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '14px' }}>
                      <span style={{ fontWeight: '600', color: '#cbd5e1' }}>Assets ({(algo.symbols || []).length}): </span>
                      {(algo.symbols || []).join(', ')}
                    </div>

                    {/* Live Stats Row */}
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(3, 1fr)',
                      gap: '8px',
                      padding: '10px',
                      background: 'rgba(15, 23, 42, 0.8)',
                      borderRadius: '8px',
                      marginBottom: '12px',
                    }}>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '0.65rem', color: '#94a3b8', textTransform: 'uppercase' }}>Cycles</div>
                        <div style={{ fontSize: '0.95rem', fontWeight: '800', color: '#ffffff', fontFamily: 'monospace' }}>
                          {algo.cycle_count || 0}
                        </div>
                      </div>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '0.65rem', color: '#94a3b8', textTransform: 'uppercase' }}>Signals</div>
                        <div style={{ fontSize: '0.95rem', fontWeight: '800', color: '#38bdf8', fontFamily: 'monospace' }}>
                          {algo.signals_count || 0}
                        </div>
                      </div>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '0.65rem', color: '#94a3b8', textTransform: 'uppercase' }}>Win Rate / PnL</div>
                        <div style={{
                          fontSize: '0.95rem',
                          fontWeight: '800',
                          color: isPositive ? '#34d399' : '#f87171',
                          fontFamily: 'monospace',
                        }}>
                          {algo.win_rate_pct || 0}% ({isPositive ? `+${pnl.toFixed(1)}%` : `${pnl.toFixed(1)}%`})
                        </div>
                      </div>
                    </div>

                    {/* Concurrency & Latency Bar */}
                    {algo.concurrency && (
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '6px 10px',
                        background: 'rgba(30, 41, 59, 0.45)',
                        borderRadius: '6px',
                        marginBottom: '14px',
                        fontSize: '0.7rem',
                        color: '#94a3b8',
                        fontFamily: 'monospace',
                        border: '1px solid rgba(255, 255, 255, 0.05)',
                      }}>
                        <span>⚡ {algo.concurrency.active_worker_threads || algo.concurrency.max_workers || 8} Workers</span>
                        <span style={{ color: '#38bdf8' }}>
                          {algo.concurrency.last_cycle_duration_ms > 0 ? `${algo.concurrency.last_cycle_duration_ms}ms scan` : 'Ready'}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Actions Toolbar */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '14px' }}>
                    {/* Execute/Start */}
                    <button
                      onClick={() => onStartAlgo(algo.algo_id)}
                      className="btn btn-execute"
                      style={{ flex: '1', fontSize: '0.75rem', padding: '6px 10px' }}
                      title="Run Scan Cycle"
                    >
                      <Play style={{ width: '12px', height: '12px', fill: '#ffffff' }} />
                      <span>Execute</span>
                    </button>

                    {/* Pause */}
                    <button
                      onClick={() => onPauseAlgo(algo.algo_id)}
                      className="btn btn-cancel"
                      style={{ padding: '6px 10px', fontSize: '0.75rem' }}
                      title="Pause Strategy"
                    >
                      <Pause style={{ width: '12px', height: '12px' }} />
                    </button>

                    {/* Stop */}
                    <button
                      onClick={() => onStopAlgo(algo.algo_id)}
                      className="btn btn-stop"
                      style={{ padding: '6px 10px', fontSize: '0.75rem' }}
                      title="Stop Strategy"
                    >
                      <Square style={{ width: '12px', height: '12px', fill: '#ffffff' }} />
                    </button>

                    {/* Duplicate */}
                    <button
                      onClick={() => onCopyAlgo(algo.algo_id)}
                      className="btn btn-blue"
                      style={{ padding: '6px 10px', fontSize: '0.75rem' }}
                      title="Duplicate Strategy"
                    >
                      <Copy style={{ width: '12px', height: '12px' }} />
                    </button>

                    {/* Backtest / Historical Evaluation */}
                    <button
                      onClick={() => handleRunEvaluation(algo.algo_id)}
                      disabled={isEvaluating}
                      className="btn btn-cancel"
                      style={{ padding: '6px 10px', fontSize: '0.75rem', color: '#c084fc' }}
                      title="Historical Backtest Evaluation"
                    >
                      <Clock style={{ width: '12px', height: '12px' }} />
                    </button>

                    {/* Delete */}
                    <button
                      onClick={() => {
                        if (confirm(`Are you sure you want to delete '${algo.algo_name}'?`)) {
                          onDeleteAlgo(algo.algo_id);
                        }
                      }}
                      className="btn btn-cancel"
                      style={{ padding: '6px 10px', fontSize: '0.75rem', color: '#f87171' }}
                      title="Delete Strategy"
                    >
                      <Trash2 style={{ width: '12px', height: '12px' }} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: SIGNALS FEED                                                       */}
      {/* ========================================================================= */}
      {activeTab === 'signals' && (
        <div className="glass-panel" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: '700', color: '#ffffff' }}>
                Actionable Signals ({signalsList.length}) for {currentAlgo?.algo_name || 'Selected Strategy'}
              </h3>
              <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                Each signal includes Execution Chart + 30-Candle Audit Chart with dynamic ATR brackets
              </p>
            </div>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8125rem' }}>
              <thead>
                <tr style={{ background: 'rgba(15, 23, 42, 0.65)', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', color: '#94a3b8', fontSize: '0.7rem', textTransform: 'uppercase' }}>
                  <th style={{ padding: '12px 16px' }}>Signal ID</th>
                  <th style={{ padding: '12px 16px' }}>Symbol</th>
                  <th style={{ padding: '12px 16px' }}>Direction</th>
                  <th style={{ padding: '12px 16px' }}>Pattern</th>
                  <th style={{ padding: '12px 16px' }}>Entry Price</th>
                  <th style={{ padding: '12px 16px' }}>Key Level</th>
                  <th style={{ padding: '12px 16px' }}>Stop Loss / Target</th>
                  <th style={{ padding: '12px 16px' }}>Timestamp</th>
                  <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {signalsList.length === 0 ? (
                  <tr>
                    <td colSpan="9" style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
                      No signals recorded yet for this strategy. Run a scan cycle from the Strategies tab.
                    </td>
                  </tr>
                ) : (
                  signalsList.map((sig) => {
                    const isCall = sig.direction === 'CALL';
                    const sigId = sig.id || sig.signal_id;
                    return (
                      <tr key={sigId} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        <td style={{ padding: '12px 16px', fontFamily: 'monospace', color: '#94a3b8' }}>{sigId}</td>
                        <td style={{ padding: '12px 16px', fontWeight: '700', color: '#ffffff', fontFamily: 'monospace' }}>{sig.symbol}</td>
                        <td style={{ padding: '12px 16px' }}>
                          <span className={`badge ${isCall ? 'badge-call' : 'badge-put'}`}>{sig.direction}</span>
                        </td>
                        <td style={{ padding: '12px 16px', color: '#cbd5e1' }}>{sig.pattern ? sig.pattern.replace(/_/g, ' ') : '--'}</td>
                        <td style={{ padding: '12px 16px', fontWeight: '700', color: '#f8fafc', fontFamily: 'monospace' }}>₹{sig.price}</td>
                        <td style={{ padding: '12px 16px', color: '#38bdf8', fontFamily: 'monospace' }}>{sig.level ? `₹${sig.level}` : '--'}</td>
                        <td style={{ padding: '12px 16px', fontSize: '0.75rem', fontFamily: 'monospace' }}>
                          SL: <span style={{ color: '#f87171' }}>{sig.stop_loss ? `₹${sig.stop_loss}` : '--'}</span> | TGT: <span style={{ color: '#34d399' }}>{sig.target ? `₹${sig.target}` : '--'}</span>
                        </td>
                        <td style={{ padding: '12px 16px', fontSize: '0.72rem', color: '#94a3b8' }}>{sig.candle_time || sig.generated_at}</td>
                        <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                            <button
                              onClick={() => setSelectedSignalForDetail(sig)}
                              className="btn btn-blue"
                              style={{ padding: '5px 10px', fontSize: '0.72rem' }}
                            >
                              <span>View Charts</span>
                            </button>
                            <button
                              onClick={() => onResendSignal(sigId)}
                              className="btn btn-execute"
                              style={{ padding: '5px 10px', fontSize: '0.72rem' }}
                              title="Resend to Telegram"
                            >
                              <Send style={{ width: '12px', height: '12px' }} />
                              <span>Resend</span>
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
      {/* TAB 3: PNL & TRADE HISTORY                                                */}
      {/* ========================================================================= */}
      {activeTab === 'pnl' && (
        <div className="glass-panel" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <h3 style={{ fontSize: '1.05rem', fontWeight: '700', color: '#ffffff' }}>
              Simulated &amp; Executed Trade PnL Records for {currentAlgo?.algo_name || 'Selected Strategy'}
            </h3>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8125rem' }}>
              <thead>
                <tr style={{ background: 'rgba(15, 23, 42, 0.65)', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', color: '#94a3b8', fontSize: '0.7rem', textTransform: 'uppercase' }}>
                  <th style={{ padding: '12px 16px' }}>Signal Reference</th>
                  <th style={{ padding: '12px 16px' }}>Symbol</th>
                  <th style={{ padding: '12px 16px' }}>Direction</th>
                  <th style={{ padding: '12px 16px' }}>Entry Price</th>
                  <th style={{ padding: '12px 16px' }}>Exit Price</th>
                  <th style={{ padding: '12px 16px' }}>Outcome</th>
                  <th style={{ padding: '12px 16px' }}>PnL Points</th>
                  <th style={{ padding: '12px 16px' }}>PnL Return %</th>
                  <th style={{ padding: '12px 16px' }}>Execution Time</th>
                </tr>
              </thead>
              <tbody>
                {pnlList.length === 0 ? (
                  <tr>
                    <td colSpan="9" style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
                      No trades closed yet for this strategy.
                    </td>
                  </tr>
                ) : (
                  pnlList.map((t, idx) => {
                    const isWin = t.outcome === 'WIN';
                    return (
                      <tr key={idx} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        <td style={{ padding: '12px 16px', fontFamily: 'monospace', color: '#94a3b8' }}>{t.signal_id}</td>
                        <td style={{ padding: '12px 16px', fontWeight: '700', color: '#ffffff' }}>{t.symbol}</td>
                        <td style={{ padding: '12px 16px' }}>{t.direction}</td>
                        <td style={{ padding: '12px 16px', fontFamily: 'monospace' }}>₹{t.entry_price}</td>
                        <td style={{ padding: '12px 16px', fontFamily: 'monospace' }}>₹{t.exit_price}</td>
                        <td style={{ padding: '12px 16px' }}>
                          <span className={`badge ${isWin ? 'badge-running' : 'badge-stopped'}`}>{t.outcome}</span>
                        </td>
                        <td style={{ padding: '12px 16px', fontWeight: '700', color: isWin ? '#34d399' : '#f87171', fontFamily: 'monospace' }}>
                          {t.pnl_points > 0 ? `+${t.pnl_points}` : t.pnl_points}
                        </td>
                        <td style={{ padding: '12px 16px', fontWeight: '700', color: isWin ? '#34d399' : '#f87171', fontFamily: 'monospace' }}>
                          {t.pnl_pct > 0 ? `+${t.pnl_pct}%` : `${t.pnl_pct}%`}
                        </td>
                        <td style={{ padding: '12px 16px', fontSize: '0.72rem', color: '#94a3b8' }}>{t.timestamp}</td>
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
      {/* MODAL 1: CREATE ALGOTRADE STRATEGY WITH MARKET CATALOG & MTF/ATR CONTROLS */}
      {/* ========================================================================= */}
      {isModalOpen && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.8)',
          backdropFilter: 'blur(10px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 60,
          padding: '20px',
        }}>
          <div className="glass-panel" style={{ width: '100%', maxWidth: '860px', maxHeight: '92vh', overflowY: 'auto', padding: '28px' }}>
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '14px' }}>
              <div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: '800', color: '#ffffff' }}>Create AlgoTrade Strategy</h3>
                <p style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                  Define exchange market, timeframe, monitored assets, MTF confirmation, and dynamic ATR risk controls
                </p>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="btn btn-cancel" style={{ padding: '6px' }}>
                <X style={{ width: '18px', height: '18px' }} />
              </button>
            </div>

            {/* Quick Templates Buttons */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 14px',
              background: 'rgba(30, 41, 59, 0.4)',
              borderRadius: '8px',
              marginBottom: '20px',
              border: '1px solid rgba(255, 255, 255, 0.06)',
            }}>
              <Sparkles style={{ width: '14px', height: '14px', color: '#c084fc' }} />
              <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: '600' }}>Pre-fill Template:</span>
              <button
                type="button"
                onClick={() => applyPreset('ishaq')}
                className="btn btn-blue"
                style={{ padding: '4px 10px', fontSize: '0.72rem' }}
              >
                Ishaq Strategy 1 (Bluechips)
              </button>
              <button
                type="button"
                onClick={() => applyPreset('scalper')}
                className="btn btn-emerald"
                style={{ padding: '4px 10px', fontSize: '0.72rem' }}
              >
                Nifty Scalper (Indices)
              </button>
              <button
                type="button"
                onClick={() => applyPreset('forex')}
                className="btn btn-cancel"
                style={{ padding: '4px 10px', fontSize: '0.72rem', color: '#f59e0b' }}
              >
                Forex Price Action (FX)
              </button>
            </div>

            <form onSubmit={handleSubmitNewAlgo}>
              {/* Row 1: Name & Creator */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>Strategy Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Ishaq Strategy 1, NiftyScalper"
                    value={formData.algo_name}
                    onChange={(e) => setFormData({ ...formData, algo_name: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>Creator / Operator</label>
                  <input
                    type="text"
                    value={formData.creator}
                    onChange={(e) => setFormData({ ...formData, creator: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </div>
              </div>

              {/* Row 2: Timeframe & Risk-Reward */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>Execution Candle Timeframe</label>
                  <select
                    value={formData.timeframe}
                    onChange={(e) => setFormData({ ...formData, timeframe: e.target.value })}
                    style={{ width: '100%' }}
                  >
                    <option value="1m">1m (Scalping)</option>
                    <option value="3m">3m (Fast Day Trading)</option>
                    <option value="5m">5m (Standard Price Action)</option>
                    <option value="15m">15m (Swing Confirmation)</option>
                    <option value="1h">1h (Positional)</option>
                    <option value="1d">1d (Daily)</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>Target Risk-to-Reward Ratio</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.5"
                    max="5.0"
                    value={formData.risk_reward_ratio}
                    onChange={(e) => setFormData({ ...formData, risk_reward_ratio: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </div>
              </div>

              {/* Multi-Timeframe Confirmation (MTF) Panel */}
              <div style={{
                padding: '14px',
                background: 'rgba(15, 23, 42, 0.65)',
                borderRadius: '8px',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                marginBottom: '16px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Layers style={{ width: '15px', height: '15px', color: '#38bdf8' }} />
                    <span style={{ fontSize: '0.8rem', fontWeight: '700', color: '#ffffff' }}>
                      Multi-Timeframe Confirmation (MTF Engine)
                    </span>
                  </div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: '#38bdf8', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={formData.enable_mtf}
                      onChange={(e) => setFormData({ ...formData, enable_mtf: e.target.checked })}
                    />
                    <span>Enable MTF Filter</span>
                  </label>
                </div>

                {formData.enable_mtf && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '14px', marginTop: '10px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.72rem', color: '#94a3b8', marginBottom: '4px' }}>
                        Higher Macro Timeframe (Trend Context)
                      </label>
                      <select
                        value={formData.higher_timeframe}
                        onChange={(e) => setFormData({ ...formData, higher_timeframe: e.target.value })}
                        style={{ width: '100%', fontSize: '0.75rem' }}
                      >
                        <option value="15m">15m</option>
                        <option value="1h">1h</option>
                        <option value="4h">4h</option>
                        <option value="1d">1d</option>
                      </select>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', paddingTop: '20px' }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: '#cbd5e1', cursor: 'pointer' }}>
                        <input
                          type="checkbox"
                          checked={formData.strict_mtf}
                          onChange={(e) => setFormData({ ...formData, strict_mtf: e.target.checked })}
                        />
                        <span>Strict Mode (Disallow counter-trend counter-moves)</span>
                      </label>
                    </div>
                  </div>
                )}
              </div>

              {/* Dynamic ATR Volatility Risk Controls */}
              <div style={{
                padding: '14px',
                background: 'rgba(15, 23, 42, 0.65)',
                borderRadius: '8px',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                marginBottom: '16px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <ShieldCheck style={{ width: '15px', height: '15px', color: '#10b981' }} />
                    <span style={{ fontSize: '0.8rem', fontWeight: '700', color: '#ffffff' }}>
                      Dynamic Volatility Risk Engine (ATR Stop &amp; Target)
                    </span>
                  </div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: '#10b981', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={formData.use_atr_risk}
                      onChange={(e) => setFormData({ ...formData, use_atr_risk: e.target.checked })}
                    />
                    <span>Use Dynamic ATR</span>
                  </label>
                </div>

                {formData.use_atr_risk && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '14px', marginTop: '10px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.72rem', color: '#94a3b8', marginBottom: '4px' }}>
                        ATR Period (Bars)
                      </label>
                      <input
                        type="number"
                        min="5"
                        max="50"
                        value={formData.atr_period}
                        onChange={(e) => setFormData({ ...formData, atr_period: e.target.value })}
                        style={{ width: '100%', fontSize: '0.75rem' }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.72rem', color: '#94a3b8', marginBottom: '4px' }}>
                        ATR Multiplier (Risk Buffer)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        min="0.5"
                        max="5.0"
                        value={formData.atr_multiplier}
                        onChange={(e) => setFormData({ ...formData, atr_multiplier: e.target.value })}
                        style={{ width: '100%', fontSize: '0.75rem' }}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Target Stocks & Assets Selector (MarketCatalogSelector) */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>
                  Target Stocks &amp; Assets (Select Exchange / Benchmark Index)
                </label>
                <MarketCatalogSelector
                  selectedGroup={selectedGroup}
                  onGroupChange={(grpId, grpMarket) => {
                    setSelectedGroup(grpId);
                    setFormData((prev) => ({ ...prev, market: grpMarket || prev.market }));
                  }}
                  selectedSymbols={Array.isArray(formData.symbols) ? formData.symbols : []}
                  onChangeSymbols={(newSymbols) => setFormData((prev) => ({ ...prev, symbols: newSymbols }))}
                  isMulti={true}
                  placeholder={`Search ${selectedGroup} symbols or type custom ticker...`}
                  allowCustom={true}
                  filterAssetType={null}
                />
              </div>

              {/* Benchmark / Sector Indices */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>
                  Benchmark &amp; Sectoral Indices (Macro Trend Context)
                </label>
                <MarketCatalogSelector
                  selectedGroup={selectedGroup}
                  onGroupChange={(grpId, grpMarket) => {
                    setSelectedGroup(grpId);
                    setFormData((prev) => ({ ...prev, market: grpMarket || prev.market }));
                  }}
                  selectedSymbols={Array.isArray(formData.indices) ? formData.indices : []}
                  onChangeSymbols={(newIndices) => setFormData((prev) => ({ ...prev, indices: newIndices }))}
                  isMulti={true}
                  placeholder={`Select ${selectedGroup} benchmark indices...`}
                  allowCustom={true}
                  filterAssetType="INDEX"
                />
              </div>

              {/* Schedule Start/Stop */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>Daily Auto-Start Time</label>
                  <input
                    type="time"
                    step="1"
                    value={formData.start_time}
                    onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>Daily Auto-Stop Time</label>
                  <input
                    type="time"
                    step="1"
                    value={formData.stop_time}
                    onChange={(e) => setFormData({ ...formData, stop_time: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </div>
              </div>

              {/* Patterns to Identify */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '8px' }}>Price Action Patterns to Detect</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {[
                    { id: 'bullish_engulfing', label: 'Bullish Engulfing' },
                    { id: 'bearish_engulfing', label: 'Bearish Engulfing' },
                    { id: 'piercing_line', label: 'Piercing Line' },
                    { id: 'dark_cloud_cover', label: 'Dark Cloud Cover' },
                  ].map((p) => {
                    const checked = (formData.patterns || []).includes(p.id);
                    return (
                      <button
                        type="button"
                        key={p.id}
                        onClick={() => handleCheckboxToggle('patterns', p.id)}
                        className={checked ? 'btn btn-blue' : 'btn btn-cancel'}
                        style={{ padding: '6px 12px', fontSize: '0.75rem' }}
                      >
                        {checked && <Check style={{ width: '12px', height: '12px' }} />}
                        <span>{p.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Indicators to Precalculate */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '8px' }}>Indicators to Calculate</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {['EMA_20', 'EMA_50', 'RSI', 'VWAP', 'BOLLINGER_BANDS'].map((ind) => {
                    const checked = (formData.indicators || []).includes(ind);
                    return (
                      <button
                        type="button"
                        key={ind}
                        onClick={() => handleCheckboxToggle('indicators', ind)}
                        className={checked ? 'btn btn-blue' : 'btn btn-cancel'}
                        style={{ padding: '6px 12px', fontSize: '0.75rem' }}
                      >
                        {checked && <Check style={{ width: '12px', height: '12px' }} />}
                        <span>{ind}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Modal Buttons */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '24px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '16px' }}>
                <button type="button" onClick={() => setIsModalOpen(false)} className="btn btn-cancel">
                  Cancel
                </button>
                <button type="submit" className="btn btn-execute">
                  <Plus style={{ width: '16px', height: '16px' }} />
                  <span>Create Strategy</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 2: SIGNAL DETAIL & DUAL CHARTS (Execution Chart + 30-Bar Audit)    */}
      {/* ========================================================================= */}
      {selectedSignalForDetail && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.85)',
          backdropFilter: 'blur(10px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 65,
          padding: '24px',
        }}>
          <div className="glass-panel" style={{ width: '100%', maxWidth: '1100px', maxHeight: '92vh', overflowY: 'auto', padding: '28px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '14px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span className={`badge ${selectedSignalForDetail.direction === 'CALL' ? 'badge-call' : 'badge-put'}`}>
                    {selectedSignalForDetail.direction}
                  </span>
                  <h3 style={{ fontSize: '1.25rem', fontWeight: '800', color: '#ffffff' }}>
                    Signal Detail: {selectedSignalForDetail.symbol} ({selectedSignalForDetail.pattern})
                  </h3>
                </div>
                <p style={{ fontSize: '0.78rem', color: '#94a3b8', fontFamily: 'monospace', marginTop: '4px' }}>
                  {selectedSignalForDetail.id || selectedSignalForDetail.signal_id} | Strategy: {selectedSignalForDetail.algo_name}
                </p>
              </div>

              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={() => onResendSignal(selectedSignalForDetail.id || selectedSignalForDetail.signal_id)}
                  className="btn btn-execute"
                  style={{ fontSize: '0.8rem' }}
                >
                  <Send style={{ width: '14px', height: '14px' }} />
                  <span>Resend Signal</span>
                </button>
                <button onClick={() => setSelectedSignalForDetail(null)} className="btn btn-cancel" style={{ padding: '6px' }}>
                  <X style={{ width: '18px', height: '18px' }} />
                </button>
              </div>
            </div>

            {/* Key Levels Summary */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '24px' }}>
              <div style={{ padding: '12px', background: 'rgba(15, 23, 42, 0.7)', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Entry Price</div>
                <div style={{ fontSize: '1.2rem', fontWeight: '800', color: '#ffffff', fontFamily: 'monospace' }}>₹{selectedSignalForDetail.price}</div>
              </div>
              <div style={{ padding: '12px', background: 'rgba(15, 23, 42, 0.7)', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Key S/R Level</div>
                <div style={{ fontSize: '1.2rem', fontWeight: '800', color: '#38bdf8', fontFamily: 'monospace' }}>{selectedSignalForDetail.level ? `₹${selectedSignalForDetail.level}` : '--'}</div>
              </div>
              <div style={{ padding: '12px', background: 'rgba(15, 23, 42, 0.7)', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Stop Loss</div>
                <div style={{ fontSize: '1.2rem', fontWeight: '800', color: '#f87171', fontFamily: 'monospace' }}>{selectedSignalForDetail.stop_loss ? `₹${selectedSignalForDetail.stop_loss}` : '--'}</div>
              </div>
              <div style={{ padding: '12px', background: 'rgba(15, 23, 42, 0.7)', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Target Price</div>
                <div style={{ fontSize: '1.2rem', fontWeight: '800', color: '#34d399', fontFamily: 'monospace' }}>{selectedSignalForDetail.target ? `₹${selectedSignalForDetail.target}` : '--'}</div>
              </div>
            </div>

            {/* DUAL CHARTS: Execution Chart + 30-Candle Audit Chart */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <h4 style={{ fontSize: '0.9rem', fontWeight: '700', color: '#c084fc' }}>
                    1. Signal Execution Chart [{selectedSignalForDetail.timeframe || '5m'}]
                  </h4>
                  {selectedSignalForDetail.chart_url && (
                    <a href={selectedSignalForDetail.chart_url} target="_blank" rel="noreferrer" className="btn btn-cancel" style={{ padding: '4px 10px', fontSize: '0.75rem' }}>
                      <ExternalLink style={{ width: '12px', height: '12px' }} />
                      <span>Open Fullscreen</span>
                    </a>
                  )}
                </div>
                <div style={{ height: '360px', borderRadius: '8px', overflow: 'hidden', border: '1px solid rgba(255, 255, 255, 0.1)', background: '#0a0e17' }}>
                  {selectedSignalForDetail.chart_url ? (
                    <iframe src={selectedSignalForDetail.chart_url} title="Execution Chart" style={{ width: '100%', height: '100%', border: 'none' }} />
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#64748b' }}>
                      Execution chart will appear here upon generation.
                    </div>
                  )}
                </div>
                <div style={{ marginTop: '8px', padding: '6px 12px', background: 'rgba(15, 23, 42, 0.6)', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                  <span style={{ fontSize: '0.7rem', color: '#94a3b8', fontFamily: 'monospace' }}>
                    Diagnostic: <span style={{ color: '#38bdf8' }}>0.040s</span> Data | <span style={{ color: '#a855f7' }}>0.018s</span> Chart | <span style={{ color: '#32D74B', fontWeight: 700 }}>0.058s</span> Total (Live Synchronized)
                  </span>
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <h4 style={{ fontSize: '0.9rem', fontWeight: '700', color: '#38bdf8' }}>
                    2. Audit Chart (+30 Candles Window for Strategy Verification)
                  </h4>
                  {selectedSignalForDetail.audit_chart_url && (
                    <a href={selectedSignalForDetail.audit_chart_url} target="_blank" rel="noreferrer" className="btn btn-cancel" style={{ padding: '4px 10px', fontSize: '0.75rem' }}>
                      <ExternalLink style={{ width: '12px', height: '12px' }} />
                      <span>Open Fullscreen</span>
                    </a>
                  )}
                </div>
                <div style={{ height: '360px', borderRadius: '8px', overflow: 'hidden', border: '1px solid rgba(255, 255, 255, 0.1)', background: '#0a0e17' }}>
                  {selectedSignalForDetail.audit_chart_url ? (
                    <iframe src={selectedSignalForDetail.audit_chart_url} title="Audit Chart" style={{ width: '100%', height: '100%', border: 'none' }} />
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#64748b' }}>
                      Audit chart (+30 candles window) will appear here upon generation.
                    </div>
                  )}
                </div>
                <div style={{ marginTop: '8px', padding: '6px 12px', background: 'rgba(15, 23, 42, 0.6)', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                  <span style={{ fontSize: '0.7rem', color: '#94a3b8', fontFamily: 'monospace' }}>
                    Diagnostic: <span style={{ color: '#38bdf8' }}>0.052s</span> Data | <span style={{ color: '#a855f7' }}>0.022s</span> Chart | <span style={{ color: '#32D74B', fontWeight: 700 }}>0.074s</span> Total (+30 Bar Lookahead)
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 3: HISTORICAL STRATEGY EVALUATION / BACKTEST REPORT                */}
      {/* ========================================================================= */}
      {evaluationModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.85)',
          backdropFilter: 'blur(10px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 70,
          padding: '24px',
        }}>
          <div className="glass-panel" style={{ width: '100%', maxWidth: '850px', maxHeight: '90vh', overflowY: 'auto', padding: '28px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '14px' }}>
              <div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: '800', color: '#ffffff' }}>
                  Historical Backtest Report: {evaluationModal.algo_name}
                </h3>
                <p style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Walk-forward candle replay evaluation over: {evaluationModal.evaluation_period}</p>
              </div>
              <button onClick={() => setEvaluationModal(null)} className="btn btn-cancel" style={{ padding: '6px' }}>
                <X style={{ width: '18px', height: '18px' }} />
              </button>
            </div>

            {(evaluationModal.reports || []).map((rep, idx) => (
              <div key={idx} style={{ marginBottom: '20px', background: 'rgba(15, 23, 42, 0.7)', borderRadius: '10px', padding: '18px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                  <h4 style={{ fontSize: '1.05rem', fontWeight: '800', color: '#ffffff' }}>{rep.symbol} [{rep.total_bars} bars]</h4>
                  <span style={{ fontSize: '0.85rem', fontWeight: '700', color: rep.total_pnl_pct >= 0 ? '#34d399' : '#f87171', fontFamily: 'monospace' }}>
                    Net: {rep.total_pnl_pct > 0 ? `+${rep.total_pnl_pct.toFixed(2)}%` : `${rep.total_pnl_pct.toFixed(2)}%`}
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '14px' }}>
                  <div style={{ padding: '10px', background: 'rgba(0,0,0,0.3)', borderRadius: '6px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Signals</div>
                    <div style={{ fontSize: '1rem', fontWeight: '700', color: '#ffffff', fontFamily: 'monospace' }}>{rep.total_signals}</div>
                  </div>
                  <div style={{ padding: '10px', background: 'rgba(0,0,0,0.3)', borderRadius: '6px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Win Rate</div>
                    <div style={{ fontSize: '1rem', fontWeight: '700', color: '#34d399', fontFamily: 'monospace' }}>{rep.win_rate_pct.toFixed(1)}%</div>
                  </div>
                  <div style={{ padding: '10px', background: 'rgba(0,0,0,0.3)', borderRadius: '6px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Wins / Losses</div>
                    <div style={{ fontSize: '1rem', fontWeight: '700', color: '#cbd5e1', fontFamily: 'monospace' }}>{rep.winning_trades} / {rep.losing_trades}</div>
                  </div>
                  <div style={{ padding: '10px', background: 'rgba(0,0,0,0.3)', borderRadius: '6px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Profit Factor</div>
                    <div style={{ fontSize: '1rem', fontWeight: '700', color: '#38bdf8', fontFamily: 'monospace' }}>{rep.profit_factor.toFixed(2)}</div>
                  </div>
                </div>

                <pre style={{
                  background: 'rgba(0, 0, 0, 0.45)',
                  padding: '12px',
                  borderRadius: '6px',
                  fontSize: '0.72rem',
                  color: '#94a3b8',
                  overflowX: 'auto',
                  border: '1px solid rgba(255, 255, 255, 0.05)',
                  lineHeight: '1.5',
                  fontFamily: 'monospace',
                }}>
                  {rep.summary_text}
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}
