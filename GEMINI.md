# TxBot / AuraTrade Architecture & Development Rules

## 1. Flexible, Extensible Architecture (SOLID Principles)

The codebase is built for maximum maintainability and adaptability across global financial markets. We avoid rigid over-engineering while ensuring that adding new markets, providers, or strategies is seamless and low-friction.

### Core Design Principles:
- **Single Responsibility (SRP)**: Each service, adapter, model, and UI component must have one well-defined responsibility.
- **Open/Closed (OCP)**: Core pipeline orchestrators are closed for modification but open for extension via provider adapters, strategy plugins, and notification dispatchers.
- **Liskov Substitution (LSP)**: All data providers implement `BaseDataProvider`; all execution engines implement `BaseExecutionEngine`. Swapping implementations must never break the pipeline.
- **Interface Segregation (ISP)**: Prefer fine-grained, composable interfaces over monolithic base classes.
- **Dependency Inversion (DIP)**: High-level trading engines depend on abstractions and interfaces, with concrete implementations injected via configuration or factory registries.

### Market Modularity & Structure:
- **Universal Pipeline**: The standard execution sequence (Select → Fetch → Identify → Detect → Visualize → Analyze → Execute → Audit → Dispatch → Log) remains consistent across all markets.
- **Pragmatic Market Organization**:
  - Common, shared models and pure mathematical logic reside in core packages (`txcore/models/`, `txcore/analysis/`, etc.).
  - Market-specific extensions, exchange-specific adapters, custom holiday calendars, or unique routing logic MAY be organized either within provider adapters (`txcore/providers/`) or dedicated market packages if complexity warrants it.
  - Avoid tight coupling: Neither approach should hardcode assumptions that make future structural changes or adding new markets difficult.
- **Process Naming**: Internally referenced as **AlgoTrade** for table naming and architecture; users may name individual strategy configurations freely (e.g., "Ishaq strategy 1", "NiftyScalper").

---

## 2. Institutional Database Invariants & Audit Columns

### Mandatory Audit Columns for All Relevant Tables:
Every relevant database table across the entire codebase MUST include four standardized audit tracking columns:
1. `created_at` (`createdAt`): `DateTime @default(now())`
2. `updated_at` (`updatedAt`): `DateTime @updatedAt`
3. `created_by` (`createdBy`): `String? @default("SYSTEM")` (User ID, email, or "SYSTEM")
4. `updated_by` (`updatedBy`): `String? @default("SYSTEM")` (User ID, email, or "SYSTEM")

### Unified Candle Storage Architecture:
- Both historical and newly streaming candles MUST reside in a single unified table (`market_candles`).
- The `timestamp` of each candle naturally defines its historical vs. real-time nature.
- High-speed data retrieval is enforced using composite indexes on `(symbol, timeframe, timestamp DESC)`.

---

## 3. Development Lifecycle & Feature Execution Protocol (Mandatory)

### Phased Feature-by-Feature Delivery
- **NEVER implement an entire module in a single turn or bulk operation.**
- Every module must be broken down into discrete, numbered features (e.g., Feature 2.1, Feature 2.2).
- Before implementing ANY feature, the agent MUST:
  1. Conduct **Deep Research** of existing codebase structures, Prisma models, and legacy code (`txcore_legacy/`).
  2. Perform a **Gap Analysis** comparing existing implementations with target specifications.
  3. Map cross-module dependencies and shared interfaces (RBAC, MarketView, AlgoTrade, Paper Trading, Charts).
  4. Write a dedicated feature plan artifact (`feature_X_Y_plan.md`).

### Explicit User Consent Gate for Extra Features & Design Decisions
- **Before adding ANY extra feature, architectural extension, or unrequested capability, STOP AND ASK THE USER.**
- Present clear decision options with recommended defaults and concrete trade-offs.
- Do not make unilateral assumptions about external API choices, deletion vs. deactivation policies, storage locations, or UI layouts.

### Data Integrity & Precision Invariants
- **Zero Mock / Dummy Data**: Never use hardcoded synthetic mocks in production pipelines. All data must originate from real market providers (e.g., TradingView), live search APIs, or pre-seeded local database records.
- **Strict Asset Precision**:
  - Stocks & Indices: Exactly 4 decimal places (`0.0001`).
  - Crypto, Forex & Commodities: Exactly 6 decimal places (`0.000001`).
