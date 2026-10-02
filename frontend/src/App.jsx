import React, { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import DashboardView from './components/DashboardView';
import AlgoTradeView from './components/AlgoTradeView';
import PaperTradingView from './components/PaperTradingView';
import MarketDataView from './components/MarketDataView';
import MarketViewScreen from './components/marketview/MarketViewScreen';
import TerminalConfigScreen from './components/marketview/TerminalConfigScreen';
import EventTriggersScreen from './components/events/EventTriggersScreen';
import AuditingView from './components/AuditingView';

import LoggingView from './components/LoggingView';
import UserManagementScreen from './components/admin/UserManagementScreen';
import MarketCatalogScreen from './components/catalog/MarketCatalogScreen';
import LoginPage from './components/auth/LoginPage';
import ThemeSettingsModal from './components/ThemeSettingsModal';
import { api, connectTelemetryStream } from './api';
import { useAuth } from './context/AuthContext';
import { CheckCircle2, AlertTriangle, X } from 'lucide-react';
import { Box, CircularProgress } from '@mui/material';

export default function App() {
  const { isAuthenticated, isLoading } = useAuth();
  const [currentModule, setCurrentModule] = useState('dashboard');
  const [algos, setAlgos] = useState([]);
  const [signals, setSignals] = useState([]);
  const [pnlSummary, setPnlSummary] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [isRunningAll, setIsRunningAll] = useState(false);
  const [toast, setToast] = useState(null);
  const [streamConnected, setStreamConnected] = useState(false);
  const [concurrencyStats, setConcurrencyStats] = useState(null);
  const [openPositionsCount, setOpenPositionsCount] = useState(0);

  // Show a notification toast
  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 3800);
  };

  // Fetch status, algos, and pnl summary
  const loadData = useCallback(async () => {
    try {
      const [statusRes, algosRes, pnlRes, signalsRes, concRes, paperPosRes] = await Promise.all([
        api.getStatus().catch(() => null),
        api.listAlgos({ include_deleted: false }).catch(() => []),
        api.getPnl().catch(() => null),
        api.listSignals().catch(() => []),
        api.getConcurrency().catch(() => null),
        api.getPaperPositions().catch(() => []),
      ]);

      if (statusRes) setSystemStatus(statusRes);
      if (Array.isArray(algosRes)) setAlgos(algosRes);
      if (pnlRes) setPnlSummary(pnlRes);
      if (Array.isArray(signalsRes)) setSignals(signalsRes);
      if (concRes) setConcurrencyStats(concRes);
      if (Array.isArray(paperPosRes)) setOpenPositionsCount(paperPosRes.length);
    } catch (err) {
      console.error('Error refreshing platform data:', err);
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    loadData();

    // Connect to real-time Server-Sent Events (SSE) telemetry stream
    const stream = connectTelemetryStream({
      onOpen: () => {
        setStreamConnected(true);
      },
      onError: () => {
        setStreamConnected(false);
      },
      onConnected: (data) => {
        setStreamConnected(true);
        if (data?.concurrency) setConcurrencyStats(data.concurrency);
      },
      onHeartbeat: (data) => {
        setStreamConnected(true);
        if (data?.concurrency) setConcurrencyStats(data.concurrency);
      },
      onCycleUpdate: (data) => {
        if (data?.metrics) {
          setAlgos((prev) =>
            prev.map((a) => (a.algo_id === data.algo_id ? { ...a, ...data.metrics } : a))
          );
        }
      },
      onSignalAlert: (data) => {
        if (data?.signal) {
          setSignals((prev) => [data.signal, ...prev]);
          showToast(
            `⚡ New Signal [${data.signal.symbol}]: ${data.signal.direction} @ ₹${data.signal.price}`,
            'info'
          );
        }
      },
      onPaperPositionOpened: () => {
        setOpenPositionsCount((prev) => prev + 1);
      },
      onPaperPositionClosed: () => {
        setOpenPositionsCount((prev) => Math.max(0, prev - 1));
      },
    });

    const interval = setInterval(loadData, 45000);
    return () => {
      stream.close();
      clearInterval(interval);
    };
  }, [loadData]);

  // Strategy Action Handlers
  const handleStartAlgo = async (id) => {
    try {
      await api.startAlgo(id);
      showToast(`AlgoTrade '${id}' started successfully.`);
      await loadData();
    } catch (err) {
      showToast(err.message || 'Failed to start AlgoTrade', 'error');
    }
  };

  const handleStopAlgo = async (id) => {
    try {
      await api.stopAlgo(id);
      showToast(`AlgoTrade '${id}' stopped.`);
      await loadData();
    } catch (err) {
      showToast(err.message || 'Failed to stop AlgoTrade', 'error');
    }
  };

  const handlePauseAlgo = async (id) => {
    try {
      await api.pauseAlgo(id);
      showToast(`AlgoTrade '${id}' paused.`);
      await loadData();
    } catch (err) {
      showToast(err.message || 'Failed to pause AlgoTrade', 'error');
    }
  };

  const handleCopyAlgo = async (id) => {
    try {
      const res = await api.copyAlgo(id);
      showToast(`AlgoTrade cloned as '${res.algo_name || 'Copy'}'.`);
      await loadData();
    } catch (err) {
      showToast(err.message || 'Failed to clone AlgoTrade', 'error');
    }
  };

  const handleDeleteAlgo = async (id) => {
    try {
      await api.deleteAlgo(id, false);
      showToast(`AlgoTrade '${id}' moved to trash.`);
      await loadData();
    } catch (err) {
      showToast(err.message || 'Failed to delete AlgoTrade', 'error');
    }
  };

  const handleCreateAlgo = async (data) => {
    try {
      const res = await api.createAlgo(data);
      showToast(`Strategy '${res.algo_name}' created and ready.`);
      await loadData();
      return res;
    } catch (err) {
      showToast(err.message || 'Failed to create strategy', 'error');
      throw err;
    }
  };

  const handleEvaluateAlgo = async (id, params) => {
    try {
      const res = await api.evaluateAlgo(id, params);
      showToast(`Backtest evaluation completed for ${id}.`);
      return res;
    } catch (err) {
      showToast(err.message || 'Backtest evaluation failed', 'error');
      throw err;
    }
  };

  const handleResendSignal = async (id) => {
    try {
      const res = await api.resendSignal(id);
      showToast(res.message || 'Signal alert resent successfully.');
    } catch (err) {
      showToast(err.message || 'Failed to resend signal alert', 'error');
    }
  };

  const handleRunAllCycles = async () => {
    setIsRunningAll(true);
    try {
      const res = await api.runAllAlgos();
      const count = res?.results?.length || 0;
      showToast(`Scan cycle completed across ${count} active AlgoTrade(s).`);
      await loadData();
    } catch (err) {
      showToast(err.message || 'Error executing scan cycles', 'error');
    } finally {
      setIsRunningAll(false);
    }
  };

  // Module Title helper
  const getModuleTitle = () => {
    switch (currentModule) {
      case 'dashboard':
        return 'Dashboard';
      case 'market':
        return 'MarketView';
      case 'terminal_config':
        return 'Terminal Configuration';
      case 'events':
        return 'Event WatchDog';
      case 'algotrade':
        return 'AlgoTrade';
      case 'paper':
        return 'Paper Trading';
      case 'catalog':
        return 'Market Catalog';
      case 'auditing':
        return 'Auditing';
      case 'logging':
        return 'Logging';
      case 'users':
        return 'User & Roles';
      default:
        return 'Dashboard';
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: 'background.default' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-primary)' }}>
      {/* Toast Notification */}
      {toast && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '24px',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '12px 20px',
          borderRadius: '12px',
          background: toast.type === 'error' ? 'rgba(239, 68, 68, 0.95)' : 'rgba(15, 23, 42, 0.95)',
          border: toast.type === 'error' ? '1px solid rgba(239, 68, 68, 0.5)' : '1px solid rgba(168, 85, 247, 0.4)',
          boxShadow: '0 10px 30px rgba(0, 0, 0, 0.6)',
          backdropFilter: 'blur(16px)',
          color: '#ffffff',
          fontSize: '0.875rem',
          fontWeight: '600',
          animation: 'fadeIn 0.2s ease',
        }}>
          {toast.type === 'error' ? (
            <AlertTriangle style={{ width: '18px', height: '18px', color: '#ffffff' }} />
          ) : (
            <CheckCircle2 style={{ width: '18px', height: '18px', color: '#c084fc' }} />
          )}
          <span>{toast.message}</span>
          <button
            onClick={() => setToast(null)}
            style={{ background: 'transparent', border: 'none', color: '#ffffff', opacity: 0.7, cursor: 'pointer', display: 'flex' }}
          >
            <X style={{ width: '16px', height: '16px' }} />
          </button>
        </div>
      )}

      {/* Sidebar Navigation */}
      <Sidebar
        currentModule={currentModule}
        onSelectModule={setCurrentModule}
        systemStatus={systemStatus}
        algosCount={algos.filter(a => !a.is_deleted).length}
        signalsCount={signals.length}
        openPositionsCount={openPositionsCount}
      />

      {/* Main Content Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Top Header */}
        <Header
          onRunAllCycles={handleRunAllCycles}
          isRunningAll={isRunningAll}
          activeModuleTitle={getModuleTitle()}
          streamConnected={streamConnected}
          concurrencyStats={concurrencyStats}
        />

        {/* View Router */}
        <main style={{ flex: 1, overflowY: 'auto' }}>
          {currentModule === 'dashboard' && (
            <DashboardView
              algos={algos}
              signals={signals}
              systemStatus={systemStatus}
              pnlSummary={pnlSummary}
              streamConnected={streamConnected}
              concurrencyStats={concurrencyStats}
              onStartAlgo={handleStartAlgo}
              onStopAlgo={handleStopAlgo}
              onPauseAlgo={handlePauseAlgo}
              onCopyAlgo={handleCopyAlgo}
              onDeleteAlgo={handleDeleteAlgo}
              onCreateAlgo={handleCreateAlgo}
              onSelectAlgo={() => setCurrentModule('algotrade')}
              onGoToSignals={() => setCurrentModule('signals')}
              onRunAllCycles={handleRunAllCycles}
              isRunningAll={isRunningAll}
              onResendSignal={handleResendSignal}
              onSelectModule={setCurrentModule}
            />
          )}

          {currentModule === 'algotrade' && (
            <AlgoTradeView
              algos={algos}
              onStartAlgo={handleStartAlgo}
              onStopAlgo={handleStopAlgo}
              onPauseAlgo={handlePauseAlgo}
              onCopyAlgo={handleCopyAlgo}
              onDeleteAlgo={handleDeleteAlgo}
              onCreateAlgo={handleCreateAlgo}
              onEvaluateAlgo={handleEvaluateAlgo}
              onResendSignal={handleResendSignal}
              initialTab="strategies"
            />
          )}

          {currentModule === 'paper' && (
            <PaperTradingView showToast={showToast} />
          )}

          {currentModule === 'signals' && (
            <AlgoTradeView
              algos={algos}
              onStartAlgo={handleStartAlgo}
              onStopAlgo={handleStopAlgo}
              onPauseAlgo={handlePauseAlgo}
              onCopyAlgo={handleCopyAlgo}
              onDeleteAlgo={handleDeleteAlgo}
              onCreateAlgo={handleCreateAlgo}
              onEvaluateAlgo={handleEvaluateAlgo}
              onResendSignal={handleResendSignal}
              initialTab="signals"
            />
          )}

          {currentModule === 'market' && (
            <MarketViewScreen />
          )}

          {currentModule === 'terminal_config' && (
            <TerminalConfigScreen />
          )}

          {currentModule === 'events' && (
            <EventTriggersScreen showToast={showToast} />
          )}

          {currentModule === 'catalog' && (
            <MarketCatalogScreen showToast={showToast} />
          )}


          {currentModule === 'auditing' && (
            <AuditingView
              onSelectAlgo={() => setCurrentModule('algotrade')}
            />
          )}

          {currentModule === 'logging' && (
            <LoggingView />
          )}

          {currentModule === 'users' && (
            <UserManagementScreen />
          )}
        </main>
      </div>

      {/* Global Theme Settings Modal */}
      <ThemeSettingsModal />
    </div>
  );
}
