# AuraTrade Code Index: Market Catalog & Asset Directory (`txcore/catalog`)

> **Module**: Module 2: Market Catalog & Asset Directory  
> **Source Directory**: [`txcore/catalog/`](file:///e:/Txbot/txcore/catalog)  
> **Primary Schema**: [`prisma/schema.prisma`](file:///e:/Txbot/prisma/schema.prisma) (`MarketGroup`, `MarketSymbol`, `MarketCandle`)  
> **Test Suites**:
> - [`tests/test_feature_2_1_schema.py`](file:///e:/Txbot/tests/test_feature_2_1_schema.py) (100% Pass)
> - [`tests/test_feature_2_2_seeder.py`](file:///e:/Txbot/tests/test_feature_2_2_seeder.py) (100% Pass)
> - [`tests/test_feature_2_3_verifier.py`](file:///e:/Txbot/tests/test_feature_2_3_verifier.py) (100% Pass)
> - [`tests/test_feature_2_4_historical.py`](file:///e:/Txbot/tests/test_feature_2_4_historical.py) (100% Pass)

---

## 1. Database Invariants & Schema Models

### `MarketGroup` (Table: `market_groups`)
- `id`: String (UUID PK)
- `groupId`: String (Unique, e.g. `NSE`, `BSE`, `US_EQUITY`, `FOREX`, `CRYPTO`, `MCX`)
- `name`: String
- `market`: String (`INDIAN_EQUITY`, `US_EQUITY`, `FOREX`, `CRYPTO`, `MCX`)
- `description`: String?
- `createdAt`, `updatedAt`, `createdBy`, `updatedBy`: Mandatory institutional audit tracking.

### `MarketSymbol` (Table: `market_symbols`)
- `id`: String (UUID PK)
- `symbol`: String (Unique canonical ticker e.g. `RELIANCE`, `AAPL`, `BTCUSDT`)
- `shortName`: String
- `fullName`: String
- `market`: String
- `exchange`: String
- `assetType`: String (`STOCK`, `INDEX`, `FOREX`, `CRYPTO`, `COMMODITY`)
- `sector`: String?
- `indexGroup`: String?
- `decimalPlaces`: Int (Strict: 4 for stocks/indices, 6 for crypto/forex/commodities)
- `groupId`: String? (FK to `market_groups.groupId`)
- `lotSize`: Int (Default 1)
- `tickSize`: Float (Default 0.05)
- `tvSymbol`: String? (TradingView search format e.g. `NSE:RELIANCE`)
- `isPreseeded`: Boolean (Identifies benchmark symbols; can be deleted or toggled)
- `isActive`: Boolean (Active status toggle)
- `isDeleted`: Boolean (Institutional soft-delete flag, default `false`)
- `deletedAt`: DateTime? (Timestamp of soft-deletion)
- `createdAt`, `updatedAt`, `createdBy`, `updatedBy`: Mandatory institutional audit tracking.
- `@@index([market, isActive, isDeleted])`, `@@index([groupId, isActive, isDeleted])`

### `MarketCandle` (Table: `market_candles`)
Unified high-performance candlestick storage for **both** historical and streaming live candles.
- `id`: String (UUID PK)
- `symbol`: String
- `timeframe`: String (`1m`, `5m`, `15m`, `1h`, `1d`)
- `timestamp`: DateTime (Defines historical factor chronologically)
- `open`, `high`, `low`, `close`: Float
- `volume`: Float (Default 0.0)
- `createdAt`, `updatedAt`, `createdBy`, `updatedBy`: Mandatory audit tracking.
- `@@unique([symbol, timeframe, timestamp])`: Prevents duplicate bars.
- `@@index([symbol, timeframe, timestamp(sort: Desc)])`: Optimized for sub-millisecond historical lookbacks.

---

## 2. API Endpoints (`txcore/catalog/router.py`)
Mounted under both `/api/catalog` and `/catalog`:
- `GET /catalog/groups` — List market groups with active symbol counts (requires `CATALOG:view`).
- `GET /catalog/symbols` — Filter catalog by group, market, assetType, search query with pagination; excludes `isDeleted=true` by default (requires `CATALOG:view`).
- `GET /catalog/search` — Live real-time TradingView Symbol Search across global markets (requires `CATALOG:view`).
- `POST /catalog/verify` — Verifies asset existence on TradingView; returns auto-detected precision and metadata or explicit error (requires `CATALOG:view`).
- `POST /catalog/add` — Adds verified asset to database or reactivates soft-deleted asset with audit tracking (`createdBy/updatedBy = user.email`) (requires `CATALOG:edit`).
- `PATCH /catalog/symbols/{symbol}/toggle` — Toggles active/inactive status (requires `CATALOG:edit`).
- `DELETE /catalog/symbols/{symbol}` — Soft-deletes symbol (`isDeleted = true`, `isActive = false`, `deletedAt = now()`) with zero data loss to associated candles/audits (requires `CATALOG:delete`).
- `GET /catalog/candles` — High-speed chronologically sorted OHLCV bars from `market_candles` (requires `CATALOG:view`).
- `POST /catalog/candles/seed` — Triggers background pre-seeding of benchmark historical bars into `market_candles` (requires `CATALOG:edit`).

---

## 3. Feature Inventory & Status
- **Feature 2.1: Unified Database Schema**: **100% Completed & Verified**.
- **Feature 2.2: Benchmark Pre-Seeding**: **100% Completed & Verified**.
- **Feature 2.3: TradingView Live Asset Search & Verification**: **100% Completed & Verified**.
- **Feature 2.4: 20-Day 1m & 5m Historical Data Pre-Seeding**: **100% Completed & Verified**.
- **Feature 2.5: Frontend MUI Market Catalog Management Screen**: **100% Completed & Verified**.