- **Explicit Verification Errors**: If an asset or ticker cannot be verified against live exchanges, return a clear, user-friendly error message rather than silently falling back to mock values.

### Documentation & Proof-of-Work Standards
- For each completed module, maintain both the master plan (`implementation_plan.md`) and the module plan (`module_X_plan.md`).
- Each feature must record:
  - Deliverables inventory (Backend files, Frontend components, Test suites).
  - Exactly **1-sentence summary** of what was achieved.
  - Exactly **1-sentence summary** of feedback work and bug resolutions.
- 100% automated test verification (`pytest` + `npm run build`) must pass before concluding any phase.

---

## 4. Code Index & AI Navigation Memory (Mandatory)

The codebase is indexed with specialized markdown code indexes to reduce token consumption and provide deep workflow and symbol maps.
**RULE FOR AI AGENTS**: Before reading or modifying source files in any layer or module, ALWAYS consult the relevant code index first to understand interfaces, function signatures, dependencies, and workflows without loading thousands of lines of raw source code into context.

### Code Index Registry:
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
- Database & ORM: `txcore/database.py` & `prisma/schema.prisma`
- Config Module Index: `config/CODE_INDEX_CONFIG.md`
- Frontend Repository Index: `frontend/CODE_INDEX_FRONTEND.md`
- Frontend Components Index: `frontend/src/components/CODE_INDEX_COMPONENTS.md`

### Maintenance Guarantee:
Whenever any module, service, strategy, or UI component is modified, added, or refactored:
1. Update that component's/module's `CODE_INDEX_<NAME>.md` with the new signatures, schemas, or behaviors.
2. Update `CODE_INDEX.md` (and the parent repository index) if higher-level architecture or endpoints changed.

---

## 5. Institutional UI Design, High-Contrast Forms & Zero-Black-Focus Invariants

### 5.1 Zero Black Boxes on Focus (Form Input Invariant):
- Every text input, select dropdown, and textarea across the platform MUST NEVER turn black, dark-grey, or invert upon receiving focus.
- Universal CSS in `frontend/src/index.css` strictly enforces transparent backgrounds and theme-inherited text for all input states:
  ```css
  .MuiInputBase-root, .MuiOutlinedInput-root,
  .MuiInputBase-root.Mui-focused, .MuiOutlinedInput-root.Mui-focused,
  .MuiInputBase-input:focus, .MuiOutlinedInput-input:focus {
    background: transparent !important;
    color: inherit !important;
    box-shadow: none !important;
    outline: none !important;
  }
  ```
- **Prohibition on Hardcoded Dark Backgrounds in Form Fields**: Never apply hardcoded dark backgrounds (e.g. `bgcolor: 'rgba(30, 41, 59, 0.6)'`) to individual `<TextField>` or `<Select>` elements inside modals or cards. Let them inherit the natural surface background of their parent container.

### 5.2 Adaptive Theme Surfaces & Zero White-on-White Text:
- Dialogs, cards, and notification panels MUST use adaptive theme tokens:
  - Surfaces: `bgcolor: 'background.paper'` or `bgcolor: 'var(--card-bg)'`.
  - Headings & Primary Text: `color: 'text.primary'` or `color: 'var(--text-main)'`.
  - Subtitles & Labels: `color: 'text.secondary'` or `color: 'var(--text-muted)'`.
- **High-Contrast Verification & Success Panels**: Success badges and confirmation cards must pair clear green icons with bold, high-contrast text (`color: 'text.primary'` and green labels `#059669`), never white text (`#f8fafc`) on light backgrounds.

### 5.3 Co-located Action Buttons:
- Primary submit actions (e.g. **Verify**, **Save**, **Submit**) and secondary cancel actions (**Cancel**, **Back**) MUST sit together on the same horizontal row with consistent spacing (`gap: 1.5` or `gap: 2`).

