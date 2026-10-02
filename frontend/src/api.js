/**
 * Central API Client for TxBot FastAPI Backend Service.
 * Automatically points to /api via Vite proxy or direct host.
 */

const API_BASE = '/api';

export async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const token = localStorage.getItem('auratrade_token');
  
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  try {
    const res = await fetch(url, { ...options, headers, credentials: 'include' });
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.detail || `HTTP Error ${res.status}: ${res.statusText}`);
    }
    return await res.json();
  } catch (err) {
    console.error(`API Call Failed [${endpoint}]:`, err);
    throw err;
  }
}

export const api = {
  // Module 1: Auth & User Administration
  login: (identifier, password) => request('/v1/auth/login', { method: 'POST', body: JSON.stringify({ identifier, password }) }),
  logout: () => request('/v1/auth/logout', { method: 'POST' }),
  getMe: () => request('/v1/auth/me'),
  
  // Module 1: Dynamic Role Management
  listRoles: () => request('/v1/roles'),
  createRole: (data) => request('/v1/roles', { method: 'POST', body: JSON.stringify(data) }),
  updateRole: (id, data) => request(`/v1/roles/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteRole: (id) => request(`/v1/roles/${id}`, { method: 'DELETE' }),

  // Module 1: User & Cash Management
  listUsers: () => request('/v1/users'),
  createUser: (data) => request('/v1/users', { method: 'POST', body: JSON.stringify(data) }),
  updateUserRole: (id, roleId) => request(`/v1/users/${id}/role`, { method: 'PUT', body: JSON.stringify({ role_id: roleId }) }),
  getUserBalance: (id) => request(`/v1/users/${id}/balance`),
  topupUserBalance: (id, data) => request(`/v1/users/${id}/balance/topup`, { method: 'POST', body: JSON.stringify(data) }),
  getBalanceAuditLogs: (id) => request(`/v1/users/${id}/balance/logs`),
  getUserTerminalConfig: () => request('/v1/users/me/terminal-config'),
  updateUserTerminalConfig: (data) => request('/v1/users/me/terminal-config', { method: 'PUT', body: JSON.stringify(data) }),

  // Status
  getStatus: () => request('/status'),

  // AlgoTrade Management
  listAlgos: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/algos${query ? `?${query}` : ''}`);
  },
  createAlgo: (data) => request('/algos', { method: 'POST', body: JSON.stringify(data) }),
  getAlgo: (id) => request(`/algos/${id}`),
  startAlgo: (id) => request(`/algos/${id}/start`, { method: 'POST' }),
  stopAlgo: (id) => request(`/algos/${id}/stop`, { method: 'POST' }),
  pauseAlgo: (id) => request(`/algos/${id}/pause`, { method: 'POST' }),
  copyAlgo: (id) => request(`/algos/${id}/copy`, { method: 'POST' }),
  deleteAlgo: (id, hard = false) => request(`/algos/${id}?hard=${hard}`, { method: 'DELETE' }),
  evaluateAlgo: (id, params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/algos/${id}/evaluate${query ? `?${query}` : ''}`, { method: 'POST' });
  },
  runAllAlgos: () => request('/algos/run-all', { method: 'POST' }),

  // Signals & PnL
  listSignals: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/signals${query ? `?${query}` : ''}`);
  },
  getSignal: (id) => request(`/signals/${id}`),
  resendSignal: (id) => request(`/signals/${id}/resend`, { method: 'POST' }),
  getPnl: (algoId) => request(`/pnl${algoId ? `?algo_id=${algoId}` : ''}`),

  // Market Data Layer
  fetchMarketData: (data) => request('/market/fetch', { method: 'POST', body: JSON.stringify(data) }),
  getMarketHistory: () => request('/market/history'),
  generateChart: (data) => request('/market/chart', { method: 'POST', body: JSON.stringify(data) }),
  compareCharts: (data) => request('/market/compare', { method: 'POST', body: JSON.stringify(data) }),

  // Auditing
  getAudits: () => request('/audits'),
  getAuditDetail: (algoName) => request(`/audits/${encodeURIComponent(algoName)}`),
  getAuditEvents: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/audits-events${query ? `?${query}` : ''}`);
  },

  // Logging
  getLogs: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/logs${query ? `?${query}` : ''}`);
  },

  // Market Catalog & Asset Directory (Module 2)
  getCatalogGroups: () => request('/catalog/groups'),
  getCatalogSymbols: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/catalog/symbols${query ? `?${query}` : ''}`);
  },
  searchCatalogAssets: (query, market, exchange) => {
    const params = new URLSearchParams({ query });
    if (market) params.append('market', market);
    if (exchange) params.append('exchange', exchange);
    return request(`/catalog/search?${params.toString()}`);
  },
  verifyCatalogAsset: (data) => request('/catalog/verify', { method: 'POST', body: JSON.stringify(data) }),
  addCatalogAsset: (data) => request('/catalog/add', { method: 'POST', body: JSON.stringify(data) }),
  toggleSymbolStatus: (symbol, isActive) => request(`/catalog/symbols/${symbol}/toggle?isActive=${isActive}`, { method: 'PATCH' }),
  deleteCatalogSymbol: (symbol) => request(`/catalog/symbols/${symbol}`, { method: 'DELETE' }),
  getCatalogCandles: (symbol, timeframe = '5m', limit = 180) => request(`/catalog/candles?symbol=${symbol}&timeframe=${timeframe}&limit=${limit}`),

  // Concurrency & Telemetry Overview
  getConcurrency: () => request('/concurrency'),

  // Paper Trading & Order Execution
  getPaperPortfolio: () => request('/paper/portfolio'),
  getPaperPositions: () => request('/paper/positions'),
  getPaperTrades: (limit = 100) => request(`/paper/trades?limit=${limit}`),
  closePaperPosition: (id, data = {}) => request(`/paper/positions/${id}/close`, { method: 'POST', body: JSON.stringify(data) }),
  modifyPaperPosition: (id, data) => request(`/paper/positions/${id}/modify`, { method: 'POST', body: JSON.stringify(data) }),
  resetPaperAccount: (data = {}) => request('/paper/reset', { method: 'POST', body: JSON.stringify(data) }),

  // Risk Management & Circuit Breaker (Phase 7)
  getRiskStatus: () => request('/risk/status'),
  updateRiskConfig: (data) => request('/risk/config', { method: 'POST', body: JSON.stringify(data) }),
  emergencySquareOff: (data = {}) => request('/risk/emergency-square-off', { method: 'POST', body: JSON.stringify(data) }),
  resetCircuitBreaker: () => request('/risk/reset-breaker', { method: 'POST' }),

  // Broker Management (Phase 7)
  getBrokers: () => request('/brokers'),
  selectBroker: (brokerName) => request('/brokers/select', { method: 'POST', body: JSON.stringify({ broker_name: brokerName }) }),
  getBrokerPositions: (brokerName) => request(`/brokers/${brokerName}/positions`),
  placeBrokerOrder: (brokerName, order) => request(`/brokers/${brokerName}/orders`, { method: 'POST', body: JSON.stringify(order) }),

  // MarketView Engine (Module 3)
  getMarketViewData: (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        query.append(k, v);
      }
    });
    return request(`/marketview/data?${query.toString()}`);
  },
  getMarketViewStatus: (market, symbol) => {
    const params = new URLSearchParams({ market });
    if (symbol) params.append('symbol', symbol);
    return request(`/marketview/status?${params.toString()}`);
  },
  getMarketViewQuote: (symbol, market) => {
    const params = new URLSearchParams({ symbol });
    if (market) params.append('market', market);
    return request(`/marketview/quote?${params.toString()}`);
  },
};

/**
 * Connects to the real-time Server-Sent Events (SSE) telemetry stream.
 * Automatically dispatches events for connection, heartbeat, cycle updates, signal alerts, and deep audit events.
 */
export function connectTelemetryStream({
  onConnected,
  onHeartbeat,
  onCycleUpdate,
  onSignalAlert,
  onLogEvent,
  onAuditEvent,
  onPaperPositionOpened,
  onPaperPositionClosed,
  onPaperPositionModified,
  onCircuitBreakerTripped,
  onCircuitBreakerReset,
  onEmergencyHaltTripped,
  onError,
  onOpen,
} = {}) {
  const eventSource = new EventSource('/api/stream');

  eventSource.onopen = (e) => {
    if (onOpen) onOpen(e);
  };

  eventSource.onerror = (e) => {
    if (onError) onError(e);
  };

  eventSource.addEventListener('connected', (e) => {
    try {
      const data = JSON.parse(e.data);
      if (onConnected) onConnected(data);
    } catch (err) {
      console.error('Failed parsing SSE connected payload:', err);
    }
  });

  eventSource.addEventListener('heartbeat', (e) => {
    try {
      const data = JSON.parse(e.data);
      if (onHeartbeat) onHeartbeat(data);
    } catch (err) {
      console.error('Failed parsing SSE heartbeat payload:', err);
    }
  });

  eventSource.addEventListener('cycle_update', (e) => {
    try {
      const data = JSON.parse(e.data);
      if (onCycleUpdate) onCycleUpdate(data);
    } catch (err) {
      console.error('Failed parsing SSE cycle_update payload:', err);
    }
  });

  eventSource.addEventListener('signal_alert', (e) => {
    try {
      const data = JSON.parse(e.data);
      if (onSignalAlert) onSignalAlert(data);
    } catch (err) {
      console.error('Failed parsing SSE signal_alert payload:', err);
    }
  });

  eventSource.addEventListener('log_event', (e) => {
    try {
      const data = JSON.parse(e.data);
      if (onLogEvent) onLogEvent(data);
    } catch (err) {
      console.error('Failed parsing SSE log_event payload:', err);
    }
  });

  eventSource.addEventListener('audit_event', (e) => {
    try {
      const data = JSON.parse(e.data);
      if (onAuditEvent) onAuditEvent(data);
    } catch (err) {
      console.error('Failed parsing SSE audit_event payload:', err);
    }
  });

  eventSource.addEventListener('paper_position_opened', (e) => {
    try {
      const data = JSON.parse(e.data);
      if (onPaperPositionOpened) onPaperPositionOpened(data);
    } catch (err) {
      console.error('Failed parsing SSE paper_position_opened payload:', err);
    }
  });

  eventSource.addEventListener('paper_position_closed', (e) => {
    try {
      const data = JSON.parse(e.data);
      if (onPaperPositionClosed) onPaperPositionClosed(data);
    } catch (err) {
      console.error('Failed parsing SSE paper_position_closed payload:', err);
    }
  });

  eventSource.addEventListener('paper_position_modified', (e) => {
    try {
      const data = JSON.parse(e.data);
      if (onPaperPositionModified) onPaperPositionModified(data);
    } catch (err) {
      console.error('Failed parsing SSE paper_position_modified payload:', err);
    }
  });

  eventSource.addEventListener('circuit_breaker_tripped', (e) => {
    try {
      const data = JSON.parse(e.data);
      if (onCircuitBreakerTripped) onCircuitBreakerTripped(data);
    } catch (err) {
      console.error('Failed parsing SSE circuit_breaker_tripped payload:', err);
    }
  });

  eventSource.addEventListener('circuit_breaker_reset', (e) => {
    try {
      const data = JSON.parse(e.data);
      if (onCircuitBreakerReset) onCircuitBreakerReset(data);
    } catch (err) {
      console.error('Failed parsing SSE circuit_breaker_reset payload:', err);
    }
  });

  eventSource.addEventListener('emergency_halt_tripped', (e) => {
    try {
      const data = JSON.parse(e.data);
      if (onEmergencyHaltTripped) onEmergencyHaltTripped(data);
    } catch (err) {
      console.error('Failed parsing SSE emergency_halt_tripped payload:', err);
    }
  });

  return {
    close: () => eventSource.close(),
  };
}

