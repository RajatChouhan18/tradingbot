import React, { useState, useEffect, useRef, useMemo } from 'react';
import { 
  ScrollText, 
  Search, 
  RefreshCw, 
  Trash2, 
  Download, 
  Filter, 
  AlertCircle, 
  Radio, 
  Send, 
  LineChart, 
  CheckCircle2, 
  Play, 
  Pause,
  ArrowDown,
  Terminal,
  ShieldCheck,
  Activity,
  Layers
} from 'lucide-react';
import { api, connectTelemetryStream } from '../api';

export default function LoggingView() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedSource, setSelectedSource] = useState('all'); // 'all', 'engine', 'market', 'signals', 'audit', 'delivery', 'errors'
  const [searchQuery, setSearchQuery] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [autoScroll, setAutoScroll] = useState(true);
  const logTerminalRef = useRef(null);

  // Fetch logs from backend
  const fetchLogs = async () => {
    try {
      const sourceParam = selectedSource === 'errors' ? 'all' : selectedSource;
      const data = await api.getLogs({ source: sourceParam, limit: 300 });
      if (data && Array.isArray(data.logs)) {
        setLogs(data.logs);
      }
    } catch (err) {
      console.error('Failed to fetch logs:', err);
    }
  };

  // Initial load
  useEffect(() => {
    fetchLogs();
  }, [selectedSource]);

  // Real-time SSE live stream listener
  useEffect(() => {
    const stream = connectTelemetryStream({
      onLogEvent: (entry) => {
        setLogs((prev) => [...prev.slice(-400), entry]);
      },
      onAuditEvent: (evt) => {
        setLogs((prev) => [
          ...prev.slice(-400),
          {
            source: 'audit',
            level: 'INFO',
            text: `[AUDIT] ${evt.symbol} | ${evt.status} | Pattern: ${evt.pattern} | Reason: ${evt.decision_reason || evt.reason}`,
            is_error: false,
            timestamp: evt.created_at || new Date().toISOString(),
          },
        ]);
      },
      onSignalAlert: (payload) => {
        const sig = payload.signal || {};
        setLogs((prev) => [
          ...prev.slice(-400),
          {
            source: 'signals',
            level: 'INFO',
            text: `[SIGNAL] ${sig.symbol} ${sig.direction} triggered at ₹${sig.price} via ${payload.algo_name || 'AlgoTrade'}`,
            is_error: false,
            timestamp: new Date().toISOString(),
          },
        ]);
      },
    });

    return () => stream.close();
  }, []);

  // Periodic polling fallback
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchLogs();
    }, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, selectedSource]);

  // Auto scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logTerminalRef.current) {
      logTerminalRef.current.scrollTop = logTerminalRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  // Filter logs client-side
  const filteredLogs = useMemo(() => {
    return logs.filter(item => {
      const src = (item.source || '').toLowerCase();
      // Errors only tab
      if (selectedSource === 'errors' && !item.is_error && (item.level || '').toUpperCase() !== 'ERROR') {
        return false;
      }
      // Source match if not all and not errors
      if (selectedSource !== 'all' && selectedSource !== 'errors' && src !== selectedSource) {
        return false;
      }
      // Search keyword match
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const text = (item.text || item.message || '').toLowerCase();
        return text.includes(q) || src.includes(q);
      }
      return true;
    });
  }, [logs, selectedSource, searchQuery]);

  // Clear logs view
  const handleClearLogs = () => {
    setLogs([]);
  };

  // Download logs as text file
  const handleDownloadLogs = () => {
    const content = filteredLogs.map(l => `[${(l.timestamp || '').slice(0, 19)}] [${(l.source || 'APP').toUpperCase()}] ${l.text || l.message}`).join('\n');
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `txbot_telemetry_${selectedSource}_${Date.now()}.log`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const getSourceBadgeStyle = (source) => {
    switch ((source || '').toLowerCase()) {
      case 'market':
        return { background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)' };
      case 'signals':
        return { background: 'rgba(52, 211, 153, 0.15)', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.3)' };
      case 'audit':
        return { background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', border: '1px solid rgba(168, 85, 247, 0.3)' };
      case 'delivery':
        return { background: 'rgba(234, 179, 8, 0.15)', color: '#facc15', border: '1px solid rgba(234, 179, 8, 0.3)' };
      case 'engine':
      case 'system':
        return { background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', border: '1px solid rgba(99, 102, 241, 0.3)' };
      default:
        return { background: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8', border: '1px solid rgba(148, 163, 184, 0.3)' };
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1680px', margin: '0 auto', color: '#e2e8f0' }}>
      {/* Control Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '16px' }}>
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '5px',
          background: 'rgba(56, 189, 248, 0.12)',
          color: '#38bdf8',
          border: '1px solid rgba(56, 189, 248, 0.3)',
          padding: '4px 10px',
          borderRadius: '999px',
          fontSize: '0.72rem',
          fontWeight: '700',
          letterSpacing: '0.04em',
        }}>
          <Radio style={{ width: '10px', height: '10px', animation: 'pulse 1.5s infinite' }} />
          REAL-TIME SSE TELEMETRY STREAM
        </span>

        {/* Global Control Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            style={{
              padding: '6px 13px',
              fontSize: '0.75rem',
              fontWeight: '700',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: '#080d19',
              border: autoRefresh ? '1px solid rgba(52, 211, 153, 0.4)' : '1px solid rgba(255, 255, 255, 0.1)',
              color: autoRefresh ? '#34d399' : '#94a3b8',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
          >
            {autoRefresh ? <Pause style={{ width: '13px', height: '13px' }} /> : <Play style={{ width: '13px', height: '13px' }} />}
            <span>Auto-Sync: {autoRefresh ? 'ON' : 'OFF'}</span>
          </button>

          <button
            onClick={() => fetchLogs()}
            style={{
              padding: '6px 13px',
              fontSize: '0.75rem',
              fontWeight: '700',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'rgba(59, 130, 246, 0.18)',
              border: '1px solid rgba(59, 130, 246, 0.4)',
              color: '#93c5fd',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
          >
            <RefreshCw style={{ width: '13px', height: '13px' }} />
            <span>Poll</span>
          </button>

          <button
            onClick={handleClearLogs}
            style={{
              padding: '6px 12px',
              fontSize: '0.75rem',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              background: '#080d19',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: '#94a3b8',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
            title="Clear display logs"
          >
            <Trash2 style={{ width: '13px', height: '13px' }} />
            <span>Clear</span>
          </button>

          <button
            onClick={handleDownloadLogs}
            style={{
              padding: '6px 13px',
              fontSize: '0.75rem',
              fontWeight: '700',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: '#0d1322',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              color: '#f8fafc',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
          >
            <Download style={{ width: '13px', height: '13px' }} />
            <span>Export Log</span>
          </button>
        </div>
      </div>

      {/* Main Terminal Container (Institutional Styling) */}
      <div style={{
        background: '#0a0f1d',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '16px',
        overflow: 'hidden',
        boxShadow: '0 25px 60px rgba(0, 0, 0, 0.7)',
      }}>
        {/* Terminal Sub-Header with Tabs & Search */}
        <div style={{
          padding: '12px 18px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          background: '#080d19',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}>
          {/* Source Tabs */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', background: 'rgba(255, 255, 255, 0.03)', padding: '3px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
            {[
              { id: 'all', label: 'All Streams' },
              { id: 'engine', label: 'Engine' },
              { id: 'signals', label: 'Signals' },
              { id: 'audit', label: 'Audits' },
              { id: 'market', label: 'Market Feed' },
              { id: 'delivery', label: 'Dispatches' },
              { id: 'errors', label: 'Errors' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setSelectedSource(tab.id)}
                style={{
                  padding: '5px 11px',
                  borderRadius: '6px',
                  fontSize: '0.72rem',
                  fontWeight: '700',
                  border: 'none',
                  cursor: 'pointer',
                  background: selectedSource === tab.id ? 'rgba(59, 130, 246, 0.3)' : 'transparent',
                  color: selectedSource === tab.id ? '#93c5fd' : '#94a3b8',
                  transition: 'all 0.15s ease',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Search Box */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: '1', maxWidth: '340px' }}>
            <div style={{ position: 'relative', width: '100%' }}>
              <Search style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', width: '14px', height: '14px', color: '#64748b' }} />
              <input
                type="text"
                placeholder="Search keywords, symbols, exceptions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%',
                  padding: '6px 10px 6px 32px',
                  borderRadius: '7px',
                  background: '#0d1322',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: '#f8fafc',
                  fontSize: '0.78rem',
                  outline: 'none',
                }}
              />
            </div>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                style={{
                  padding: '5px 9px',
                  fontSize: '0.7rem',
                  background: '#0d1322',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: '#94a3b8',
                  borderRadius: '6px',
                  cursor: 'pointer',
                }}
              >
                Clear
              </button>
            )}
          </div>

          {/* Auto Scroll Toggle */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              onClick={() => setAutoScroll(!autoScroll)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '4px 9px',
                borderRadius: '6px',
                background: autoScroll ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                color: autoScroll ? '#60a5fa' : '#64748b',
                fontSize: '0.7rem',
                cursor: 'pointer',
              }}
            >
              <ArrowDown style={{ width: '12px', height: '12px' }} />
              <span>Auto-Scroll</span>
            </button>
            <span style={{ fontSize: '0.72rem', color: '#64748b', fontFamily: 'monospace' }}>
              Lines: <strong style={{ color: '#cbd5e1' }}>{filteredLogs.length}</strong>
            </span>
          </div>
        </div>

        {/* Terminal Window Body */}
        <div
          ref={logTerminalRef}
          style={{
            height: '670px',
            overflowY: 'auto',
            padding: '16px 20px',
            fontFamily: '"JetBrains Mono", Consolas, "Fira Code", Monaco, monospace',
            fontSize: '0.8rem',
            lineHeight: '1.65',
            background: '#040711',
            color: '#cbd5e1',
          }}
        >
          {filteredLogs.length === 0 ? (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
              <ScrollText style={{ width: '40px', height: '40px', marginBottom: '12px', opacity: 0.3 }} />
              <p style={{ margin: 0, fontWeight: '600', color: '#94a3b8' }}>No logs match current filters</p>
              <p style={{ margin: '4px 0 0', fontSize: '0.75rem' }}>Select "All Streams" or clear search keywords</p>
            </div>
          ) : (
            filteredLogs.map((item, index) => {
              const isErr = item.is_error || (item.level || '').toUpperCase() === 'ERROR';
              const badgeStyle = getSourceBadgeStyle(item.source);
              const textContent = item.text || item.message || '';
              const timeStr = item.timestamp ? item.timestamp.slice(11, 19) : '--:--:--';

              return (
                <div
                  key={index}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                    padding: '2px 0',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.015)',
                    color: isErr ? '#f87171' : '#cbd5e1',
                  }}
                >
                  {/* Line Number */}
                  <span style={{ width: '36px', color: '#334155', fontSize: '0.7rem', userSelect: 'none', textAlign: 'right' }}>
                    {index + 1}
                  </span>

                  {/* Timestamp */}
                  <span style={{ color: '#475569', fontSize: '0.7rem', userSelect: 'none' }}>
                    {timeStr}
                  </span>

                  {/* Source Badge */}
                  <span style={{
                    ...badgeStyle,
                    padding: '0 6px',
                    borderRadius: '4px',
                    fontSize: '0.65rem',
                    fontWeight: '700',
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                    minWidth: '58px',
                    textAlign: 'center',
                    userSelect: 'none',
                  }}>
                    {item.source || 'APP'}
                  </span>

                  {/* Log Content */}
                  <span style={{ flex: 1, wordBreak: 'break-all', whiteSpace: 'pre-wrap' }}>
                    {textContent}
                  </span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
