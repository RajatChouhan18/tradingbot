# AuraTrade Code Index: Backend Core Repository (`txcore`)

> **Repository Identifier**: `txcore` (Backend)  
> **Index Suffix**: `TXCORE` / `BACKEND`  
> **Source Directory**: [`txcore/`](file:///e:/Txbot/txcore)  
> **Legacy Reference**: [`txcore_legacy/`](file:///e:/Txbot/txcore_legacy)  
> **Role**: Institutional Ecosystem to Monitor Paper Trades, Strategies, and Portfolio Performance.

---

## 1. Backend Architecture & High-Performance Design

The `txcore` package forms the modular backend of **AuraTrade**. It is architected strictly under the **Market-Agnostic Pipeline** philosophy: every algorithm, data model, indicator, strategy, visualization, and audit workflow works identically across all asset classes (Forex, Indian Equities/F&O, Commodities, Crypto).

### Architecture Highlights
- **Application Core**: AuraTrade v2.0.0.
- **Reference Preservation**: All legacy implementations of data providers, technical indicators, pattern detectors, and strategies are preserved untouched in [`txcore_legacy/`](file:///e:/Txbot/txcore_legacy/).
- **Feature-by-Feature Incremental Delivery**: Modules are developed feature-by-feature with deep research and cross-module gap analysis before implementation.
- **Strict Decimal Precision**: Python `decimal.Decimal` enforcing 4 decimal places for stocks (`0.0001`) and 6 decimal places for crypto/forex/commodities (`0.000001`).
- **Incremental Processing**: 180 past candles cached; ONLY new incoming candles evaluated with O(1) rolling indicator accumulators.

---

## 2. Backend Modular Structure

| Module | Package Directory | Purpose & Responsibilities |
|---|---|---|
| **Module 1: User & Roles** | [`txcore/auth`](file:///e:/Txbot/txcore/auth) | User authentication, PBKDF2/bcrypt, DB-stored session tokens, dynamic role permission matrix, virtual cash management. |
| **Module 2: Market Catalog** | [`txcore/catalog`](file:///e:/Txbot/txcore/catalog) ([Index](file:///e:/Txbot/txcore/catalog/CODE_INDEX_CATALOG.md)) | Pre-seeded benchmarks, TradingView live verification, unified `market_candles` storage, audit columns, precision rules. |
| **Module 3: MarketView** | [`txcore/marketview`](file:///e:/Txbot/txcore/marketview) ([Index](file:///e:/Txbot/txcore/marketview/CODE_INDEX_MARKETVIEW.md)) | Data provider layer, fastest free live data engine, market-closed detection/overlay, optional indicator/OI/VIX overlays, zero-recalculation cache. |
| **Module 4: Event Triggers** | [`txcore/events`](file:///e:/Txbot/txcore/events) | Standalone named watchers on single assets, pattern/spike/SR/indicator rules, Telegram & WhatsApp dispatchers (no trade execution). |
| **Module 5: AlgoTrade** | [`txcore/algotrade`](file:///e:/Txbot/txcore/algotrade) | Composite triggers, configurable predefined strategies (PDF Price Action), multi-leg trade execution orchestration, aggregate scorecard, safe cascading deletion. |
| **Module 6: Paper Trading** | [`txcore/paper`](file:///e:/Txbot/txcore/paper) | Multi-leg & standalone paper trades, complete evaluation matrix (PnL, ROI, MFE, MAE), zero-RAM risk manager in PostgreSQL, full lifecycle charts with post-exit `<x>` slider. |
| **Module 7: Visualization** | [`txcore/visualization`](file:///e:/Txbot/txcore/visualization) | Pure data-driven candlestick canvas, pre-render diagnostic timing banner, progressive rendering pipeline. |
| **Module 8: Test Workbench** | [`txcore/test_engine`](file:///e:/Txbot/txcore/test_engine) | Native async test runner with isolated DB transactions, real-world loophole test suite, custom scenario builder, side-by-side visual diffs. |
| **Database & ORM** | [`txcore/database.py`](file:///e:/Txbot/txcore/database.py) | Prisma ORM async client lifecycle and connection manager. |