### 5.4 Compact Institutional Headers:
- Module view headers must remain compact, clean, and unobtrusive:
  - Header text size: `variant="h6"` or `variant="h5"` (maximum `1.25rem` - `1.5rem`), bold weight (`700`).
  - Eliminate verbose decorative subtitles, redundant module numbered chips (e.g. "Module 2"), and extraneous manual refresh buttons unless explicitly requested.

---

## 6. Frontend Design Framework: Institutional Financial Dashboard (Synthesized with Material UI)

Adapted from `frontend-design-framework.md` to work in full harmony with Material UI (MUI v6) and modern CSS:

### 6.1 Visual Atmosphere:
- The design conveys **technical reliability**, **precision**, and **quantitative control** (Bloomberg terminal / Power BI dashboard precision, refined for traders).
- Avoid gamified or casual social media aesthetics; prioritize low visual fatigue for extended trading sessions.

### 6.2 Institutional Color Palette & Material UI Tokens:
- **Primary Canvas Background:** `#121212` (or `--bg-primary`).
- **Card & Paper Surface:** `#1E1E1E` (MUI `<Card>`, `<Paper>`, Dialog Paper).
- **Subtle Structural Borders:** `#2C2C2E` (`1px solid #2C2C2E` for card perimeters, dividers, and table rows).
- **Primary Data Accent:** `#2563EB` (Deep Blue / Electric Sapphire) for charts, primary KPIs, active indicators, and primary action triggers.
- **Alert / Bearish Accent:** `#FF453A` (Institutional Red) for stop-losses, drawdowns, price drops, and risk alerts.
- **Live / Bullish / Success Accent:** `#32D74B` (Lime / Emerald Green) for live telemetry, winning trades, and normal system states.
- **Primary Text:** `#FFFFFF` (High contrast, crisp legibility).
- **Secondary Text:** `#98989D` (Neutral slate gray for labels, table headers, and metadata).

### 6.3 Material UI Component Specifications:
- **Cards & Papers (`<Card>`, `<Paper>`):**
  - Border radius: `16px` (`borderRadius: 2.5` or `borderRadius: 3`).
  - Background: `#1E1E1E` (in dark theme).
  - Internal padding: `20px` (`p: 2.5`).
  - Perimeter border: `1px solid #2C2C2E`.
  - Box shadow: `0 4px 20px rgba(0, 0, 0, 0.35)`.
- **Data Tables (`<Table>`, `<DataGrid>`):**
  - Row bottom border: `1px solid #2C2C2E`.
  - Row hover background: `#252525`.
  - Table headers: Uppercase, bold (`0.75rem`), text `#98989D`.
- **Alerts (`<Alert>`):**
  - Error: Background `#3A1C1C`, text `#FF453A`, left accent border `4px solid #FF453A`.
  - Success: Background `#1C3A24`, text `#32D74B`, left accent border `4px solid #32D74B`.
- **Charts & Financial Curves:**
  - Grid lines: `#2C2C2E`.
  - Area gradients: `#2563EB` (Deep Blue) and `#32D74B` (Green) fills with zero heavy borders.

### 6.4 Typography Hierarchy:
- **Headings & Titles:** Plus Jakarta Sans / Inter, Semi-Bold (`600` - `700`), `20px` - `24px`.
- **Financial Figures & Numerical Data (Prices, PnL, Decimals, Lot Sizes, Tickers):**
  - Strictly **JetBrains Mono** or monospace font (`tabular-nums`), bold (`700` - `800`), `28px` - `32px` for hero metrics.
- **Body & Metadata Copy:** Regular (`400`), `14px` (`0.875rem`).

### 6.5 Layout & Grid Rules:
- **12-Column Responsive Grid** (`<Grid container columns={12}>`).
- **8px Spacing Cadence**: Spacing values must strictly follow multiples of 8px (`8px`, `16px`, `24px`, `32px`).
- **High-Density Dashboard Structure**: Top KPI row (3 or 4 columns), main chart or table (8 columns), live event/alert rail (4 columns).

