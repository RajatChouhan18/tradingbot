import React, { useState, useMemo } from 'react';
import { 
  Play, 
  Square, 
  Pause, 
  Copy, 
  Trash2, 
  Radio, 
  TrendingUp, 
  TrendingDown, 
  Filter, 
  Search, 
  ArrowUpDown, 
  Clock, 
  User, 
  ShieldCheck,
  ChevronRight,
  Sparkles
} from 'lucide-react';

export default function DashboardView({ 
  algos, 
  onStartAlgo, 
  onStopAlgo, 
  onPauseAlgo, 
  onCopyAlgo, 
  onDeleteAlgo, 
  onSelectAlgo, 
  onGoToSignals,
  pnlSummary 
}) {
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [pnlFilter, setPnlFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortKey, setSortKey] = useState('name'); // 'name', 'startTime', 'owner'
  const [sortOrder, setSortOrder] = useState('asc'); // 'asc', 'desc'

  // Filtered & Sorted Algos
  const processedAlgos = useMemo(() => {
    return algos
      .filter((a) => {
        // Status filter
        if (statusFilter !== 'ALL') {
          if (statusFilter === 'RUNNING' && a.status !== 'RUNNING') return false;
          if (statusFilter === 'STOPPED' && a.status !== 'STOPPED') return false;
          if (statusFilter === 'PAUSED' && a.status !== 'PAUSED') return false;
          if (statusFilter === 'DELETED' && !a.is_deleted) return false;
        } else if (a.is_deleted) {
          return false;
        }

        // PnL filter
        if (pnlFilter === 'PROFIT' && (a.total_pnl_pct || 0) <= 0) return false;
        if (pnlFilter === 'LOSS' && (a.total_pnl_pct || 0) >= 0) return false;

        // Search query
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchName = (a.algo_name || '').toLowerCase().includes(q);
          const matchCreator = (a.creator || '').toLowerCase().includes(q);
          const matchSymbol = (a.symbols || []).some(s => s.toLowerCase().includes(q));
          if (!matchName && !matchCreator && !matchSymbol) return false;
        }

        return true;
      })
      .sort((a, b) => {
        let valA = '';
        let valB = '';

        if (sortKey === 'name') {
          valA = a.algo_name || '';
          valB = b.algo_name || '';
        } else if (sortKey === 'startTime') {
          valA = a.start_time || a.created_at || '';
          valB = b.start_time || b.created_at || '';
        } else if (sortKey === 'owner') {
          valA = a.creator || '';
          valB = b.creator || '';
        }

        const cmp = valA.localeCompare(valB);
        return sortOrder === 'asc' ? cmp : -cmp;
      });
  }, [algos, statusFilter, pnlFilter, searchQuery, sortKey, sortOrder]);

  const activeCount = algos.filter(a => a.status === 'RUNNING' && !a.is_deleted).length;
  const totalSignals = algos.reduce((sum, a) => sum + (a.signals_count || 0), 0);
  const netPnlPct = pnlSummary?.total_pnl_pct || 0;
  const winRatePct = pnlSummary?.win_rate_pct || 0;

  return (
    <div style={{ padding: '28px', maxWidth: '1440px', margin: '0 auto' }}>
      {/* Top Welcome & KPI Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '28px' }}>
        {/* Metric 1 */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.8rem', fontWeight: '600', marginBottom: '8px' }}>
            <span>Active AlgoTrades</span>
            <span style={{ padding: '4px 8px', borderRadius: '999px', background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', fontSize: '0.7rem' }}>Running</span>
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '800', color: '#ffffff', letterSpacing: '-0.03em' }}>
            {activeCount} <span style={{ fontSize: '1rem', color: '#64748b', fontWeight: '500' }}>/ {algos.length}</span>
          </div>
          <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '6px' }}>Parallel multi-symbol scanning active</p>
        </div>

        {/* Metric 2 */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.8rem', fontWeight: '600', marginBottom: '8px' }}>
            <span>Total Signals Generated</span>
            <Radio style={{ width: '16px', height: '16px', color: '#38bdf8' }} />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '800', color: '#ffffff', letterSpacing: '-0.03em' }}>
            {totalSignals}
          </div>
          <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '6px' }}>Confirmed PDF Price Action setups</p>
        </div>

        {/* Metric 3 */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.8rem', fontWeight: '600', marginBottom: '8px' }}>
            <span>Net Strategy Return (PnL)</span>
            {netPnlPct >= 0 ? <TrendingUp style={{ width: '16px', height: '16px', color: '#34d399' }} /> : <TrendingDown style={{ width: '16px', height: '16px', color: '#f87171' }} />}
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '800', color: netPnlPct >= 0 ? '#34d399' : '#f87171', letterSpacing: '-0.03em' }}>
            {netPnlPct >= 0 ? `+${netPnlPct.toFixed(2)}%` : `${netPnlPct.toFixed(2)}%`}
          </div>
          <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '6px' }}>{pnlSummary?.total_trades || 0} executed trades tracked</p>
        </div>

        {/* Metric 4 */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.8rem', fontWeight: '600', marginBottom: '8px' }}>
            <span>Overall Win Rate</span>
            <ShieldCheck style={{ width: '16px', height: '16px', color: '#a855f7' }} />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '800', color: '#ffffff', letterSpacing: '-0.03em' }}>
            {winRatePct.toFixed(1)}%
          </div>
          <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '6px' }}>Profit Factor: {pnlSummary?.profit_factor || 1.0}</p>
        </div>
      </div>

      {/* Control Bar: Search, Filters & Sorting */}
      <div className="glass-panel" style={{ padding: '16px 20px', marginBottom: '20px', display: 'flex', flexWrap: 'wrap', gap: '14px', alignItems: 'center', justifyContent: 'space-between' }}>
        {/* Search */}
        <div style={{ position: 'relative', minWidth: '260px', flex: '1' }}>
          <Search style={{ position: 'absolute', left: '12px', top: '12px', width: '16px', height: '16px', color: '#64748b' }} />
          <input
            type="text"
            placeholder="Search strategy, symbol, or creator..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ width: '100%', paddingLeft: '38px' }}
          />
        </div>

        {/* Status Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: '600' }}>Status:</span>
          {['ALL', 'RUNNING', 'PAUSED', 'STOPPED'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={statusFilter === st ? 'btn btn-blue' : 'btn btn-cancel'}
              style={{ padding: '6px 12px', fontSize: '0.78rem' }}
            >
              {st}
            </button>
          ))}
        </div>

        {/* PnL Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: '600' }}>PnL:</span>
          <button
            onClick={() => setPnlFilter('ALL')}
            className={pnlFilter === 'ALL' ? 'btn btn-blue' : 'btn btn-cancel'}
            style={{ padding: '6px 12px', fontSize: '0.78rem' }}
          >
            All
          </button>
          <button
            onClick={() => setPnlFilter('PROFIT')}
            className={pnlFilter === 'PROFIT' ? 'btn btn-emerald' : 'btn btn-cancel'}
            style={{ padding: '6px 12px', fontSize: '0.78rem' }}
          >
            Profit (&gt;0)
          </button>
          <button
            onClick={() => setPnlFilter('LOSS')}
            className={pnlFilter === 'LOSS' ? 'btn btn-stop' : 'btn btn-cancel'}
            style={{ padding: '6px 12px', fontSize: '0.78rem' }}
          >
            Loss (&lt;0)
          </button>
        </div>

        {/* Sorting */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ArrowUpDown style={{ width: '14px', height: '14px', color: '#94a3b8' }} />
          <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: '600' }}>Sort:</span>
          <select
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value)}
            style={{ padding: '6px 10px', fontSize: '0.8rem' }}
          >
            <option value="name">Strategy Name</option>
            <option value="startTime">Start Time</option>
            <option value="owner">Owner / Creator</option>
          </select>
          <button
            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
            className="btn btn-cancel"
            style={{ padding: '6px 10px', fontSize: '0.8rem' }}
          >
            {sortOrder.toUpperCase()}
          </button>
        </div>
      </div>

      {/* AlgoTrades List Table */}
      <div className="glass-panel" style={{ overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: '700', color: '#ffffff' }}>
            Registered AlgoTrade Strategies ({processedAlgos.length})
          </h2>
          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Click any row to view Signals & Analytics</span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ background: 'rgba(15, 23, 42, 0.6)', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                <th style={{ padding: '12px 20px' }}>Strategy / Process ID</th>
                <th style={{ padding: '12px 14px' }}>Market & Timeframe</th>
                <th style={{ padding: '12px 14px' }}>Target Assets</th>
                <th style={{ padding: '12px 14px' }}>Status</th>
                <th style={{ padding: '12px 14px' }}>Schedule (Start/Stop)</th>
                <th style={{ padding: '12px 14px' }}>Win Rate / PnL</th>
                <th style={{ padding: '12px 14px' }}>Owner</th>
                <th style={{ padding: '12px 20px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {processedAlgos.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
                    No AlgoTrades matching your filter criteria.
                  </td>
                </tr>
              ) : (
                processedAlgos.map((algo) => {
                  const pnl = algo.total_pnl_pct || 0;
                  const isPositive = pnl >= 0;
                  return (
                    <tr
                      key={algo.algo_id}
                      style={{
                        borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                        transition: 'background 0.15s',
                        cursor: 'pointer',
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                      onClick={() => onSelectAlgo(algo)}
                    >
                      {/* Name & ID */}
                      <td style={{ padding: '14px 20px' }}>
                        <div style={{ fontWeight: '700', color: '#f8fafc' }}>{algo.algo_name}</div>
                        <div style={{ fontSize: '0.72rem', color: '#94a3b8', fontFamily: 'monospace' }}>{algo.algo_id}</div>
                      </td>

                      {/* Market & Timeframe */}
                      <td style={{ padding: '14px 14px' }}>
                        <span style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>{algo.market}</span>
                        <div style={{ fontSize: '0.75rem', color: '#c084fc', fontWeight: '600' }}>[{algo.timeframe}] candles</div>
                      </td>

                      {/* Assets */}
                      <td style={{ padding: '14px 14px' }}>
                        <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                          {(algo.symbols || []).slice(0, 3).map((s) => (
                            <span key={s} style={{ fontSize: '0.7rem', padding: '2px 6px', background: 'rgba(51, 65, 85, 0.5)', borderRadius: '6px', color: '#f1f5f9' }}>
                              {s}
                            </span>
                          ))}
                          {(algo.symbols || []).length > 3 && (
                            <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>+{(algo.symbols || []).length - 3}</span>
                          )}
                        </div>
                      </td>

                      {/* Status */}
                      <td style={{ padding: '14px 14px' }}>
                        <span className={`badge badge-${algo.status.toLowerCase()}`}>
                          {algo.status}
                        </span>
                      </td>

                      {/* Schedule */}
                      <td style={{ padding: '14px 14px', fontSize: '0.8rem', color: '#cbd5e1' }}>
                        {algo.start_time || algo.stop_time ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Clock style={{ width: '12px', height: '12px', color: '#94a3b8' }} />
                            <span>{algo.start_time || '--'} → {algo.stop_time || '--'}</span>
                          </div>
                        ) : (
                          <span style={{ color: '#64748b' }}>Continuous</span>
                        )}
                      </td>

                      {/* Win Rate / PnL */}
                      <td style={{ padding: '14px 14px' }}>
                        <div style={{ fontWeight: '700', color: isPositive ? '#34d399' : '#f87171' }}>
                          {isPositive ? `+${pnl.toFixed(2)}%` : `${pnl.toFixed(2)}%`}
                        </div>
                        <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                          Win: {algo.win_rate_pct || 0}% ({algo.signals_count || 0} sigs)
                        </div>
                      </td>

                      {/* Owner */}
                      <td style={{ padding: '14px 14px', fontSize: '0.8rem', color: '#94a3b8' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                          <User style={{ width: '12px', height: '12px', color: '#38bdf8' }} />
                          <span style={{ color: '#cbd5e1' }}>{algo.creator || 'Admin'}</span>
                        </div>
                      </td>

                      {/* Action Buttons (Popping new style) */}
                      <td style={{ padding: '14px 20px', textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                          {/* Execute/Start (Purple) */}
                          <button
                            onClick={() => onStartAlgo(algo.algo_id)}
                            className="btn btn-execute"
                            style={{ padding: '6px 10px', fontSize: '0.75rem' }}
                            title="Run / Start Cycle"
                          >
                            <Play style={{ width: '12px', height: '12px', fill: '#fff' }} />
                            <span>Run</span>
                          </button>

                          {/* Stop (Red) */}
                          <button
                            onClick={() => onStopAlgo(algo.algo_id)}
                            className="btn btn-stop"
                            style={{ padding: '6px 10px', fontSize: '0.75rem' }}
                            title="Stop Strategy"
                          >
                            <Square style={{ width: '12px', height: '12px', fill: '#fff' }} />
                          </button>

                          {/* Copy (Blue) */}
                          <button
                            onClick={() => onCopyAlgo(algo.algo_id)}
                            className="btn btn-blue"
                            style={{ padding: '6px 10px', fontSize: '0.75rem' }}
                            title="Duplicate Strategy"
                          >
                            <Copy style={{ width: '12px', height: '12px' }} />
                          </button>

                          {/* View Signals (Grey/Blue) */}
                          <button
                            onClick={() => onGoToSignals(algo.algo_id)}
                            className="btn btn-cancel"
                            style={{ padding: '6px 10px', fontSize: '0.75rem' }}
                            title="View Generated Signals"
                          >
                            <Radio style={{ width: '12px', height: '12px', color: '#38bdf8' }} />
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
    </div>
  );
}
