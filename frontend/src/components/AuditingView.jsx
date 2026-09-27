import React, { useState, useEffect, useMemo } from 'react';
import { 
  ShieldCheck, 
  ShieldAlert, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  ExternalLink, 
  RefreshCw, 
  ArrowLeft, 
  BarChart3, 
  TrendingUp, 
  TrendingDown, 
  Search, 
  Filter, 
  AlertTriangle, 
  Layers, 
  ChevronRight, 
  FileText,
  Activity,
  Zap,
  Check
} from 'lucide-react';
import { api } from '../api';

export default function AuditingView({ onSelectAlgo }) {
  const [audits, setAudits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAlgoName, setSelectedAlgoName] = useState(null);
  const [algoDetail, setAlgoDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL'); // 'ALL', 'PROFIT', 'LOSS'
  const [selectedAuditChartUrl, setSelectedAuditChartUrl] = useState(null);

  // Fetch all audit summaries
  const fetchAudits = async () => {
    setLoading(true);
    try {
      const data = await api.getAudits();
      setAudits(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to fetch audits:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAudits();
  }, []);

  // Fetch detail when an algo is selected
  const handleSelectAudit = async (algoName) => {
    setSelectedAlgoName(algoName);
    setLoadingDetail(true);
    try {
      const detail = await api.getAuditDetail(algoName);
      setAlgoDetail(detail);
    } catch (err) {
      console.error(`Failed to fetch audit detail for ${algoName}:`, err);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleBackToList = () => {
    setSelectedAlgoName(null);
    setAlgoDetail(null);
    setSelectedAuditChartUrl(null);
  };

  // Filtered audits
  const filteredAudits = useMemo(() => {
    return audits.filter(a => {
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesName = (a.algo_name || '').toLowerCase().includes(q);
        const matchesId = (a.algo_id || '').toLowerCase().includes(q);
        const matchesMarket = (a.market || '').toLowerCase().includes(q);
        if (!matchesName && !matchesId && !matchesMarket) return false;
      }
      if (statusFilter === 'PROFIT' && (a.total_pnl_pct || 0) <= 0) return false;
      if (statusFilter === 'LOSS' && (a.total_pnl_pct || 0) >= 0) return false;
      return true;
    });
  }, [audits, searchQuery, statusFilter]);

  // Total summary metrics
  const totalAudits = audits.length;
  const totalSignals = audits.reduce((acc, a) => acc + (a.total_signals || 0), 0);
  const totalApproved = audits.reduce((acc, a) => acc + (a.approved_signals || 0), 0);
  const avgWinRate = audits.length > 0 
    ? (audits.reduce((acc, a) => acc + (a.win_rate_pct || 0), 0) / audits.length).toFixed(1) 
    : '0.0';

  return (
    <div style={{ padding: '24px', maxWidth: '1600px', margin: '0 auto' }}>
      {/* Top Banner & Stats */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(99, 102, 241, 0.2) 100%)',
              border: '1px solid rgba(59, 130, 246, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <ShieldCheck style={{ width: '20px', height: '20px', color: '#60a5fa' }} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.4rem', fontWeight: '800', color: '#ffffff', letterSpacing: '-0.02em', margin: 0 }}>
                Auditing & Compliance Engine
              </h2>
              <p style={{ fontSize: '0.85rem', color: '#94a3b8', margin: 0 }}>
                Continuous algorithmic verification, 30-candle post-signal lookahead audits, and rule validation footprints
              </p>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={selectedAlgoName ? () => handleSelectAudit(selectedAlgoName) : fetchAudits}
            className="btn btn-blue"
            disabled={loading || loadingDetail}
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <RefreshCw style={{ width: '15px', height: '15px', animation: (loading || loadingDetail) ? 'spin 1s linear infinite' : 'none' }} />
            <span>Refresh Audit Data</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '16px',
        marginBottom: '24px',
      }}>
        <div style={{
          background: 'rgba(15, 23, 42, 0.75)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '16px',
          padding: '16px 20px',
          backdropFilter: 'blur(12px)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: '600', textTransform: 'uppercase' }}>Audited Strategies</span>
            <Layers style={{ width: '18px', height: '18px', color: '#a855f7' }} />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: '800', color: '#ffffff' }}>
            {totalAudits}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>
            Active AlgoTrade pipelines
          </div>
        </div>

        <div style={{
          background: 'rgba(15, 23, 42, 0.75)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '16px',
          padding: '16px 20px',
          backdropFilter: 'blur(12px)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: '600', textTransform: 'uppercase' }}>Audited Signals</span>
            <Activity style={{ width: '18px', height: '18px', color: '#38bdf8' }} />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: '800', color: '#38bdf8' }}>
            {totalSignals}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>
            Total evaluated patterns
          </div>
        </div>

        <div style={{
          background: 'rgba(15, 23, 42, 0.75)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '16px',
          padding: '16px 20px',
          backdropFilter: 'blur(12px)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: '600', textTransform: 'uppercase' }}>Approved Signals</span>
            <CheckCircle2 style={{ width: '18px', height: '18px', color: '#10b981' }} />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: '800', color: '#34d399' }}>
            {totalApproved}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>
            Passed key S/R & VIX compliance
          </div>
        </div>

        <div style={{
          background: 'rgba(15, 23, 42, 0.75)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '16px',
          padding: '16px 20px',
          backdropFilter: 'blur(12px)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: '600', textTransform: 'uppercase' }}>Average Win Rate</span>
            <TrendingUp style={{ width: '18px', height: '18px', color: '#f59e0b' }} />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: '800', color: '#fbbf24' }}>
            {avgWinRate}%
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>
            Across all strategies
          </div>
        </div>
      </div>

      {/* Main Content: List View OR Detail View */}
      {!selectedAlgoName ? (
        /* ================= LIST VIEW ================= */
        <div style={{
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '18px',
          padding: '24px',
          backdropFilter: 'blur(16px)',
        }}>
          {/* Filter Bar */}
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: '1', minWidth: '280px' }}>
              <div style={{
                position: 'relative',
                width: '100%',
                maxWidth: '400px',
              }}>
                <Search style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', width: '16px', height: '16px', color: '#64748b' }} />
                <input
                  type="text"
                  placeholder="Search by Strategy Name or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '9px 12px 9px 38px',
                    borderRadius: '10px',
                    background: 'rgba(30, 41, 59, 0.6)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    color: '#f8fafc',
                    fontSize: '0.875rem',
                    outline: 'none',
                  }}
                />
              </div>

              {/* Status Filter Buttons */}
              <div style={{ display: 'flex', alignItems: 'center', background: 'rgba(30, 41, 59, 0.5)', padding: '3px', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                {['ALL', 'PROFIT', 'LOSS'].map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setStatusFilter(filter)}
                    style={{
                      padding: '6px 14px',
                      borderRadius: '8px',
                      fontSize: '0.75rem',
                      fontWeight: '700',
                      border: 'none',
                      cursor: 'pointer',
                      background: statusFilter === filter ? 'rgba(59, 130, 246, 0.25)' : 'transparent',
                      color: statusFilter === filter ? '#93c5fd' : '#94a3b8',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    {filter === 'ALL' ? 'All Results' : filter === 'PROFIT' ? 'Profitable' : 'Loss'}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
              Showing <span style={{ color: '#f8fafc', fontWeight: '700' }}>{filteredAudits.length}</span> audited pipelines
            </div>
          </div>

          {/* Audits Table */}
          {loading ? (
            <div style={{ padding: '60px', textAlign: 'center', color: '#94a3b8' }}>
              <RefreshCw style={{ width: '28px', height: '28px', animation: 'spin 1s linear infinite', margin: '0 auto 12px' }} />
              <p style={{ margin: 0, fontWeight: '600' }}>Loading audit records...</p>
            </div>
          ) : filteredAudits.length === 0 ? (
            <div style={{ padding: '60px', textAlign: 'center', color: '#64748b' }}>
              <ShieldAlert style={{ width: '36px', height: '36px', margin: '0 auto 12px', opacity: 0.5 }} />
              <p style={{ fontSize: '1rem', fontWeight: '600', color: '#94a3b8', margin: '0 0 4px' }}>No audit records found</p>
              <p style={{ fontSize: '0.8rem', margin: 0 }}>Create and execute an AlgoTrade strategy to start recording audits.</p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.08)', color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    <th style={{ padding: '12px 16px' }}>AlgoTrade Strategy</th>
                    <th style={{ padding: '12px 16px' }}>Market / Timeframe</th>
                    <th style={{ padding: '12px 16px' }}>Audited Signals</th>
                    <th style={{ padding: '12px 16px' }}>Approval Rate</th>
                    <th style={{ padding: '12px 16px' }}>Win Rate %</th>
                    <th style={{ padding: '12px 16px' }}>Total PnL %</th>
                    <th style={{ padding: '12px 16px' }}>Last Audit Timestamp</th>
                    <th style={{ padding: '12px 16px', textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAudits.map((item) => {
                    const isProfit = (item.total_pnl_pct || 0) >= 0;
                    const approvalPct = item.total_signals > 0 
                      ? Math.round((item.approved_signals / item.total_signals) * 100) 
                      : 0;

                    return (
                      <tr 
                        key={item.algo_id}
                        style={{ 
                          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                          transition: 'background 0.15s ease',
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                      >
                        <td style={{ padding: '14px 16px' }}>
                          <div style={{ fontWeight: '700', color: '#f8fafc', fontSize: '0.92rem' }}>
                            {item.algo_name}
                          </div>
                          <div style={{ fontSize: '0.72rem', color: '#64748b', fontFamily: 'monospace' }}>
                            {item.algo_id}
                          </div>
                        </td>

                        <td style={{ padding: '14px 16px' }}>
                          <span style={{
                            padding: '3px 8px',
                            borderRadius: '6px',
                            background: 'rgba(59, 130, 246, 0.15)',
                            color: '#60a5fa',
                            fontSize: '0.72rem',
                            fontWeight: '700',
                            marginRight: '6px'
                          }}>
                            {item.market}
                          </span>
                          <span style={{
                            padding: '3px 8px',
                            borderRadius: '6px',
                            background: 'rgba(147, 51, 234, 0.15)',
                            color: '#c084fc',
                            fontSize: '0.72rem',
                            fontWeight: '700',
                          }}>
                            {item.timeframe}
                          </span>
                        </td>

                        <td style={{ padding: '14px 16px' }}>
                          <div style={{ fontWeight: '700', color: '#ffffff' }}>
                            {item.total_signals}
                          </div>
                          <div style={{ fontSize: '0.72rem', color: '#10b981' }}>
                            {item.approved_signals} approved
                          </div>
                        </td>

                        <td style={{ padding: '14px 16px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <div style={{ flex: 1, maxWidth: '80px', height: '6px', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '999px', overflow: 'hidden' }}>
                              <div style={{
                                width: `${approvalPct}%`,
                                height: '100%',
                                background: approvalPct >= 70 ? '#10b981' : approvalPct >= 40 ? '#f59e0b' : '#ef4444',
                                borderRadius: '999px',
                              }}></div>
                            </div>
                            <span style={{ fontSize: '0.75rem', fontWeight: '700', color: '#e2e8f0' }}>{approvalPct}%</span>
                          </div>
                        </td>

                        <td style={{ padding: '14px 16px' }}>
                          <span style={{
                            fontSize: '0.85rem',
                            fontWeight: '800',
                            color: item.win_rate_pct >= 50 ? '#34d399' : '#f87171',
                          }}>
                            {item.win_rate_pct ? item.win_rate_pct.toFixed(1) : '0.0'}%
                          </span>
                        </td>

                        <td style={{ padding: '14px 16px' }}>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            fontSize: '0.875rem',
                            fontWeight: '800',
                            color: isProfit ? '#34d399' : '#f87171',
                          }}>
                            {isProfit ? <TrendingUp style={{ width: '14px', height: '14px' }} /> : <TrendingDown style={{ width: '14px', height: '14px' }} />}
                            {isProfit ? '+' : ''}{(item.total_pnl_pct || 0).toFixed(2)}%
                          </span>
                        </td>

                        <td style={{ padding: '14px 16px', color: '#94a3b8', fontSize: '0.75rem', fontFamily: 'monospace' }}>
                          {item.last_audit_time ? new Date(item.last_audit_time).toLocaleString() : 'N/A'}
                        </td>

                        <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                          <button
                            onClick={() => handleSelectAudit(item.algo_name)}
                            className="btn btn-blue"
                            style={{
                              padding: '6px 14px',
                              fontSize: '0.78rem',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                            }}
                          >
                            <span>Inspect Audit</span>
                            <ChevronRight style={{ width: '14px', height: '14px' }} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        /* ================= DETAIL VIEW ================= */
        <div>
          {/* Navigation Bar */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <button
              onClick={handleBackToList}
              className="btn btn-cancel"
              style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px' }}
            >
              <ArrowLeft style={{ width: '16px', height: '16px' }} />
              <span>Back to All Audits</span>
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{
                padding: '5px 12px',
                borderRadius: '8px',
                background: algoDetail?.status === 'RUNNING' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                color: algoDetail?.status === 'RUNNING' ? '#34d399' : '#f87171',
                fontSize: '0.75rem',
                fontWeight: '700',
                border: algoDetail?.status === 'RUNNING' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)',
              }}>
                Status: {algoDetail?.status || 'UNKNOWN'}
              </span>
              <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                Cycles Executed: <strong style={{ color: '#ffffff' }}>{algoDetail?.cycle_count || 0}</strong>
              </span>
            </div>
          </div>

          {loadingDetail ? (
            <div style={{ padding: '80px', textAlign: 'center', color: '#94a3b8' }}>
              <RefreshCw style={{ width: '32px', height: '32px', animation: 'spin 1s linear infinite', margin: '0 auto 12px' }} />
              <p>Fetching granular audit trail for <strong>{selectedAlgoName}</strong>...</p>
            </div>
          ) : !algoDetail ? (
            <div style={{ padding: '60px', textAlign: 'center', color: '#ef4444' }}>
              <AlertTriangle style={{ width: '36px', height: '36px', margin: '0 auto 12px' }} />
              <p>Failed to load audit detail for {selectedAlgoName}.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* Header Card */}
              <div style={{
                background: 'rgba(15, 23, 42, 0.85)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '16px',
                padding: '20px 24px',
                backdropFilter: 'blur(16px)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '16px',
              }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <h3 style={{ fontSize: '1.25rem', fontWeight: '800', color: '#ffffff', margin: 0 }}>
                      {algoDetail.algo_name}
                    </h3>
                    <span style={{ fontSize: '0.72rem', color: '#64748b', fontFamily: 'monospace', background: 'rgba(0,0,0,0.3)', padding: '2px 8px', borderRadius: '4px' }}>
                      {algoDetail.algo_id}
                    </span>
                  </div>
                  <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: '4px 0 0' }}>
                    Initialized: {new Date(algoDetail.created_at).toLocaleString()} • Continuous Background Auditing Enabled
                  </p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Audited Signals</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: '800', color: '#38bdf8' }}>
                      {(algoDetail.signals || []).length}
                    </div>
                  </div>
                  <div style={{ width: '1px', height: '32px', background: 'rgba(255, 255, 255, 0.1)' }}></div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>PnL Trades</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: '800', color: '#a855f7' }}>
                      {(algoDetail.pnl_history || []).length}
                    </div>
                  </div>
                </div>
              </div>

              {/* Signals Audit & Validation Table */}
              <div style={{
                background: 'rgba(15, 23, 42, 0.85)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '16px',
                padding: '24px',
                backdropFilter: 'blur(16px)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                  <h4 style={{ fontSize: '1rem', fontWeight: '700', color: '#ffffff', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <CheckCircle2 style={{ width: '18px', height: '18px', color: '#10b981' }} />
                    <span>Rule Validation & Signal Audit Footprint</span>
                  </h4>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    Dual-Chart Auditing (+30 Candles Window Verification)
                  </span>
                </div>

                {(algoDetail.signals || []).length === 0 ? (
                  <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
                    No signals have been generated or audited by this AlgoTrade yet.
                  </div>
                ) : (
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.08)', color: '#94a3b8', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          <th style={{ padding: '10px 14px' }}>Signal ID</th>
                          <th style={{ padding: '10px 14px' }}>Symbol</th>
                          <th style={{ padding: '10px 14px' }}>Direction</th>
                          <th style={{ padding: '10px 14px' }}>Pattern</th>
                          <th style={{ padding: '10px 14px' }}>Trigger Price</th>
                          <th style={{ padding: '10px 14px' }}>SL / Target</th>
                          <th style={{ padding: '10px 14px' }}>Audit Status</th>
                          <th style={{ padding: '10px 14px' }}>Audit Charts</th>
                        </tr>
                      </thead>
                      <tbody>
                        {algoDetail.signals.map((sig, idx) => {
                          const isCall = (sig.direction || '').toUpperCase() === 'CALL';
                          const isApproved = sig.status === 'APPROVED' || sig.status === 'CONFIRMED_SIGNAL' || !sig.status;

                          return (
                            <tr
                              key={sig.id || idx}
                              style={{
                                borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                                transition: 'background 0.15s ease',
                              }}
                              onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)'}
                              onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                            >
                              <td style={{ padding: '12px 14px', fontFamily: 'monospace', color: '#94a3b8', fontSize: '0.75rem' }}>
                                {sig.id || `SIG-${idx + 1}`}
                              </td>

                              <td style={{ padding: '12px 14px', fontWeight: '700', color: '#ffffff' }}>
                                {sig.symbol}
                              </td>

                              <td style={{ padding: '12px 14px' }}>
                                <span style={{
                                  padding: '3px 8px',
                                  borderRadius: '6px',
                                  fontSize: '0.72rem',
                                  fontWeight: '800',
                                  background: isCall ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                                  color: isCall ? '#34d399' : '#f87171',
                                  border: isCall ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)',
                                }}>
                                  {sig.direction || 'SIGNAL'}
                                </span>
                              </td>

                              <td style={{ padding: '12px 14px', color: '#cbd5e1' }}>
                                {sig.pattern || 'Technical Breakout'}
                              </td>

                              <td style={{ padding: '12px 14px', fontWeight: '700', color: '#f8fafc' }}>
                                ₹{sig.price ? Number(sig.price).toFixed(2) : '-'}
                              </td>

                              <td style={{ padding: '12px 14px', fontSize: '0.75rem', color: '#94a3b8' }}>
                                <div>SL: <span style={{ color: '#f87171', fontWeight: '600' }}>₹{sig.stop_loss ? Number(sig.stop_loss).toFixed(2) : '-'}</span></div>
                                <div>TGT: <span style={{ color: '#34d399', fontWeight: '600' }}>₹{sig.target ? Number(sig.target).toFixed(2) : '-'}</span></div>
                              </td>

                              <td style={{ padding: '12px 14px' }}>
                                <span style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                  padding: '3px 8px',
                                  borderRadius: '6px',
                                  fontSize: '0.72rem',
                                  fontWeight: '700',
                                  background: isApproved ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                                  color: isApproved ? '#34d399' : '#fbbf24',
                                }}>
                                  {isApproved ? <Check style={{ width: '12px', height: '12px' }} /> : <AlertTriangle style={{ width: '12px', height: '12px' }} />}
                                  {sig.status || 'APPROVED'}
                                </span>
                              </td>

                              <td style={{ padding: '12px 14px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  {sig.audit_chart_url && (
                                    <button
                                      onClick={() => setSelectedAuditChartUrl(sig.audit_chart_url)}
                                      className="btn btn-blue"
                                      style={{ padding: '4px 10px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                                      title="Open +30 Candle Lookahead Audit Chart"
                                    >
                                      <BarChart3 style={{ width: '12px', height: '12px' }} />
                                      <span>Audit (+30)</span>
                                    </button>
                                  )}
                                  {sig.chart_url && (
                                    <button
                                      onClick={() => setSelectedAuditChartUrl(sig.chart_url)}
                                      className="btn btn-cancel"
                                      style={{ padding: '4px 10px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                                      title="Open Execution Chart"
                                    >
                                      <span>Exec Chart</span>
                                    </button>
                                  )}
                                  {!sig.audit_chart_url && !sig.chart_url && (
                                    <span style={{ fontSize: '0.72rem', color: '#64748b' }}>No Chart</span>
                                  )}
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Error Footprint / Audit Log section */}
              {algoDetail.error_log && algoDetail.error_log.length > 0 && (
                <div style={{
                  background: 'rgba(239, 68, 68, 0.05)',
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  borderRadius: '16px',
                  padding: '20px 24px',
                }}>
                  <h4 style={{ fontSize: '0.9rem', fontWeight: '700', color: '#f87171', margin: '0 0 12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <ShieldAlert style={{ width: '16px', height: '16px' }} />
                    <span>Audit Discrepancies & Anomaly Footprints ({algoDetail.error_log.length})</span>
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {algoDetail.error_log.map((err, idx) => (
                      <div key={idx} style={{ fontSize: '0.78rem', color: '#fca5a5', fontFamily: 'monospace', background: 'rgba(0,0,0,0.3)', padding: '8px 12px', borderRadius: '8px' }}>
                        {err}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Audit Chart Interactive Preview Modal */}
      {selectedAuditChartUrl && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(3, 7, 18, 0.85)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          padding: '24px',
        }}>
          <div style={{
            width: '100%',
            maxWidth: '1200px',
            height: '85vh',
            background: '#0f172a',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            borderRadius: '20px',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            boxShadow: '0 25px 60px rgba(0, 0, 0, 0.7)',
          }}>
            <div style={{
              padding: '16px 24px',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'rgba(15, 23, 42, 0.95)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <ShieldCheck style={{ width: '20px', height: '20px', color: '#60a5fa' }} />
                <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#ffffff', margin: 0 }}>
                  Audit Chart Verification (+30 Lookahead Window)
                </h3>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <a
                  href={selectedAuditChartUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-blue"
                  style={{ padding: '6px 12px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '6px', textDecoration: 'none' }}
                >
                  <ExternalLink style={{ width: '14px', height: '14px' }} />
                  <span>Open Fullscreen</span>
                </a>
                <button
                  onClick={() => setSelectedAuditChartUrl(null)}
                  className="btn btn-cancel"
                  style={{ padding: '6px 12px', fontSize: '0.75rem' }}
                >
                  Close
                </button>
              </div>
            </div>

            <div style={{ flex: 1, position: 'relative' }}>
              <iframe
                src={selectedAuditChartUrl}
                title="Audit Chart"
                style={{ width: '100%', height: '100%', border: 'none' }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
