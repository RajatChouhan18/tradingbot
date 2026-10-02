# TxBot Code Index: Frontend Repository (`frontend`)

> **Index Identifier**: `frontend`  
> **Index Suffix**: `FRONTEND`  
> **Source Directory**: [`frontend/`](file:///e:/Txbot/frontend)  
> **Role**: React 19 Single Page Application (SPA), user interface, trading command center, multi-theme engine, and interactive visualization client.

---

## 1. Overview & Technology Stack

The `frontend` application is an ultra-fast, modern trading dashboard built for non-technical users and quantitative operators. It connects to the FastAPI backend service to manage algorithmic trading strategies, view live market data, inspect interactive TradingView charts, route paper and broker orders, and audit signal records.

### Technology Stack
- **Framework**: [React 19](file:///e:/Txbot/frontend/package.json)
- **Bundler & Dev Server**: [Vite 8](file:///e:/Txbot/frontend/vite.config.js)
- **Icons**: [Lucide React](file:///e:/Txbot/frontend/package.json)
- **State & Theming**: [`ThemeContext.jsx`](file:///e:/Txbot/frontend/src/ThemeContext.jsx) providing persistent theme switching between `obsidian` (Institutional Dark) and `enterprise` (NOSSA Corporate Navy & Light Slate).
- **Styling**: Modern CSS variables, glassmorphism, responsive grid layout, and multi-theme design tokens ([`index.css`](file:///e:/Txbot/frontend/src/index.css)).
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
    ├── main.jsx                         # React DOM root render wrapped with ThemeProvider
    ├── App.jsx                          # Main shell, tab router, state sync, toast engine
    ├── App.css                          # App layout styling
    ├── index.css                        # Multi-theme design tokens (Obsidian vs Enterprise)
    ├── ThemeContext.jsx                 # Theme state context & localStorage persistence
    ├── api.js                           # Centralized API service client (fetch wrapper)
    ├── assets/                          # Static logos and SVGs
    └── components/                      # UI modules (indexed in CODE_INDEX_COMPONENTS.md)
        ├── CODE_INDEX_COMPONENTS.md     # Component catalog index
        ├── Header.jsx                   # Market session header, telemetry, and quick theme toggle
        ├── Sidebar.jsx                  # Navigation drawer with theme-adaptive styles
        ├── ThemeSettingsModal.jsx       # Theme switcher dialog with interactive visual previews
        ├── DashboardView.jsx            # KPI cards & command center
        ├── AlgoTradeView.jsx            # Strategy manager & backtest evaluator
        ├── PaperTradingView.jsx         # Paper trading & broker execution engine
        ├── MarketCatalogSelector.jsx    # Institutional market group & symbol multi-select
        ├── MarketDataView.jsx           # Candle fetcher & chart comparison
        ├── AuditingView.jsx             # Strategy audit explorer & chart modals
        ├── LoggingView.jsx              # Streaming live telemetry logs
        ├── catalog/                     # Market Catalog Module (Module 2)
        │   ├── MarketCatalogScreen.jsx  # Multi-market catalog directory & table
        │   └── AddAssetModal.jsx        # Live TradingView search & verification modal
        └── admin/                       # User & Role Administration (Module 1)
            ├── UserManagementScreen.jsx # Users, roles, cash top-ups, permissions
            ├── CreateUserModal.jsx      # New user modal
            ├── CreateRoleModal.jsx      # Role builder modal
            └── CashTopupModal.jsx       # Balance adjustment modal
```

---

## 3. Key Core Modules

### 3.1 [`ThemeContext.jsx`](file:///e:/Txbot/frontend/src/ThemeContext.jsx) — Theme Management
Provides persistent multi-theme capabilities across the whole SPA:
- `theme`: `'obsidian'` | `'enterprise'`
- `setTheme(themeId)`: Sets active theme and persists to `localStorage.setItem('txbot_theme', themeId)`.
- `toggleTheme()`: Instant toggle between Obsidian Dark and Enterprise Portal.
- `themes`: Theme metadata list with color swatches and descriptive badges.
- `isThemeModalOpen`, `setIsThemeModalOpen`: Global modal control.
- Automatically synchronizes `<html data-theme="...">` and `<body data-theme="...">` attributes.

### 3.2 [`api.js`](file:///e:/Txbot/frontend/src/api.js) — Central API Client
Provides type-safe, asynchronous methods for every backend endpoint:
```javascript
export const api = {
  getStatus: () => request('/status'),
  getCatalogGroups: () => request('/catalog/groups'),
  getCatalogSymbols: (params) => request('/catalog/symbols...'),
  getCatalogMarkets: () => request('/catalog/markets'),
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
  getConcurrency: () => request('/concurrency'),
  getPaperPortfolio: () => request('/paper/portfolio'),
  getPaperPositions: () => request('/paper/positions'),
  getRiskStatus: () => request('/paper/risk/status'),
  getBrokers: () => request('/paper/brokers'),
};

// SSE Telemetry Streaming Client
export function connectTelemetryStream({ onConnected, onHeartbeat, onCycleUpdate, onSignalAlert, onLogEvent, onError, onOpen });
```

---

## 4. UI Design System Tokens ([`index.css`](file:///e:/Txbot/frontend/src/index.css))

### Theme 1: `obsidian` (Institutional Fintech Dark)
| Token | Hex / Value | Usage |
|---|---|---|
| `--bg-primary` | `#0a0d14` | Onyx black application canvas |
| `--bg-card` | `#131927` | Deep slate card and panel background |
| `--accent` | `#2563eb` | Electric blue primary action highlight |
| `--bullish` | `#00c087` | Neon emerald for CALL signals, wins, positive PnL |
| `--bearish` | `#f43f5e` | Neon rose for PUT signals, losses, negative PnL |
| `--text-main` | `#f1f5f9` | Primary high-contrast text |
| `--text-muted` | `#94a3b8` | Cool slate subtitle text |

### Theme 2: `enterprise` (NOSSA Seguros Portal Design System)
| Token | Hex / Value | Usage |
|---|---|---|
| `--bg-primary` | `#EBEEF2` | Clean neutral slate-gray background |
| `--bg-card` | `#FFFFFF` | Crisp white cards with 1px `#D5D8DC` borders |
| `--accent` | `#1B3A6B` | Deep Portuguese corporate navy header & buttons |
| `--bullish` | `#82B440` | Signature olive lime green for CALL signals & active state |
| `--bullish-dim` | `#EFF5E6` | Soft tinted green background for pill badges |
| `--bearish` | `#C0392B` | Crimson red for PUT signals & stops |
| `--bearish-dim` | `#FDEDEC` | Soft tinted red background for danger badges |
| `--warning` | `#E67E22` | Amber orange for pending/paused states |
| `--text-main` | `#1A1A2E` | Deep charcoal-navy primary text |
| `--text-muted` | `#5D6D7E` | Corporate mid-slate subtitle text |

---

## 5. Development & Build Commands

- **Start Dev Server**: `npm run dev` (Runs Vite on `http://localhost:5173` with proxy to `:8000`).
- **Production Build**: `npm run build` (Outputs bundle to [`frontend/dist/`](file:///e:/Txbot/frontend/dist) which is mounted directly by FastAPI).
- **Linter**: `npm run lint` (Runs Oxlint).
