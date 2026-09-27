# TxBot Code Index: Services Layer (`txcore/services`)

> **Index Identifier**: `txcore/services`  
> **Index Suffix**: `SERVICES`  
> **Source Files**: [`txcore/service.py`](file:///e:/Txbot/txcore/service.py), [`run_server.py`](file:///e:/Txbot/run_server.py), [`run_algotrade.py`](file:///e:/Txbot/run_algotrade.py)  
> **Role**: RESTful API Service layer, background auto-scheduler, WebSocket/HTTP server lifecycle, and runtime process controllers.

---

## 1. Services Overview & Responsibilities

The Services layer exposes the high-performance core engine to non-technical users via a modern REST API (FastAPI) and automated background scheduling workers.

### Key Responsibilities
- **FastAPI HTTP Service**: Asynchronous REST API serving strategy controls, real-time market telemetry, signal feeds, chart rendering, and audit histories.
- **Automated Scheduling Worker**: Background thread (`_scheduler_worker`) checking user-specified `start_time` and `stop_time` against IST exchange hours every 30 seconds.
- **Static Assets Serving**: Mounts `/charts` and `/exports` to serve standalone TradingView HTML charts directly into browser iframes.
- **Production Server Runners**:
  - [`run_server.py`](file:///e:/Txbot/run_server.py): Launches Uvicorn server (`0.0.0.0:8000`).
  - [`run_algotrade.py`](file:///e:/Txbot/run_algotrade.py): Headless terminal runner executing continuous multi-symbol scanning cycles.

---

## 2. API Endpoints Catalog

### 2.1 System & Telemetry Endpoints

| Method | Endpoint | Query / Body Params | Returns | Description |
|---|---|---|---|---|
| `GET` | [`/api/status`](file:///e:/Txbot/txcore/service.py#L239-L280) | None | System status, session info, India VIX regime, market breadth ADR, active algos count. | Real-time health check and live market status. |

### 2.2 AlgoTrade Strategy Management

| Method | Endpoint | Request Body | Description |
|---|---|---|---|
| `GET` | [`/api/algos`](file:///e:/Txbot/txcore/service.py#L286-L295) | `status`, `creator`, `include_deleted` | Lists all registered AlgoTrades with live metrics (win rate %, PnL %, cycle count). |
| `POST` | [`/api/algos`](file:///e:/Txbot/txcore/service.py#L297-L331) | `CreateAlgoRequest` JSON | Creates and registers a new AlgoTrade instance. |
| `GET` | [`/api/algos/{algo_id}`](file:///e:/Txbot/txcore/service.py#L333-L343) | None | Detailed view with configuration, signal history, and PnL trades. |
| `POST` | [`/api/algos/{algo_id}/start`](file:///e:/Txbot/txcore/service.py#L345-L360) | None | Starts strategy and triggers one immediate parallel scan cycle. |
| `POST` | [`/api/algos/{algo_id}/stop`](file:///e:/Txbot/txcore/service.py#L362-L369) | None | Sets status to STOPPED. |
| `POST` | [`/api/algos/{algo_id}/pause`](file:///e:/Txbot/txcore/service.py#L371-L378) | None | Sets status to PAUSED (skips scheduler triggers). |
| `POST` | [`/api/algos/{algo_id}/copy`](file:///e:/Txbot/txcore/service.py#L380-L391) | None | Duplicates configuration under a new collision-resistant ID. |
| `DELETE` | [`/api/algos/{algo_id}`](file:///e:/Txbot/txcore/service.py#L393-L400) | `hard: bool = False` | Soft-deletes (or purges) strategy from manager. |
| `POST` | [`/api/algos/{algo_id}/evaluate`](file:///e:/Txbot/txcore/service.py#L402-L450) | `start_date`, `end_date` | Runs walk-forward historical backtest and returns per-symbol `StrategyEvaluationReport`. |
| `POST` | [`/api/algos/run-all`](file:///e:/Txbot/txcore/service.py#L453-L458) | None | Concurrently triggers one scan cycle across all RUNNING strategies. |

### 2.3 Signals & PnL Analytics

| Method | Endpoint | Query Params | Description |
|---|---|---|---|
| `GET` | [`/api/signals`](file:///e:/Txbot/txcore/service.py#L464-L481) | `algo_id`, `symbol`, `direction` | Retrieves generated signals with converted chart URLs. |
| `GET` | [`/api/signals/{signal_id}`](file:///e:/Txbot/txcore/service.py#L483-L497) | None | Detailed signal inspection with execution chart and +30 candle audit chart URLs. |
| `POST` | [`/api/signals/{signal_id}/resend`](file:///e:/Txbot/txcore/service.py#L499-L527) | None | Re-dispatches alert text and chart to configured Telegram endpoints. |
| `GET` | [`/api/pnl`](file:///e:/Txbot/txcore/service.py#L529-L533) | `algo_id` (optional) | Consolidated win/loss stats, total points, total PnL %. |

### 2.4 Market Data Layer

| Method | Endpoint | Request Body | Description |
|---|---|---|---|
| `POST` | [`/api/market/fetch`](file:///e:/Txbot/txcore/service.py#L539-L597) | `MarketDataFetchRequest` | Ingests candles, analyzes trend, stores query footprint in history. |
| `GET` | [`/api/market/history`](file:///e:/Txbot/txcore/service.py#L599-L603) | None | Returns recent saved market data queries. |
| `POST` | [`/api/market/chart`](file:///e:/Txbot/txcore/service.py#L605-L637) | `MarketDataFetchRequest` | Generates on-demand interactive HTML chart and returns its URL. |
| `POST` | [`/api/market/compare`](file:///e:/Txbot/txcore/service.py#L639-L667) | `CompareRequest` | Dual dataset fetch and chart URLs for side-by-side comparison. |

### 2.5 Auditing & Logs

| Method | Endpoint | Query / Body Params | Description |
|---|---|---|---|
| `GET` | [`/api/audits`](file:///e:/Txbot/txcore/service.py#L673-L693) | None | Lists audit records grouped by AlgoTrade name. |
| `GET` | [`/api/audits/{algo_name}`](file:///e:/Txbot/txcore/service.py#L695-L720) | None | Detailed audit view with signals history, audit charts, and error logs. |
| `GET` | [`/api/logs`](file:///e:/Txbot/txcore/service.py#L725-L755) | `source: market|signals|delivery|all`, `search`, `limit` | Live log lines streamed from log files with error flags. |

---

## 3. Background Services & Daemons

### 3.1 [`_scheduler_worker()`](file:///e:/Txbot/txcore/service.py#L127-L159)
- Runs as a daemon thread initialized on FastAPI startup.
- Loops every 30 seconds.
- Checks local IST time against `algo.config.start_time` and `algo.config.stop_time`.
- Auto-starts strategies at `start_time` and auto-stops them at `stop_time`.

### 3.2 [`seed_default_algos()`](file:///e:/Txbot/txcore/service.py#L69-L120)
Seeds 3 sample strategies into the runtime manager on startup if no strategies are present:
1. **Ishaq Strategy 1**: Bluechip equities (`RELIANCE`, `TCS`, `HDFCBANK`) on 5m timeframe.
2. **Nifty Scalper**: Benchmark indices (`NIFTY`, `BANKNIFTY`) on 5m timeframe.
3. **Forex Price Action**: Major currency pairs (`EUR/USD`, `GBP/USD`, `USD/JPY`) on 15m timeframe.

---

## 4. Service Architecture & Network Topology

```mermaid
graph TD
    Client[Web Browser / React Frontend] -->|HTTP REST / Static| FastAPI[FastAPI Server :8000]
    
    subgraph FastAPI Runtime
        FastAPI --> Endpoints[API Route Handlers]
        Endpoints --> Manager[AlgoTradeManager]
        Endpoints --> StaticCharts[Static Mount: /charts]
        Endpoints --> StaticDist[Static Mount: / (Frontend Build)]
        Scheduler[_scheduler_worker Thread: 30s Loop] --> Manager
    end
    
    subgraph Core Engine Execution
        Manager --> Algo1[AlgoTrade 1: Nifty Scalper]
        Manager --> Algo2[AlgoTrade 2: Ishaq Strategy 1]
        Manager --> AlgoN[AlgoTrade N: ...]
    end
```

---

## 5. Token-Saving AI Guide

- To add or modify REST endpoints, edit [`txcore/service.py`](file:///e:/Txbot/txcore/service.py).
- To launch the server programmatically or in test, run `python run_server.py`.
- Static charts are accessible at `http://localhost:8000/charts/{filename}`.
- All endpoints return standard JSON objects with CORS headers enabled for all origins.
