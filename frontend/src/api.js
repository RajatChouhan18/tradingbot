/**
 * Central API Client for TxBot FastAPI Backend Service.
 * Automatically points to /api via Vite proxy or direct host.
 */

const API_BASE = '/api';

export async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  try {
    const res = await fetch(url, { ...options, headers });
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

  // Logging
  getLogs: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/logs${query ? `?${query}` : ''}`);
  },
};
