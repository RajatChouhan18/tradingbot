# TxBot Architecture Rules

## Market-Agnostic Pipeline Architecture

This trading bot uses a **universal, market-agnostic pipeline** where the same modules and data flow work for ALL markets. Market-specific details are injected via configuration and provider adapters.

**DO NOT** create separate folders or packages per market (e.g., `indian_market/`, `forex/`, `crypto/`).

- Internally the process should be called **AlgoTrade** for table naming and architecture, but the user should be able to name his process (e.g., "Ishaq strategy 1", "Ishaq strategy 2", etc.).

**DO** follow this universal pipeline structure:

1. **Select** — Market, timeframe, symbols, indicators, patterns, strategy, VIX or other indicators, Index data, volume, RSI etc. (via config), chart options, auditing.
2. **Fetch** — Data from any market via injectable `BaseDataProvider` subclasses. Save computation by fetching precalculated data directly from the DataProvider where available.
3. **Identify** — Parallel/async extraction of candles, VIX, OI, index movement, volume, moving averages, and indicators. Precalculate anything possible and error-free.
4. **Detect** — Parallel pattern recognition and indicator applications chosen at Step 1.
5. **Visualization** — Execute a parallel/asynchronous background pipeline for creating charts without blocking the trading loop.
6. **Analyze** — Fast multi-factor analysis (VIX, index movement, indicators, patterns, candles).
7. **Execute** — Apply the configured strategy for evaluating the final signal (CALL/PUT) with key levels, stop loss, target, timeframe to execute the trade.
8. **Audit** — Execute a parallel auditing pipeline that audits data, patterns, charts, SR levels, key levels, strategy, Analysis, PnL; generate audit visualization charts (timeframe of fetched data + trade duration).
9. **Dispatch** — Send signal and attachments asynchronously to configured channels (Telegram, WhatsApp, email, webhooks, etc.).
10. **Logging** — Asynchronous non-blocking logging of entire footprints for instant trace and retrieval.

## High-Performance & Concurrency Requirements

- **Computation Saving**: Precalculate reusable indicators, cache rolling calculations, and fetch enriched aggregates directly from providers.
- **Parallel / Async Execution**: MUST launch parallel/async workers for pattern identification, indicator computations, chart visualization, symbol batch scans, and auditing so that signal discovery and dispatch latency is minimized.
- **Non-Blocking Output**: Visualization rendering, file logging, and network dispatches must never block the core signal evaluation cycle.

## Module Structure (Common for All Markets)

The `txcore/` package follows this structure where each module is market-agnostic:

| Module | Purpose |
|--------|---------|
| `txcore/providers/` | Data providers (`BaseDataProvider` subclasses — TradingView, NSE, Zerodha, etc.) |
| `txcore/models/` | Domain models, types, enums (shared across all markets) |
| `txcore/analysis/` | Candle classification, levels, indicators, pattern detection (vectorized & pure functions) |
| `txcore/strategies/` | Strategy engines (`BaseStrategy` subclasses) |
| `txcore/execution/` | Signal dispatchers (`BaseNotifier` subclasses — Telegram, Discord, etc.) |
| `txcore/visualization/` | Async/parallel chart generation (works with any market's data) |
| `txcore/audit/` | Deduplication, auditing, delivery tracking, parallel audit pipeline |
| `txcore/filters/` | Safety filters (news, volatility, etc.) |
| `config/` | Environment config, market-specific watchlists, and provider settings |

## Naming Conventions

- Module and variable names must use **market nomenclature** (e.g., "candle", "bar", "signal", "level", not generic CS terms).
- New providers go into `txcore/providers/` (e.g., `nse_provider.py`, `zerodha_provider.py`).
- New strategies go into `txcore/strategies/`.
- Market-specific constants/watchlists go into `config/settings.py`.
- If a new structural folder is needed, it must be created for ALL markets, not just one.

## AlgoTrade Process Model

Each running pipeline instance is called an **AlgoTrade** with:
- A user-defined name (e.g., "Ishaq strategy 1", "NiftyScalper")
- A unique collision-resistant ID (e.g., `AT-IshaqStrategy1-20260927-1234AB`)
- Full configuration (`AlgoTradeConfig`: market, symbols, strategy, indicators, patterns, endpoints)
- Ability to spin up multiple AlgoTrade processes concurrently and monitor them independently
- Parallel multi-symbol scanning engine with non-blocking audit & dispatch

## Code Index & AI Navigation Memory (Mandatory)

The codebase is indexed with specialized markdown code indexes to reduce token consumption and provide deep workflow and symbol maps.
**RULE FOR AI AGENTS**: Before reading or modifying source files in any layer or module, ALWAYS consult the relevant code index first to understand interfaces, function signatures, dependencies, and workflows without loading thousands of lines of raw source code into context.

### Code Index Registry
- Master Root Index: `CODE_INDEX.md`
- Backend Core Index: `txcore/CODE_INDEX_TXCORE.md`
- Services Layer Index: `txcore/CODE_INDEX_SERVICES.md`
- AlgoTrade Orchestrator Index: `txcore/CODE_INDEX_ALGOTRADE.md`
- Models Module Index: `txcore/models/CODE_INDEX_MODELS.md`
- Analysis Module Index: `txcore/analysis/CODE_INDEX_ANALYSIS.md`
- Providers Module Index: `txcore/providers/CODE_INDEX_PROVIDERS.md`
- Strategies Module Index: `txcore/strategies/CODE_INDEX_STRATEGIES.md`
- Visualization Module Index: `txcore/visualization/CODE_INDEX_VISUALIZATION.md`
- Audit Module Index: `txcore/audit/CODE_INDEX_AUDIT.md`
- Execution Module Index: `txcore/execution/CODE_INDEX_EXECUTION.md`
- Filters Module Index: `txcore/filters/CODE_INDEX_FILTERS.md`
- Config Module Index: `config/CODE_INDEX_CONFIG.md`
- Frontend Repository Index: `frontend/CODE_INDEX_FRONTEND.md`
- Frontend Components Index: `frontend/src/components/CODE_INDEX_COMPONENTS.md`

### Maintenance Guarantee
Whenever any module, service, strategy, or UI component is modified, added, or refactored:
1. Update that component's/module's `CODE_INDEX_<NAME>.md` with the new signatures, schemas, or behaviors.
2. Update `CODE_INDEX.md` (and the parent repository index) if higher-level architecture or endpoints changed.

