import React, { useState, useEffect } from 'react';
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
  DollarSign
} from 'lucide-react';

export default function AlgoTradeView({
  algos,
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
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedAlgo, setSelectedAlgo] = useState(algos[0] || null);
  const [activeTab, setActiveTab] = useState(initialTab); // 'strategies', 'signals', 'pnl'
  const [selectedSignalForDetail, setSelectedSignalForDetail] = useState(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [evaluationModal, setEvaluationModal] = useState(null);

  useEffect(() => {
    if (initialTab) {
      setActiveTab(initialTab);
    }
  }, [initialTab]);

  // New Algo Form State
  const [formData, setFormData] = useState({
    algo_name: '',
    market: 'INDIAN_EQUITY',
    timeframe: '5m',
    symbols: 'RELIANCE, TCS',
    indices: 'NIFTY 50, NIFTY BANK',
    patterns: ['bullish_engulfing', 'bearish_engulfing', 'dark_cloud_cover', 'piercing_line'],
    indicators: ['EMA_20', 'EMA_50', 'RSI', 'VWAP'],
    extra_data: ['candles', 'volume', 'vix', 'index_movement'],
    start_date: '',
    end_date: '',
    start_time: '09:15:00',
    stop_time: '15:30:00',
    chart_enabled: true,
    audit_enabled: true,
    risk_reward_ratio: 1.5,
    creator: 'Ishaq',
    description: '',
  });

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

    const payload = {
      ...formData,
      symbols: formData.symbols.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean),
      indices: formData.indices.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean),
      risk_reward_ratio: parseFloat(formData.risk_reward_ratio) || 1.5,
    };

    await onCreateAlgo(payload);
    setIsModalOpen(false);
    setFormData({
      algo_name: '',
      market: 'INDIAN_EQUITY',
      timeframe: '5m',
      symbols: 'RELIANCE, TCS',
      indices: 'NIFTY 50, NIFTY BANK',
      patterns: ['bullish_engulfing', 'bearish_engulfing', 'dark_cloud_cover', 'piercing_line'],
      indicators: ['EMA_20', 'EMA_50', 'RSI', 'VWAP'],
      extra_data: ['candles', 'volume', 'vix', 'index_movement'],
      start_date: '',
      end_date: '',
      start_time: '09:15:00',
      stop_time: '15:30:00',
      chart_enabled: true,
      audit_enabled: true,
      risk_reward_ratio: 1.5,
      creator: 'Ishaq',
      description: '',
    });
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

  // Currently focused algo signals and PnL
  const currentAlgo = algos.find((a) => a.algo_id === (selectedAlgo?.algo_id || algos[0]?.algo_id)) || algos[0];
  const signalsList = currentAlgo?.signals_history || currentAlgo?.signals || [];
  const pnlList = currentAlgo?.pnl_history || currentAlgo?.pnl_trades || [];

  return (
    <div style={{ padding: '28px', maxWidth: '1440px', margin: '0 auto' }}>
      {/* Module Sub-Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: '800', color: '#ffffff' }}>AlgoTrade Strategies</h2>
          <p style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Create, execute, schedule, backtest, and audit custom trading models</p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          {/* Create Button (Popping Purple Execution Style) */}
          <button onClick={() => setIsModalOpen(true)} className="btn btn-execute">
            <Plus style={{ width: '16px', height: '16px' }} />
            <span>Create AlgoTrade</span>
          </button>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', marginBottom: '24px', paddingBottom: '8px' }}>
        <button
          onClick={() => setActiveTab('strategies')}
          className={activeTab === 'strategies' ? 'btn btn-blue' : 'btn btn-cancel'}
          style={{ padding: '8px 16px', fontSize: '0.82rem' }}
        >
          Active Strategies ({algos.length})
        </button>
        <button
          onClick={() => setActiveTab('signals')}
          className={activeTab === 'signals' ? 'btn btn-blue' : 'btn btn-cancel'}
          style={{ padding: '8px 16px', fontSize: '0.82rem' }}
        >
          Signal Feeds ({signalsList.length})
        </button>
        <button
          onClick={() => setActiveTab('pnl')}
          className={activeTab === 'pnl' ? 'btn btn-blue' : 'btn btn-cancel'}
          style={{ padding: '8px 16px', fontSize: '0.82rem' }}
        >
          PnL &amp; Trade History ({pnlList.length})
        </button>
      </div>

      {/* TAB 1: STRATEGIES LIST */}
      {activeTab === 'strategies' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: '20px' }}>
          {algos.map((algo) => {
            const isRunning = algo.status === 'RUNNING';
            return (
              <div key={algo.algo_id} className="glass-panel" style={{ padding: '22px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  {/* Card Header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                    <div>
                      <h3 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#ffffff' }}>{algo.algo_name}</h3>
                      <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontFamily: 'monospace' }}>{algo.algo_id}</span>
                    </div>
                    <span className={`badge badge-${algo.status.toLowerCase()}`}>
                      {algo.status}
                    </span>
                  </div>

                  <p style={{ fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '16px', minHeight: '38px' }}>
                    {algo.description || 'Configured with PDF Price Action rules, level rejection confirmation, and real-time visualization.'}
                  </p>

                  {/* Attributes Badges */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '16px' }}>
                    <span style={{ fontSize: '0.72rem', padding: '3px 8px', borderRadius: '6px', background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', border: '1px solid rgba(168, 85, 247, 0.3)' }}>
                      {algo.market}
                    </span>
                    <span style={{ fontSize: '0.72rem', padding: '3px 8px', borderRadius: '6px', background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
                      Timeframe: {algo.timeframe}
                    </span>
                    {algo.start_time && (
                      <span style={{ fontSize: '0.72rem', padding: '3px 8px', borderRadius: '6px', background: 'rgba(51, 65, 85, 0.5)', color: '#cbd5e1' }}>
                        ⏰ {algo.start_time} - {algo.stop_time}
                      </span>
                    )}
                    <span style={{ fontSize: '0.72rem', padding: '3px 8px', borderRadius: '6px', background: 'rgba(51, 65, 85, 0.5)', color: '#cbd5e1' }}>
                      👤 {algo.creator || 'Admin'}
                    </span>
                  </div>

                  {/* Monitored Assets list */}
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '16px' }}>
                    <span style={{ fontWeight: '600', color: '#cbd5e1' }}>Assets: </span>
                    {(algo.symbols || []).join(', ')}
                  </div>

                  {/* Live Stats Row */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', padding: '12px', background: 'rgba(15, 23, 42, 0.8)', borderRadius: '10px', marginBottom: '18px' }}>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '0.68rem', color: '#94a3b8', textTransform: 'uppercase' }}>Cycles</div>
                      <div style={{ fontSize: '1rem', fontWeight: '700', color: '#ffffff' }}>{algo.cycle_count || 0}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '0.68rem', color: '#94a3b8', textTransform: 'uppercase' }}>Signals</div>
                      <div style={{ fontSize: '1rem', fontWeight: '700', color: '#38bdf8' }}>{algo.signals_count || 0}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '0.68rem', color: '#94a3b8', textTransform: 'uppercase' }}>Win Rate</div>
                      <div style={{ fontSize: '1rem', fontWeight: '700', color: '#34d399' }}>{algo.win_rate_pct || 0}%</div>
                    </div>
                  </div>
                </div>

                {/* Actions Toolbar (Popping Buttons) */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '16px' }}>
                  {/* Execute/Start (Purple) */}
                  <button
                    onClick={() => onStartAlgo(algo.algo_id)}
                    className="btn btn-execute"
                    style={{ flex: '1', fontSize: '0.78rem' }}
                  >
                    <Play style={{ width: '13px', height: '13px', fill: '#ffffff' }} />
                    <span>Execute</span>
                  </button>

                  {/* Stop (Red) */}
                  <button
                    onClick={() => onStopAlgo(algo.algo_id)}
                    className="btn btn-stop"
                    style={{ padding: '8px 12px', fontSize: '0.78rem' }}
                    title="Stop AlgoTrade"
                  >
                    <Square style={{ width: '13px', height: '13px', fill: '#ffffff' }} />
                  </button>

                  {/* Pause (Amber/Grey) */}
                  <button
                    onClick={() => onPauseAlgo(algo.algo_id)}
                    className="btn btn-cancel"
                    style={{ padding: '8px 12px', fontSize: '0.78rem' }}
                    title="Pause AlgoTrade"
                  >
                    <Pause style={{ width: '13px', height: '13px' }} />
                  </button>

                  {/* Copy (Blue) */}
                  <button
                    onClick={() => onCopyAlgo(algo.algo_id)}
                    className="btn btn-blue"
                    style={{ padding: '8px 12px', fontSize: '0.78rem' }}
                    title="Duplicate Strategy"
                  >
                    <Copy style={{ width: '13px', height: '13px' }} />
                  </button>

                  {/* Historical Backtest / Evaluate */}
                  <button
                    onClick={() => handleRunEvaluation(algo.algo_id)}
                    disabled={isEvaluating}
                    className="btn btn-cancel"
                    style={{ padding: '8px 12px', fontSize: '0.78rem', color: '#c084fc' }}
                    title="Backtest / Historical Evaluation on Past Data"
                  >
                    <Clock style={{ width: '13px', height: '13px' }} />
                  </button>

                  {/* Delete (Grey/Trash) */}
                  <button
                    onClick={() => {
                      if (confirm(`Are you sure you want to delete '${algo.algo_name}'?`)) {
                        onDeleteAlgo(algo.algo_id);
                      }
                    }}
                    className="btn btn-cancel"
                    style={{ padding: '8px 12px', fontSize: '0.78rem', color: '#f87171' }}
                    title="Delete Strategy"
                  >
                    <Trash2 style={{ width: '13px', height: '13px' }} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* TAB 2: SIGNALS LIST & DETAIL */}
      {activeTab === 'signals' && (
        <div className="glass-panel" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '700', color: '#ffffff' }}>
              Actionable Signals ({signalsList.length}) for {currentAlgo?.algo_name}
            </h3>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Each signal includes Execution Chart + 30-Candle Audit Chart</span>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ background: 'rgba(15, 23, 42, 0.6)', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                  <th style={{ padding: '12px 16px' }}>Signal ID</th>
                  <th style={{ padding: '12px 16px' }}>Symbol</th>
                  <th style={{ padding: '12px 16px' }}>Direction</th>
                  <th style={{ padding: '12px 16px' }}>Pattern</th>
                  <th style={{ padding: '12px 16px' }}>Entry Price</th>
                  <th style={{ padding: '12px 16px' }}>Stop Loss / Target</th>
                  <th style={{ padding: '12px 16px' }}>Timestamp</th>
                  <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {signalsList.length === 0 ? (
                  <tr>
                    <td colSpan="8" style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
                      No signals fired yet in this cycle. Click "Execute" on an active strategy to scan monitored candles.
                    </td>
                  </tr>
                ) : (
                  signalsList.map((sig) => {
                    const isCall = sig.direction === 'CALL';
                    return (
                      <tr key={sig.id || sig.signal_id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        <td style={{ padding: '12px 16px', fontFamily: 'monospace', color: '#94a3b8' }}>{sig.id || sig.signal_id}</td>
                        <td style={{ padding: '12px 16px', fontWeight: '700', color: '#ffffff' }}>{sig.symbol}</td>
                        <td style={{ padding: '12px 16px' }}>
                          <span className={`badge ${isCall ? 'badge-call' : 'badge-put'}`}>{sig.direction}</span>
                        </td>
                        <td style={{ padding: '12px 16px', color: '#cbd5e1' }}>{sig.pattern}</td>
                        <td style={{ padding: '12px 16px', fontWeight: '600', color: '#f8fafc' }}>{sig.price}</td>
                        <td style={{ padding: '12px 16px', fontSize: '0.78rem', color: '#94a3b8' }}>
                          SL: <span style={{ color: '#f87171' }}>{sig.stop_loss || '--'}</span> | TGT: <span style={{ color: '#34d399' }}>{sig.target || '--'}</span>
                        </td>
                        <td style={{ padding: '12px 16px', fontSize: '0.75rem', color: '#94a3b8' }}>{sig.candle_time || sig.generated_at}</td>
                        <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                            {/* View Charts & Detail Modal */}
                            <button
                              onClick={() => setSelectedSignalForDetail(sig)}
                              className="btn btn-blue"
                              style={{ padding: '6px 12px', fontSize: '0.75rem' }}
                            >
                              <span>View Charts</span>
                            </button>
                            {/* Resend Signal Button */}
                            <button
                              onClick={() => onResendSignal(sig.id || sig.signal_id)}
                              className="btn btn-execute"
                              style={{ padding: '6px 12px', fontSize: '0.75rem' }}
                              title="Resend to Telegram / Endpoints"
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

      {/* TAB 3: PNL & TRADE HISTORY */}
      {activeTab === 'pnl' && (
        <div className="glass-panel" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '700', color: '#ffffff' }}>
              Simulated &amp; Executed Trade PnL Records for {currentAlgo?.algo_name}
            </h3>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ background: 'rgba(15, 23, 42, 0.6)', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase' }}>
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
                        <td style={{ padding: '12px 16px' }}>{t.entry_price}</td>
                        <td style={{ padding: '12px 16px' }}>{t.exit_price}</td>
                        <td style={{ padding: '12px 16px' }}>
                          <span className={`badge ${isWin ? 'badge-running' : 'badge-stopped'}`}>{t.outcome}</span>
                        </td>
                        <td style={{ padding: '12px 16px', fontWeight: '600', color: isWin ? '#34d399' : '#f87171' }}>
                          {t.pnl_points > 0 ? `+${t.pnl_points}` : t.pnl_points}
                        </td>
                        <td style={{ padding: '12px 16px', fontWeight: '700', color: isWin ? '#34d399' : '#f87171' }}>
                          {t.pnl_pct > 0 ? `+${t.pnl_pct}%` : `${t.pnl_pct}%`}
                        </td>
                        <td style={{ padding: '12px 16px', fontSize: '0.75rem', color: '#94a3b8' }}>{t.timestamp}</td>
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
      {/* MODAL 1: CREATE ALGOTRADE STRATEGY                                        */}
      {/* ========================================================================= */}
      {isModalOpen && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 50,
          padding: '20px',
        }}>
          <div className="glass-panel" style={{ width: '100%', maxWidth: '780px', maxHeight: '90vh', overflowY: 'auto', padding: '28px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '14px' }}>
              <div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: '800', color: '#ffffff' }}>Create AlgoTrade Strategy</h3>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Define market, candle timeframe, indicators, patterns, and execution parameters</p>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="btn btn-cancel" style={{ padding: '6px' }}>
                <X style={{ width: '18px', height: '18px' }} />
              </button>
            </div>

            <form onSubmit={handleSubmitNewAlgo}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '16px' }}>
                {/* Strategy Name */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>Strategy Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Ishaq strategy 1, NiftyScalper"
                    value={formData.algo_name}
                    onChange={(e) => setFormData({ ...formData, algo_name: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </div>

                {/* Creator / Owner */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>Creator / Owner</label>
                  <input
                    type="text"
                    value={formData.creator}
                    onChange={(e) => setFormData({ ...formData, creator: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '16px' }}>
                {/* Market */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>Market</label>
                  <select
                    value={formData.market}
                    onChange={(e) => setFormData({ ...formData, market: e.target.value })}
                    style={{ width: '100%' }}
                  >
                    <option value="INDIAN_EQUITY">Indian Equity (NSE/BSE)</option>
                    <option value="FOREX">Forex</option>
                    <option value="COMMODITY">Commodity</option>
                    <option value="CRYPTO">Crypto</option>
                  </select>
                </div>

                {/* Candlestick Timeframe */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>Candle Timeframe</label>
                  <select
                    value={formData.timeframe}
                    onChange={(e) => setFormData({ ...formData, timeframe: e.target.value })}
                    style={{ width: '100%' }}
                  >
                    <option value="1m">1m</option>
                    <option value="3m">3m</option>
                    <option value="5m">5m</option>
                    <option value="15m">15m</option>
                    <option value="1h">1h</option>
                    <option value="1d">1d</option>
                  </select>
                </div>

                {/* Risk-to-Reward Ratio */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>Risk : Reward</label>
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

              {/* Target Symbols (Multiple) */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>Target Stock(s) &amp; Symbols (comma-separated)</label>
                <input
                  type="text"
                  placeholder="e.g. RELIANCE, TCS, HDFCBANK, INFY, or EUR/USD"
                  value={formData.symbols}
                  onChange={(e) => setFormData({ ...formData, symbols: e.target.value })}
                  style={{ width: '100%' }}
                />
              </div>

              {/* Benchmark / Sector Indices */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>Benchmark &amp; Sectoral Indices (comma-separated)</label>
                <input
                  type="text"
                  placeholder="e.g. NIFTY 50, NIFTY BANK, NIFTY IT"
                  value={formData.indices}
                  onChange={(e) => setFormData({ ...formData, indices: e.target.value })}
                  style={{ width: '100%' }}
                />
              </div>

              {/* Time Period / Historical Date Range */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '16px', background: 'rgba(15, 23, 42, 0.6)', padding: '12px', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>Start Date (Historical Test)</label>
                  <input
                    type="date"
                    value={formData.start_date}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>End Date (Historical Test)</label>
                  <input
                    type="date"
                    value={formData.end_date}
                    onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </div>
              </div>

              {/* Custom Schedule Start/Stop */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>Daily Auto-Start Time</label>
                  <input
                    type="time"
                    step="1"
                    value={formData.start_time}
                    onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>Daily Auto-Stop Time</label>
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
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '8px' }}>Patterns to Identify</label>
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

              {/* Indicators to Apply */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '8px' }}>Indicators to Precalculate</label>
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

              {/* Data to Fetch */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '8px' }}>Data to Fetch</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {['candles', 'volume', 'MVA', 'RSI', 'OI', 'vix', 'index_movement'].map((item) => {
                    const checked = (formData.extra_data || []).includes(item);
                    return (
                      <button
                        type="button"
                        key={item}
                        onClick={() => handleCheckboxToggle('extra_data', item)}
                        className={checked ? 'btn btn-blue' : 'btn btn-cancel'}
                        style={{ padding: '6px 12px', fontSize: '0.75rem' }}
                      >
                        {checked && <Check style={{ width: '12px', height: '12px' }} />}
                        <span style={{ textTransform: 'uppercase' }}>{item}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Modal Buttons (Popping Style: Purple Execute, Grey Cancel) */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '16px' }}>
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
      {/* MODAL 2: SIGNAL DETAIL & DUAL CHARTS (Execution Chart + 30-Bar Audit Chart) */}
      {/* ========================================================================= */}
      {selectedSignalForDetail && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.8)',
          backdropFilter: 'blur(10px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 60,
          padding: '24px',
        }}>
          <div className="glass-panel" style={{ width: '100%', maxWidth: '1100px', maxHeight: '92vh', overflowY: 'auto', padding: '28px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '14px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span className={`badge ${selectedSignalForDetail.direction === 'CALL' ? 'badge-call' : 'badge-put'}`}>{selectedSignalForDetail.direction}</span>
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

            {/* Signal Key Levels Summary */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '24px' }}>
              <div style={{ padding: '12px', background: 'rgba(15, 23, 42, 0.7)', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Entry Price</div>
                <div style={{ fontSize: '1.2rem', fontWeight: '800', color: '#ffffff' }}>{selectedSignalForDetail.price}</div>
              </div>
              <div style={{ padding: '12px', background: 'rgba(15, 23, 42, 0.7)', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Key S/R Level</div>
                <div style={{ fontSize: '1.2rem', fontWeight: '800', color: '#38bdf8' }}>{selectedSignalForDetail.level}</div>
              </div>
              <div style={{ padding: '12px', background: 'rgba(15, 23, 42, 0.7)', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Stop Loss</div>
                <div style={{ fontSize: '1.2rem', fontWeight: '800', color: '#f87171' }}>{selectedSignalForDetail.stop_loss || '--'}</div>
              </div>
              <div style={{ padding: '12px', background: 'rgba(15, 23, 42, 0.7)', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Target Price</div>
                <div style={{ fontSize: '1.2rem', fontWeight: '800', color: '#34d399' }}>{selectedSignalForDetail.target || '--'}</div>
              </div>
            </div>

            {/* DUAL CHARTS: Execution Chart + 30-Candle Audit Chart */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
              {/* Execution Chart */}
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
                <div style={{ height: '360px', borderRadius: '12px', overflow: 'hidden', border: '1px solid rgba(255, 255, 255, 0.1)', background: '#0a0e17' }}>
                  {selectedSignalForDetail.chart_url ? (
                    <iframe src={selectedSignalForDetail.chart_url} title="Execution Chart" style={{ width: '100%', height: '100%', border: 'none' }} />
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#64748b' }}>
                      Execution chart will appear here upon generation.
                    </div>
                  )}
                </div>
              </div>

              {/* 30-Candle Audit Chart */}
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
                <div style={{ height: '360px', borderRadius: '12px', overflow: 'hidden', border: '1px solid rgba(255, 255, 255, 0.1)', background: '#0a0e17' }}>
                  {selectedSignalForDetail.audit_chart_url ? (
                    <iframe src={selectedSignalForDetail.audit_chart_url} title="Audit Chart" style={{ width: '100%', height: '100%', border: 'none' }} />
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#64748b' }}>
                      Audit chart (+30 candles window) will appear here upon generation.
                    </div>
                  )}
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
          background: 'rgba(0, 0, 0, 0.8)',
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
                <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Walk-forward candle replay evaluation over: {evaluationModal.evaluation_period}</p>
              </div>
              <button onClick={() => setEvaluationModal(null)} className="btn btn-cancel" style={{ padding: '6px' }}>
                <X style={{ width: '18px', height: '18px' }} />
              </button>
            </div>

            {(evaluationModal.reports || []).map((rep, idx) => (
              <div key={idx} style={{ marginBottom: '24px', background: 'rgba(15, 23, 42, 0.7)', borderRadius: '12px', padding: '20px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                  <h4 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#ffffff' }}>{rep.symbol} [{rep.total_bars} bars]</h4>
                  <span style={{ fontSize: '0.85rem', fontWeight: '700', color: rep.total_pnl_pct >= 0 ? '#34d399' : '#f87171' }}>
                    Net: {rep.total_pnl_pct > 0 ? `+${rep.total_pnl_pct.toFixed(2)}%` : `${rep.total_pnl_pct.toFixed(2)}%`}
                  </span>
                </div>

                {/* Metrics Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '16px' }}>
                  <div style={{ padding: '10px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Signals</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: '700', color: '#ffffff' }}>{rep.total_signals}</div>
                  </div>
                  <div style={{ padding: '10px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Win Rate</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: '700', color: '#34d399' }}>{rep.win_rate_pct.toFixed(1)}%</div>
                  </div>
                  <div style={{ padding: '10px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Wins / Losses</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: '700', color: '#cbd5e1' }}>{rep.winning_trades} / {rep.losing_trades}</div>
                  </div>
                  <div style={{ padding: '10px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Profit Factor</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: '700', color: '#38bdf8' }}>{rep.profit_factor.toFixed(2)}</div>
                  </div>
                </div>

                {/* Raw Summary Output Box */}
                <pre style={{
                  background: 'rgba(0, 0, 0, 0.45)',
                  padding: '14px',
                  borderRadius: '10px',
                  fontSize: '0.75rem',
                  color: '#94a3b8',
                  overflowX: 'auto',
                  border: '1px solid rgba(255, 255, 255, 0.05)',
                  lineHeight: '1.5',
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
