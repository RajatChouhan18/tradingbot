# TxBot Code Index: Frontend Repository (`frontend`)

> **Index Identifier**: `frontend`  
> **Index Suffix**: `FRONTEND`  
> **Source Directory**: [`frontend/`](file:///e:/Txbot/frontend)  
> **Role**: React 19 Single Page Application (SPA), user interface, trading command center, and interactive visualization client.

---

## 1. Overview & Technology Stack

The `frontend` application is an ultra-fast, modern trading dashboard built for non-technical users and quantitative operators. It connects to the FastAPI backend service to manage algorithmic trading strategies, view live market data, inspect interactive TradingView charts, and audit signal records.

### Technology Stack
- **Framework**: [React 19](file:///e:/Txbot/frontend/package.json)
- **Bundler & Dev Server**: [Vite 8](file:///e:/Txbot/frontend/vite.config.js)
- **Icons**: [Lucide React](file:///e:/Txbot/frontend/package.json)
- **Styling**: Modern CSS variables, glassmorphism, responsive grid layout, and dark-theme aesthetics ([`index.css`](file:///e:/Txbot/frontend/src/index.css)).
- **Sub-module Index**: Refer to [`frontend/src/components/CODE_INDEX_COMPONENTS.md`](file:///e:/Txbot/frontend/src/components/CODE_INDEX_COMPONENTS.md) for individual component details.

---

## 2. Directory & File Structure

```
frontend/
├── index.html                           # HTML entry point with meta tags & root mount
├── package.json                         # Node dependencies & Vite build scripts
├── vite.config.js                       # Vite configuration & /api proxy to FastAPI (:8000)
├── dist/                                # Precompiled production build (served by FastAPI)
└── src/
    ├── main.jsx                         # React DOM root render
    ├── App.jsx                          # Main shell, tab router, state sync, toast engine
    ├── App.css                          # App layout styling
    ├── index.css                        # Design tokens, color palette, animations
    ├── api.js                           # Centralized API service client (fetch wrapper)
    ├── assets/                          # Static logos and SVGs
    └── components/                      # UI modules (indexed in CODE_INDEX_COMPONENTS.md)
        ├── CODE_INDEX_COMPONENTS.md     # Component catalog index
        ├── Header.jsx                   # Market session header & global triggers
        ├── Sidebar.jsx                  # Navigation drawer
        ├── DashboardView.jsx            # KPI cards & command center
        ├── AlgoTradeView.jsx            # Strategy manager & backtest evaluator
        ├── MarketDataView.jsx           # Candle fetcher & chart comparison
        ├── AuditingView.jsx             # Strategy audit explorer & chart modals
        └── LoggingView.jsx              # Streaming live telemetry logs
```

---

## 3. Key Core Modules

### 3.1 [`api.js`](file:///e:/Txbot/frontend/src/api.js) — Central API Client
Provides type-safe, asynchronous methods for every backend endpoint:
```javascript
export const api = {
  getStatus: () => request('/status'),
  listAlgos: (params) => request('/algos...'),
  createAlgo: (data) => request('/algos', { method: 'POST', body: JSON.stringify(data) }),
  startAlgo: (id) => request(`/algos/${id}/start`, { method: 'POST' }),
  stopAlgo: (id) => request(`/algos/${id}/stop`, { method: 'POST' }),
  pauseAlgo: (id) => request(`/algos/${id}/pause`, { method: 'POST' }),
  copyAlgo: (id) => request(`/algos/${id}/copy`, { method: 'POST' }),
  deleteAlgo: (id, hard) => request(`/algos/${id}?hard=${hard}`, { method: 'DELETE' }),
  evaluateAlgo: (id, params) => request(`/algos/${id}/evaluate...`, { method: 'POST' }),
  runAllAlgos: () => request('/algos/run-all', { method: 'POST' }),
  listSignals: (params) => request('/signals...'),
  resendSignal: (id) => request(`/signals/${id}/resend`, { method: 'POST' }),
  getPnl: (algoId) => request('/pnl...'),
  fetchMarketData: (data) => request('/market/fetch', { method: 'POST', body: ... }),
  generateChart: (data) => request('/market/chart', { method: 'POST', body: ... }),
  compareCharts: (data) => request('/market/compare', { method: 'POST', body: ... }),
  getAudits: () => request('/audits'),
  getAuditDetail: (name) => request(`/audits/${name}`),
  getLogs: (params) => request('/logs...'),
};
```

### 3.2 [`App.jsx`](file:///e:/Txbot/frontend/src/App.jsx) — Application Shell & State
- **Polling Loop**: Automatically refreshes platform status, active strategies, PnL, and signals every 20 seconds.
- **Global Notification Engine**: Top-level toast alert system for success/error feedback.
- **Module Router**: Seamless tab switching between `dashboard`, `algotrade`, `market`, `auditing`, and `logging`.

---

## 4. UI Design System Tokens ([`index.css`](file:///e:/Txbot/frontend/src/index.css))

| Token | Hex / Value | Usage |
|---|---|---|
| `--bg-primary` | `#0b0f19` | Deep dark slate app background |
| `--bg-secondary` | `#111827` | Card and panel container background |
| `--bg-card` | `#1f2937` | Interactive card and table header background |
| `--accent-primary` | `#8b5cf6` | Primary violet brand and button highlight |
| `--bullish` | `#10b981` | Emerald green for CALL signals, wins, and positive PnL |
| `--bearish` | `#ef4444` | Crimson red for PUT signals, losses, and negative PnL |
| `--text-primary` | `#f9fafb` | Primary high-contrast text |
| `--text-muted` | `#9ca3af` | Secondary subtitle text |

---

## 5. Development & Build Commands

- **Start Dev Server**: `npm run dev` (Runs Vite on `http://localhost:5173` with proxy to `:8000`).
- **Production Build**: `npm run build` (Outputs bundle to [`frontend/dist/`](file:///e:/Txbot/frontend/dist) which is mounted directly by FastAPI).
- **Linter**: `npm run lint` (Runs Oxlint).

---

## 6. Token-Saving AI Guide

- When modifying API communication, inspect [`frontend/src/api.js`](file:///e:/Txbot/frontend/src/api.js).
- For individual view logic, consult [`frontend/src/components/CODE_INDEX_COMPONENTS.md`](file:///e:/Txbot/frontend/src/components/CODE_INDEX_COMPONENTS.md).
- Do not read large minified files in `frontend/dist/`.