### 6.6 Design Invariants (Do's and Don'ts):
- ✅ **Do:** Always render financial numbers, asset symbols, lot sizes, and precision decimals in monospace fonts.
- ✅ **Do:** Co-locate primary action buttons with secondary actions on the same horizontal row.
- ❌ **Don't:** Use washed-out pastel colors or harsh blinding white card backgrounds in dark-mode trading screens.
- ❌ **Don't:** Use decorative or generic clipart icons; prefer sharp, domain-specific Lucide/MUI icons.

---

## 7. Institutional Soft-Delete & Zero Data Loss Policy

To maintain complete historical audit trails, time-series continuity, and financial compliance across all platform modules:

### 7.1 Mandatory Soft-Delete Fields on Managed Entities:
- Managed financial entities (e.g. `MarketSymbol`, strategies, user configurations) MUST include:
  - `isDeleted` (`is_deleted`): `Boolean @default(false)`
  - `deletedAt` (`deleted_at`): `DateTime?`
  - Standard institutional audit columns (`createdAt`, `updatedAt`, `createdBy`, `updatedBy`).

### 7.2 Zero Data Loss Invariant:
- Hard deletion (`DELETE FROM ...`) of catalog assets or registered tickers is **strictly prohibited**.
- When an asset is deleted by an operator or user:
  1. The record is flagged as soft-deleted: `isDeleted = true`, `isActive = false`, `deletedAt = now()`, `updatedBy = current_user.email`.
  2. **Zero Cascade / Zero Data Deletion**: None of the associated data — including historical and live OHLCV bars in `market_candles`, event trigger histories, telemetry logs, or audit records — may be deleted or modified.

### 7.3 Re-Add & Re-Activation Semantics:
- If a user re-adds an asset that was previously soft-deleted:
  1. The existing record MUST be restored and updated rather than rejected with `409 Conflict`.
  2. Set `isDeleted = false`, `isActive = true`, `deletedAt = null`, update any refreshed metadata (e.g. lot size, tick size, description, group ID), and record `updatedBy = current_user.email`.
  3. Attempting to add an asset that is currently active (`isDeleted = false`) will raise standard `409 Conflict`.

### 7.4 Query Filtering Invariant:
- All platform catalog listings, selector dropdowns, active market scanners, and lookups MUST filter out soft-deleted assets by default (`where: { isDeleted: false }`).

---

## 8. Global Chart Ecosystem & Diagnostic Telemetry Invariants

### 8.1 Universal Live Polling & Streaming:
- Every interactive chart across all modules (including **MarketView**, **Side-by-Side Dual Comparison**, **Signal Preview Modals**, **Backtest Walk-Forward Evaluators**, and **Audit Verification Charts**) MUST support live tick/candle synchronization.
- When market sessions are active or Live Stream mode is toggled ON, charts must poll or stream delta updates (1s–5s intervals) to reflect live exchange price discovery.

### 8.2 Standardized Chart Diagnostic Data Footer:
- Every chart canvas MUST include a standardized monospace diagnostic metadata bar directly below the canvas showing:
  - Data Fetch Latency (`X.XXXs Data`)
  - Canvas Render Latency (`X.XXXs Chart`)
  - Total Pipeline Latency (`X.XXXs Total`)
  - Bar Count (`N bars`)
  - Data Provider / Exchange Source (`PROVIDER`)
- Format: `Diagnostic: 0.120s Data | 0.045s Chart | 0.165s Total (180 bars • TRADINGVIEW)`

---

## 9. Advanced Navigation Drawer Standards (Material UI Enhanced)

### 9.1 Hamburger Toggle & Centered Brand Header:
- The navigation drawer header MUST feature a centered platform title (`AuraTrade`) paired with a hamburger or collapse icon button (`Menu`, `ChevronLeft`/`ChevronRight`, `PanelLeftClose`).
- Expanding and collapsing must transition smoothly (`0.2s cubic-bezier(0.4, 0, 0.2, 1)`).

### 9.2 Collapsible State Specifications:
- **Expanded Mode**: Compact 60% width (`~165px`), centered brand title, category labels, and numeric badges.
- **Collapsed Mode**: Icon-only footprint (`~60px`), centered icons, indicator dots for active badges, and Material-UI `<Tooltip>` popovers displaying the full module title on hover.
- **State Persistence**: The collapse state MUST be remembered in `localStorage` across page reloads.


