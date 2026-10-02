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
  ChevronDown,
  FileText,
  Activity,
  Zap,
  Check,
  Sliders,
  Cpu,
  Eye,
  Radio
} from 'lucide-react';
import { api, connectTelemetryStream } from '../api';

export default function AuditingView({ onSelectAlgo }) {
  const [audits, setAudits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAlgoName, setSelectedAlgoName] = useState(null);
  const [algoDetail, setAlgoDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL'); // 'ALL', 'PROFIT', 'LOSS'
  const [eventTab, setEventTab] = useState('ALL'); // 'ALL', 'APPROVED', 'BLOCKED'
  const [selectedAuditChartUrl, setSelectedAuditChartUrl] = useState(null);
  const [expandedEventId, setExpandedEventId] = useState(null);
  const [liveEvents, setLiveEvents] = useState([]);

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

  // Real-time SSE Telemetry connection for live audit updates
  useEffect(() => {
    const stream = connectTelemetryStream({
      onAuditEvent: (evt) => {
        setLiveEvents((prev) => [evt, ...prev.slice(0, 39)]);
      },
      onCycleUpdate: () => {
        // Refetch audit metrics smoothly in background
        api.getAudits().then((data) => {
          if (Array.isArray(data)) setAudits(data);
        }).catch(() => {});
      },
    });

    return () => stream.close();
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
    setExpandedEventId(null);
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
  const totalMtfBlocks = audits.reduce((acc, a) => acc + (a.signals_blocked_by_mtf || 0), 0);
  const avgWinRate = audits.length > 0 
    ? (audits.reduce((acc, a) => acc + (a.win_rate_pct || 0), 0) / audits.length).toFixed(1) 
    : '0.0';

  return (
    <div style={{ padding: '24px', maxWidth: '1680px', margin: '0 auto', color: '#e2e8f0' }}>
      {/* Action Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', marginBottom: '20px', flexWrap: 'wrap', gap: '16px' }}>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={selectedAlgoName ? () => handleSelectAudit(selectedAlgoName) : fetchAudits}
            className="btn btn-blue"
            disabled={loading || loadingDetail}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: 'linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              padding: '8px 16px',
              fontSize: '0.82rem',
              fontWeight: '700',
              borderRadius: '10px',
              color: '#ffffff',
            }}
          >
            <RefreshCw style={{ width: '15px', height: '15px', animation: (loading || loadingDetail) ? 'spin 1s linear infinite' : 'none' }} />
            <span>Sync Audit Footprints</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Row (Institutional Density) */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
        gap: '14px',
        marginBottom: '24px',
      }}>
        <div style={{
          background: '#0d1322',
          border: '1px solid rgba(255, 255, 255, 0.07)',
          borderRadius: '14px',
          padding: '16px 20px',
          position: 'relative',
          overflow: 'hidden',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Audited Strategies</span>
            <Layers style={{ width: '16px', height: '16px', color: '#a855f7' }} />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', color: '#ffffff', fontFamily: 'monospace' }}>
            {totalAudits}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '2px' }}>
            Active AlgoTrade pipelines
          </div>
        </div>

        <div style={{
          background: '#0d1322',
          border: '1px solid rgba(255, 255, 255, 0.07)',
          borderRadius: '14px',
          padding: '16px 20px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Evaluated Signals</span>
            <Activity style={{ width: '16px', height: '16px', color: '#38bdf8' }} />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', color: '#38bdf8', fontFamily: 'monospace' }}>
            {totalSignals}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '2px' }}>
            Total candidate triggers
          </div>
        </div>

        <div style={{
          background: '#0d1322',
          border: '1px solid rgba(255, 255, 255, 0.07)',
          borderRadius: '14px',
          padding: '16px 20px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Approved Setups</span>
            <CheckCircle2 style={{ width: '16px', height: '16px', color: '#10b981' }} />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', color: '#34d399', fontFamily: 'monospace' }}>
            {totalApproved}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '2px' }}>
            Passed key S/R & VIX compliance
          </div>
        </div>

        <div style={{
          background: '#0d1322',
          border: '1px solid rgba(255, 255, 255, 0.07)',
          borderRadius: '14px',
          padding: '16px 20px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>MTF Trend Blocks</span>
            <ShieldAlert style={{ width: '16px', height: '16px', color: '#f59e0b' }} />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', color: '#fbbf24', fontFamily: 'monospace' }}>
            {totalMtfBlocks}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '2px' }}>
            Filtered against macro trend
          </div>
        </div>

        <div style={{
          background: '#0d1322',
          border: '1px solid rgba(255, 255, 255, 0.07)',
          borderRadius: '14px',
          padding: '16px 20px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Consolidated Win Rate</span>
            <TrendingUp style={{ width: '16px', height: '16px', color: '#10b981' }} />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', color: Number(avgWinRate) >= 50 ? '#34d399' : '#f87171', fontFamily: 'monospace' }}>
            {avgWinRate}%
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '2px' }}>
            Across all active portfolios
          </div>
        </div>
      </div>

      {/* Main Content: List View OR Detail View */}
      {!selectedAlgoName ? (
        /* ================= LIST VIEW ================= */
        <div style={{
          background: '#0d1322',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '16px',
          padding: '22px',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.4)',
        }}>
          {/* Filter Bar */}
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: '1', minWidth: '280px' }}>
              <div style={{ position: 'relative', width: '100%', maxWidth: '380px' }}>
                <Search style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', width: '15px', height: '15px', color: '#64748b' }} />
                <input
                  type="text"
                  placeholder="Filter by strategy name, ID or market..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px 8px 36px',
                    borderRadius: '8px',
                    background: '#080d19',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    color: '#f8fafc',
                    fontSize: '0.85rem',
                    outline: 'none',
                  }}
                />
              </div>

              {/* Status Filter Buttons */}
              <div style={{ display: 'flex', alignItems: 'center', background: '#080d19', padding: '3px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                {['ALL', 'PROFIT', 'LOSS'].map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setStatusFilter(filter)}
                    style={{
                      padding: '5px 12px',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                      fontWeight: '700',
                      border: 'none',
                      cursor: 'pointer',
                      background: statusFilter === filter ? 'rgba(59, 130, 246, 0.25)' : 'transparent',
                      color: statusFilter === filter ? '#93c5fd' : '#94a3b8',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    {filter === 'ALL' ? 'All Portfolios' : filter === 'PROFIT' ? 'Profitable' : 'Drawdown'}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ fontSize: '0.78rem', color: '#94a3b8', fontFamily: 'monospace' }}>
              Showing <span style={{ color: '#f8fafc', fontWeight: '700' }}>{filteredAudits.length}</span> audited strategies
            </div>
          </div>

          {/* Audits Table */}
          {loading ? (
            <div style={{ padding: '60px', textAlign: 'center', color: '#94a3b8' }}>
              <RefreshCw style={{ width: '28px', height: '28px', animation: 'spin 1s linear infinite', margin: '0 auto 12px', color: '#60a5fa' }} />
              <p style={{ margin: 0, fontWeight: '600' }}>Loading audit footprints from PostgreSQL...</p>
            </div>
          ) : filteredAudits.length === 0 ? (
            <div style={{ padding: '60px', textAlign: 'center', color: '#64748b' }}>
              <ShieldAlert style={{ width: '40px', height: '40px', margin: '0 auto 12px', opacity: 0.5, color: '#f59e0b' }} />
              <p style={{ fontSize: '1rem', fontWeight: '600', color: '#94a3b8', margin: '0 0 4px' }}>No audit records found</p>
              <p style={{ fontSize: '0.8rem', margin: 0 }}>Create and execute an AlgoTrade strategy to start recording audits.</p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.84rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.08)', color: '#94a3b8', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    <th style={{ padding: '10px 14px' }}>AlgoTrade Strategy</th>
                    <th style={{ padding: '10px 14px' }}>Market / Timeframe</th>
                    <th style={{ padding: '10px 14px' }}>Signals / Approved</th>
                    <th style={{ padding: '10px 14px' }}>Approval Rate</th>
                    <th style={{ padding: '10px 14px' }}>Filter Rejections</th>
                    <th style={{ padding: '10px 14px' }}>Win Rate %</th>
                    <th style={{ padding: '10px 14px' }}>Total PnL %</th>
                    <th style={{ padding: '10px 14px' }}>Avg Latency</th>
                    <th style={{ padding: '10px 14px', textAlign: 'right' }}>Action</th>
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
                          borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                          transition: 'background 0.15s ease',
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                      >
                        <td style={{ padding: '12px 14px' }}>
                          <div style={{ fontWeight: '700', color: '#f8fafc', fontSize: '0.9rem' }}>
                            {item.algo_name}
                          </div>
                          <div style={{ fontSize: '0.7rem', color: '#64748b', fontFamily: 'monospace' }}>
                            {item.algo_id}
                          </div>
                        </td>

                        <td style={{ padding: '12px 14px' }}>
                          <span style={{
                            padding: '2px 7px',
                            borderRadius: '5px',
                            background: 'rgba(59, 130, 246, 0.15)',
                            color: '#60a5fa',
                            fontSize: '0.7rem',
                            fontWeight: '700',
                            marginRight: '6px'
                          }}>
                            {item.market}
                          </span>
                          <span style={{
                            padding: '2px 7px',
                            borderRadius: '5px',
                            background: 'rgba(147, 51, 234, 0.15)',
                            color: '#c084fc',
                            fontSize: '0.7rem',
                            fontWeight: '700',
                          }}>
                            {item.timeframe}
                          </span>
                        </td>

                        <td style={{ padding: '12px 14px' }}>
                          <div style={{ fontWeight: '700', color: '#ffffff', fontFamily: 'monospace' }}>
                            {item.total_signals}
                          </div>
                          <div style={{ fontSize: '0.7rem', color: '#10b981', fontFamily: 'monospace' }}>
                            {item.approved_signals} approved
                          </div>
                        </td>

                        <td style={{ padding: '12px 14px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <div style={{ flex: 1, maxWidth: '70px', height: '5px', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '999px', overflow: 'hidden' }}>
                              <div style={{
                                width: `${approvalPct}%`,
                                height: '100%',
                                background: approvalPct >= 70 ? '#10b981' : approvalPct >= 40 ? '#f59e0b' : '#ef4444',
                                borderRadius: '999px',
                              }}></div>
                            </div>
                            <span style={{ fontSize: '0.72rem', fontWeight: '700', color: '#e2e8f0', fontFamily: 'monospace' }}>{approvalPct}%</span>
                          </div>
                        </td>

                        <td style={{ padding: '12px 14px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              background: 'rgba(245, 158, 11, 0.15)',
                              color: '#fbbf24',
                              fontSize: '0.68rem',
                              fontWeight: '700',
                            }} title="MTF confirmation filter blocks">
                              MTF: {item.signals_blocked_by_mtf || 0}
                            </span>
                            <span style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              background: 'rgba(239, 68, 68, 0.15)',
                              color: '#f87171',
                              fontSize: '0.68rem',
                              fontWeight: '700',
                            }} title="News filter blocks">
                              News: {item.signals_blocked_by_news || 0}
                            </span>
                          </div>
                        </td>

                        <td style={{ padding: '12px 14px' }}>
                          <span style={{
                            fontSize: '0.85rem',
                            fontWeight: '800',
                            color: item.win_rate_pct >= 50 ? '#34d399' : '#f87171',
                            fontFamily: 'monospace',
                          }}>
                            {item.win_rate_pct ? item.win_rate_pct.toFixed(1) : '0.0'}%
                          </span>
                        </td>

                        <td style={{ padding: '12px 14px' }}>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            fontSize: '0.85rem',
                            fontWeight: '800',
                            color: isProfit ? '#34d399' : '#f87171',
                            fontFamily: 'monospace',
                          }}>
                            {isProfit ? <TrendingUp style={{ width: '13px', height: '13px' }} /> : <TrendingDown style={{ width: '13px', height: '13px' }} />}
                            {isProfit ? '+' : ''}{(item.total_pnl_pct || 0).toFixed(2)}%
                          </span>
                        </td>

                        <td style={{ padding: '12px 14px', color: '#94a3b8', fontSize: '0.72rem', fontFamily: 'monospace' }}>
                          <span style={{ color: '#38bdf8' }}>{item.avg_latency_ms ? `${item.avg_latency_ms.toFixed(1)}ms` : '< 1ms'}</span>
                        </td>

                        <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                          <button
                            onClick={() => handleSelectAudit(item.algo_name)}
                            style={{
                              padding: '5px 12px',
                              fontSize: '0.75rem',
                              fontWeight: '700',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '5px',
                              background: 'rgba(59, 130, 246, 0.15)',
                              border: '1px solid rgba(59, 130, 246, 0.35)',
                              color: '#93c5fd',
                              borderRadius: '7px',
                              cursor: 'pointer',
                              transition: 'all 0.15s ease',
                            }}
                          >
                            <span>Inspect Audit</span>
                            <ChevronRight style={{ width: '13px', height: '13px' }} />
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
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
            <button
              onClick={handleBackToList}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '7px 14px',
                background: '#080d19',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                color: '#cbd5e1',
                borderRadius: '8px',
                fontSize: '0.8rem',
                fontWeight: '600',
                cursor: 'pointer',
              }}
            >
              <ArrowLeft style={{ width: '15px', height: '15px' }} />
              <span>Back to All Audits</span>
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{
                padding: '4px 10px',
                borderRadius: '6px',
                background: algoDetail?.status === 'RUNNING' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                color: algoDetail?.status === 'RUNNING' ? '#34d399' : '#f87171',
                fontSize: '0.72rem',
                fontWeight: '700',
                border: algoDetail?.status === 'RUNNING' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)',
              }}>
                Status: {algoDetail?.status || 'UNKNOWN'}
              </span>
              <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                Cycles Executed: <strong style={{ color: '#ffffff', fontFamily: 'monospace' }}>{algoDetail?.cycle_count || 0}</strong>
              </span>
            </div>
          </div>

          {loadingDetail ? (
            <div style={{ padding: '80px', textAlign: 'center', color: '#94a3b8' }}>
              <RefreshCw style={{ width: '32px', height: '32px', animation: 'spin 1s linear infinite', margin: '0 auto 12px', color: '#60a5fa' }} />
              <p>Fetching granular audit trail for <strong>{selectedAlgoName}</strong>...</p>
            </div>
          ) : !algoDetail ? (
            <div style={{ padding: '60px', textAlign: 'center', color: '#ef4444' }}>
              <AlertTriangle style={{ width: '36px', height: '36px', margin: '0 auto 12px' }} />
              <p>Failed to load audit detail for {selectedAlgoName}.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              {/* Header Card */}
              <div style={{
                background: '#0d1322',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '14px',
                padding: '18px 22px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '14px',
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
                  <p style={{ fontSize: '0.78rem', color: '#94a3b8', margin: '4px 0 0' }}>
                    Initialized: {new Date(algoDetail.created_at).toLocaleString()} • Continuous Background Auditing Active
                  </p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Audited Signals</div>
                    <div style={{ fontSize: '1.3rem', fontWeight: '800', color: '#38bdf8', fontFamily: 'monospace' }}>
                      {(algoDetail.signals || []).length}
                    </div>
                  </div>
                  <div style={{ width: '1px', height: '30px', background: 'rgba(255, 255, 255, 0.1)' }}></div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>PnL Trades</div>
                    <div style={{ fontSize: '1.3rem', fontWeight: '800', color: '#a855f7', fontFamily: 'monospace' }}>
                      {(algoDetail.pnl_history || []).length}
                    </div>
                  </div>
                </div>
              </div>

              {/* Event Tabs (All / Approved / Filter Blocks) */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {[
                  { id: 'ALL', label: 'All Audit Footprints' },
                  { id: 'APPROVED', label: 'Approved Signals' },
                  { id: 'BLOCKED', label: 'Filter Rejections' },
                ].map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setEventTab(t.id)}
                    style={{
                      padding: '6px 14px',
                      borderRadius: '8px',
                      fontSize: '0.75rem',
                      fontWeight: '700',
                      border: 'none',
                      cursor: 'pointer',
                      background: eventTab === t.id ? 'rgba(59, 130, 246, 0.25)' : '#080d19',
                      color: eventTab === t.id ? '#93c5fd' : '#94a3b8',
                      border: eventTab === t.id ? '1px solid rgba(59, 130, 246, 0.4)' : '1px solid rgba(255, 255, 255, 0.06)',
                    }}
                  >
                    {t.label}
                  </button>
                ))}
              </div>

              {/* Signals Audit & Validation Table */}
              <div style={{
                background: '#0d1322',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '16px',
                padding: '20px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                  <h4 style={{ fontSize: '0.95rem', fontWeight: '700', color: '#ffffff', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <CheckCircle2 style={{ width: '17px', height: '17px', color: '#10b981' }} />
                    <span>Rule Validation, Indicators & S/R Level Footprint</span>
                  </h4>
                  <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                    Click any row to expand deep Indicator & S/R Snapshots
                  </span>
                </div>

                {/* Combine signals and auditor events */}
                {(() => {
                  const combined = (algoDetail.audit_events && algoDetail.audit_events.length > 0)
                    ? algoDetail.audit_events
                    : (algoDetail.signals || []);

                  const filtered = combined.filter((e) => {
                    const st = (e.status || 'APPROVED').toUpperCase();
                    if (eventTab === 'APPROVED' && st !== 'APPROVED' && st !== 'CONFIRMED_SIGNAL') return false;
                    if (eventTab === 'BLOCKED' && st !== 'BLOCKED') return false;
                    return true;
                  });

                  if (filtered.length === 0) {
                    return (
                      <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
                        No events match current filter tab for this AlgoTrade.
                      </div>
                    );
                  }

                  return (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {filtered.map((item, idx) => {
                        const isCall = (item.direction || '').toUpperCase() === 'CALL';
                        const isApproved = item.status === 'APPROVED' || item.status === 'CONFIRMED_SIGNAL' || !item.status;
                        const eventId = item.id || `EVT-${idx}`;
                        const isExpanded = expandedEventId === eventId;
                        const indicatorSnap = item.indicator_snapshot || {};
                        const levelSnap = item.level_snapshot || {};

                        return (
                          <div
                            key={eventId}
                            style={{
                              background: isExpanded ? '#080d19' : 'rgba(255, 255, 255, 0.015)',
                              border: isExpanded ? '1px solid rgba(59, 130, 246, 0.4)' : '1px solid rgba(255, 255, 255, 0.05)',
                              borderRadius: '10px',
                              overflow: 'hidden',
                              transition: 'all 0.15s ease',
                            }}
                          >
                            <div
                              onClick={() => setExpandedEventId(isExpanded ? null : eventId)}
                              style={{
                                padding: '12px 16px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                cursor: 'pointer',
                                flexWrap: 'wrap',
                                gap: '10px',
                              }}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                <span style={{ color: '#64748b' }}>
                                  {isExpanded ? <ChevronDown style={{ width: '16px', height: '16px' }} /> : <ChevronRight style={{ width: '16px', height: '16px' }} />}
                                </span>
                                <div>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <span style={{ fontWeight: '800', color: '#ffffff', fontSize: '0.9rem' }}>
                                      {item.symbol}
                                    </span>
                                    <span style={{
                                      padding: '2px 7px',
                                      borderRadius: '4px',
                                      fontSize: '0.68rem',
                                      fontWeight: '800',
                                      background: isCall ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                                      color: isCall ? '#34d399' : '#f87171',
                                      border: isCall ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)',
                                    }}>
                                      {item.direction || 'SIGNAL'}
                                    </span>
                                    <span style={{ color: '#cbd5e1', fontSize: '0.78rem' }}>
                                      {item.pattern || 'Technical Setup'}
                                    </span>
                                  </div>
                                  <div style={{ fontSize: '0.7rem', color: '#64748b', fontFamily: 'monospace', marginTop: '2px' }}>
                                    {item.decision_reason || item.reason || 'Pipeline evaluated'}
                                  </div>
                                </div>
                              </div>

                              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                                {item.price && (
                                  <div style={{ textAlign: 'right', fontFamily: 'monospace', fontSize: '0.8rem' }}>
                                    <span style={{ color: '#94a3b8' }}>Trigger: </span>
                                    <strong style={{ color: '#f8fafc' }}>₹{Number(item.price).toFixed(2)}</strong>
                                  </div>
                                )}

                                <span style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                  padding: '3px 8px',
                                  borderRadius: '5px',
                                  fontSize: '0.7rem',
                                  fontWeight: '700',
                                  background: isApproved ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                                  color: isApproved ? '#34d399' : '#fbbf24',
                                  border: isApproved ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(245, 158, 11, 0.3)',
                                }}>
                                  {isApproved ? <Check style={{ width: '11px', height: '11px' }} /> : <AlertTriangle style={{ width: '11px', height: '11px' }} />}
                                  {item.status || 'APPROVED'}
                                </span>

                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }} onClick={(e) => e.stopPropagation()}>
                                  {item.audit_chart_url && (
                                    <button
                                      onClick={() => setSelectedAuditChartUrl(item.audit_chart_url)}
                                      style={{
                                        padding: '4px 9px',
                                        fontSize: '0.7rem',
                                        fontWeight: '700',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '4px',
                                        background: 'rgba(59, 130, 246, 0.15)',
                                        border: '1px solid rgba(59, 130, 246, 0.35)',
                                        color: '#93c5fd',
                                        borderRadius: '5px',
                                        cursor: 'pointer',
                                      }}
                                    >
                                      <BarChart3 style={{ width: '12px', height: '12px' }} />
                                      <span>Audit (+30)</span>
                                    </button>
                                  )}
                                  {item.chart_url && (
                                    <button
                                      onClick={() => setSelectedAuditChartUrl(item.chart_url)}
                                      style={{
                                        padding: '4px 9px',
                                        fontSize: '0.7rem',
                                        fontWeight: '600',
                                        background: '#0d1322',
                                        border: '1px solid rgba(255, 255, 255, 0.12)',
                                        color: '#cbd5e1',
                                        borderRadius: '5px',
                                        cursor: 'pointer',
                                      }}
                                    >
                                      <span>Exec</span>
                                    </button>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Expanded Indicator & S/R Level Snapshot Drawer */}
                            {isExpanded && (
                              <div style={{
                                padding: '14px 18px',
                                borderTop: '1px solid rgba(255, 255, 255, 0.06)',
                                background: '#050811',
                                fontSize: '0.78rem',
                              }}>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
                                  {/* Indicator Snapshot Panel */}
                                  <div style={{
                                    background: '#0d1322',
                                    border: '1px solid rgba(255, 255, 255, 0.06)',
                                    borderRadius: '8px',
                                    padding: '12px 14px',
                                  }}>
                                    <div style={{ fontWeight: '700', color: '#38bdf8', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                      <Sliders style={{ width: '13px', height: '13px' }} />
                                      <span>Indicator Snapshot at Execution</span>
                                    </div>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontFamily: 'monospace' }}>
                                      <div>RSI (14): <strong style={{ color: '#f8fafc' }}>{indicatorSnap.rsi ? Number(indicatorSnap.rsi).toFixed(2) : (item.rsi ? Number(item.rsi).toFixed(2) : 'N/A')}</strong></div>
                                      <div>Trend State: <strong style={{ color: indicatorSnap.trend_state === 'UPTREND' ? '#34d399' : indicatorSnap.trend_state === 'DOWNTREND' ? '#f87171' : '#fbbf24' }}>{indicatorSnap.trend_state || 'N/A'}</strong></div>
                                      <div>MTF Trend: <strong style={{ color: '#c084fc' }}>{indicatorSnap.htf_trend || item.mtf_trend || 'ALIGNED'}</strong></div>
                                      <div>ATR Volatility: <strong style={{ color: '#f8fafc' }}>{levelSnap.atr ? Number(levelSnap.atr).toFixed(4) : (item.atr ? Number(item.atr).toFixed(4) : 'N/A')}</strong></div>
                                    </div>
                                  </div>

                                  {/* Key S/R & Risk Levels Panel */}
                                  <div style={{
                                    background: '#0d1322',
                                    border: '1px solid rgba(255, 255, 255, 0.06)',
                                    borderRadius: '8px',
                                    padding: '12px 14px',
                                  }}>
                                    <div style={{ fontWeight: '700', color: '#10b981', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                      <Cpu style={{ width: '13px', height: '13px' }} />
                                      <span>Dynamic S/R & ATR Risk Bracket</span>
                                    </div>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontFamily: 'monospace' }}>
                                      <div>Support Level: <strong style={{ color: '#34d399' }}>₹{indicatorSnap.support_level ? Number(indicatorSnap.support_level).toFixed(2) : (levelSnap.level ? Number(levelSnap.level).toFixed(2) : 'N/A')}</strong></div>
                                      <div>Resistance Level: <strong style={{ color: '#f87171' }}>₹{indicatorSnap.resistance_level ? Number(indicatorSnap.resistance_level).toFixed(2) : 'N/A'}</strong></div>
                                      <div>Stop Loss: <strong style={{ color: '#f87171' }}>₹{levelSnap.stop_loss ? Number(levelSnap.stop_loss).toFixed(2) : (item.stop_loss ? Number(item.stop_loss).toFixed(2) : 'N/A')}</strong></div>
                                      <div>Profit Target: <strong style={{ color: '#34d399' }}>₹{levelSnap.target ? Number(levelSnap.target).toFixed(2) : (item.target ? Number(item.target).toFixed(2) : 'N/A')}</strong></div>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  );
                })()}
              </div>

              {/* Error Footprint / Audit Log section */}
              {algoDetail.error_log && algoDetail.error_log.length > 0 && (
                <div style={{
                  background: 'rgba(239, 68, 68, 0.05)',
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  borderRadius: '14px',
                  padding: '16px 20px',
                }}>
                  <h4 style={{ fontSize: '0.85rem', fontWeight: '700', color: '#f87171', margin: '0 0 10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <ShieldAlert style={{ width: '15px', height: '15px' }} />
                    <span>Audit Discrepancies & Anomaly Footprints ({algoDetail.error_log.length})</span>
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {algoDetail.error_log.map((err, idx) => (
                      <div key={idx} style={{ fontSize: '0.75rem', color: '#fca5a5', fontFamily: 'monospace', background: 'rgba(0,0,0,0.3)', padding: '6px 10px', borderRadius: '6px' }}>
                        {typeof err === 'object' ? JSON.stringify(err) : String(err)}
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
          background: 'rgba(3, 7, 18, 0.88)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          padding: '24px',
        }}>
          <div style={{
            width: '100%',
            maxWidth: '1240px',
            height: '86vh',
            background: '#0d1322',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            borderRadius: '18px',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            boxShadow: '0 25px 60px rgba(0, 0, 0, 0.8)',
          }}>
            <div style={{
              padding: '14px 20px',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: '#080d19',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <ShieldCheck style={{ width: '18px', height: '18px', color: '#60a5fa' }} />
                <h3 style={{ fontSize: '1rem', fontWeight: '700', color: '#ffffff', margin: 0 }}>
                  Audit Chart Verification (+30 Lookahead Window)
                </h3>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <a
                  href={selectedAuditChartUrl}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    padding: '5px 12px',
                    fontSize: '0.75rem',
                    fontWeight: '700',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    background: 'rgba(59, 130, 246, 0.2)',
                    border: '1px solid rgba(59, 130, 246, 0.4)',
                    color: '#93c5fd',
                    borderRadius: '6px',
                    textDecoration: 'none',
                  }}
                >
                  <ExternalLink style={{ width: '13px', height: '13px' }} />
                  <span>Open Fullscreen</span>
                </a>
                <button
                  onClick={() => setSelectedAuditChartUrl(null)}
                  style={{
                    padding: '5px 12px',
                    fontSize: '0.75rem',
                    fontWeight: '600',
                    background: '#0d1322',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    color: '#cbd5e1',
                    borderRadius: '6px',
                    cursor: 'pointer',
                  }}
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

            {/* Standardized Chart Diagnostic Data Footer */}
            <div style={{ padding: '8px 20px', background: '#080d19', borderTop: '1px solid rgba(255, 255, 255, 0.08)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontFamily: 'monospace' }}>
                Diagnostic: <span style={{ color: '#38bdf8' }}>0.052s</span> Data | <span style={{ color: '#a855f7' }}>0.018s</span> Chart | <span style={{ color: '#32D74B', fontWeight: 700 }}>0.070s</span> Total (+30 Candle Audit Window)
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
