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
  ArrowDown
} from 'lucide-react';
import { api } from '../api';

export default function LoggingView() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedSource, setSelectedSource] = useState('all'); // 'all', 'market', 'signals', 'delivery', 'errors'
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

  // Auto-refresh interval
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchLogs();
    }, 4000);
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
      // Errors only tab
      if (selectedSource === 'errors' && !item.is_error) {
        return false;
      }
      // Source match if not all and not errors
      if (selectedSource !== 'all' && selectedSource !== 'errors' && item.source !== selectedSource) {
        return false;
      }
      // Search keyword match
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return item.text.toLowerCase().includes(q) || item.source.toLowerCase().includes(q);
      }
      return true;
    });
  }, [logs, selectedSource, searchQuery]);

  // Download logs as text file
  const handleDownloadLogs = () => {
    const content = filteredLogs.map(l => `[${l.source.toUpperCase()}] ${l.text}`).join('\n');
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `txbot_logs_${selectedSource}_${Date.now()}.log`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const getSourceBadgeStyle = (source) => {
    switch (source) {
      case 'market':
        return { background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)' };
      case 'signals':
        return { background: 'rgba(52, 211, 153, 0.15)', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.3)' };
      case 'delivery':
        return { background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', border: '1px solid rgba(168, 85, 247, 0.3)' };
      default:
        return { background: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8', border: '1px solid rgba(148, 163, 184, 0.3)' };
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1600px', margin: '0 auto' }}>
      {/* Header & Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.2) 0%, rgba(99, 102, 241, 0.2) 100%)',
            border: '1px solid rgba(168, 85, 247, 0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <ScrollText style={{ width: '20px', height: '20px', color: '#c084fc' }} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: '800', color: '#ffffff', letterSpacing: '-0.02em', margin: 0 }}>
              Live Execution Footprints & Logs
            </h2>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', margin: 0 }}>
              Real-time asynchronous telemetry across Market Data, Pattern Engine, Signals, and Telegram Delivery
            </p>
          </div>
        </div>

        {/* Global Control Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className="btn btn-cancel"
            style={{
              padding: '7px 14px',
              fontSize: '0.78rem',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              color: autoRefresh ? '#34d399' : '#94a3b8',
              borderColor: autoRefresh ? 'rgba(52, 211, 153, 0.4)' : 'rgba(255, 255, 255, 0.1)',
            }}
          >
            {autoRefresh ? <Pause style={{ width: '14px', height: '14px' }} /> : <Play style={{ width: '14px', height: '14px' }} />}
            <span>Auto-Refresh: {autoRefresh ? 'ON' : 'OFF'}</span>
          </button>

          <button
            onClick={() => fetchLogs()}
            className="btn btn-blue"
            style={{ padding: '7px 14px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw style={{ width: '14px', height: '14px' }} />
            <span>Refresh</span>
          </button>

          <button
            onClick={handleDownloadLogs}
            className="btn btn-cancel"
            style={{ padding: '7px 14px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Download style={{ width: '14px', height: '14px' }} />
            <span>Download</span>
          </button>
        </div>
      </div>

      {/* Main Terminal Container */}
      <div style={{
        background: 'rgba(10, 15, 29, 0.95)',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        borderRadius: '18px',
        overflow: 'hidden',
        boxShadow: '0 20px 50px rgba(0, 0, 0, 0.6)',
        backdropFilter: 'blur(20px)',
      }}>
        {/* Terminal Sub-Header with Tabs & Search */}
        <div style={{
          padding: '14px 20px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(15, 23, 42, 0.9)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}>
          {/* Source Tabs */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(30, 41, 59, 0.6)', padding: '3px', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
            {[
              { id: 'all', label: 'All Streams' },
              { id: 'market', label: 'Market Data' },
              { id: 'signals', label: 'Signals' },
              { id: 'delivery', label: 'Dispatch' },
              { id: 'errors', label: 'Errors Only' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setSelectedSource(tab.id)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '7px',
                  fontSize: '0.75rem',
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: '1', maxWidth: '350px' }}>
            <div style={{ position: 'relative', width: '100%' }}>
              <Search style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', width: '14px', height: '14px', color: '#64748b' }} />
              <input
                type="text"
                placeholder="Search keywords, symbols, exceptions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%',
                  padding: '7px 10px 7px 32px',
                  borderRadius: '8px',
                  background: 'rgba(30, 41, 59, 0.8)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: '#f8fafc',
                  fontSize: '0.8rem',
                  outline: 'none',
                }}
              />
            </div>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="btn btn-cancel"
                style={{ padding: '6px 10px', fontSize: '0.72rem' }}
              >
                Clear
              </button>
            )}
          </div>

          {/* Auto Scroll Toggle */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => setAutoScroll(!autoScroll)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '5px 10px',
                borderRadius: '6px',
                background: autoScroll ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                color: autoScroll ? '#60a5fa' : '#64748b',
                fontSize: '0.72rem',
                cursor: 'pointer',
              }}
            >
              <ArrowDown style={{ width: '12px', height: '12px' }} />
              <span>Auto-Scroll</span>
            </button>
            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
              Lines: <strong style={{ color: '#cbd5e1' }}>{filteredLogs.length}</strong>
            </span>
          </div>
        </div>

        {/* Terminal Window Body */}
        <div
          ref={logTerminalRef}
          style={{
            height: '650px',
            overflowY: 'auto',
            padding: '16px 20px',
            fontFamily: 'Consolas, "Fira Code", Monaco, monospace',
            fontSize: '0.82rem',
            lineHeight: '1.6',
            background: '#070a13',
            color: '#e2e8f0',
          }}
        >
          {filteredLogs.length === 0 ? (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
              <ScrollText style={{ width: '40px', height: '40px', marginBottom: '12px', opacity: 0.4 }} />
              <p style={{ margin: 0, fontWeight: '600', color: '#94a3b8' }}>No logs match current filters</p>
              <p style={{ margin: '4px 0 0', fontSize: '0.75rem' }}>Try clearing search or selecting "All Streams"</p>
            </div>
          ) : (
            filteredLogs.map((item, index) => {
              const isErr = item.is_error;
              const badgeStyle = getSourceBadgeStyle(item.source);

              // Highlight key symbols / words in log lines
              let lineClass = isErr ? 'text-rose-400' : 'text-slate-300';

              return (
                <div
                  key={index}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '12px',
                    padding: '3px 0',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.02)',
                    color: isErr ? '#f87171' : '#cbd5e1',
                  }}
                >
                  {/* Line Number */}
                  <span style={{ width: '38px', color: '#475569', fontSize: '0.72rem', userSelect: 'none', textAlign: 'right' }}>
                    {index + 1}
                  </span>

                  {/* Source Badge */}
                  <span style={{
                    ...badgeStyle,
                    padding: '1px 6px',
                    borderRadius: '4px',
                    fontSize: '0.68rem',
                    fontWeight: '700',
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                    minWidth: '60px',
                    textAlign: 'center',
                    userSelect: 'none',
                  }}>
                    {item.source}
                  </span>

                  {/* Log Content */}
                  <span style={{ flex: 1, wordBreak: 'break-all', whiteSpace: 'pre-wrap' }}>
                    {item.text}
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
