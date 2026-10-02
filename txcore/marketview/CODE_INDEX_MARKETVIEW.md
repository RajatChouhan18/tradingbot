# AuraTrade Code Index: MarketView Data Provider Layer (`txcore/marketview`)

> **Module**: Module 3: MarketView Engine  
> **Source Directory**: [`txcore/marketview/`](file:///e:/Txbot/txcore/marketview)  
> **Package Index**: `MARKETVIEW` / `DATA_PROVIDERS`  
> **Test Suite**: [`tests/test_feature_3_1_providers.py`](file:///e:/Txbot/tests/test_feature_3_1_providers.py) (100% Pass)  

---

## 1. Module Overview & Responsibilities

The `txcore.marketview` module acts as the central data provider and real-time ingestion layer of **AuraTrade**. It delivers unified, high-speed candlestick lookbacks and real-time spot quotes to downstream modules (Event Triggers, AlgoTrade, Paper Trading, Charts) while maintaining strict **O(1) incremental computation guarantees** (zero recalculation of past 180 bars).

### Core Design Guarantees:
- **Liskov Substitution Principle (LSP)**: All providers inherit from `BaseDataProvider` and return standardized Pydantic models (`CandleData`, `LiveQuote`, `MarketStatusInfo`).
- **Resilient Fallback Routing**: `ProviderRegistry` automatically fails over from primary adapters to secondary backups upon upstream network dropouts.
- **Thread-Safe Async TTL Caching**: `get_cached_candles` prevents redundant remote queries during multi-symbol parallel evaluation loops.
- **Zero Dummy Data**: All market data is sourced from real exchanges (Binance, TradingView, NSE India, Yahoo Finance).

---

## 2. File Index & Exported Symbols

| File | Primary Classes / Interfaces | Responsibility |
|---|---|---|
| [`models.py`](file:///e:/Txbot/txcore/marketview/models.py) | `CandleData`, `LiveQuote`, `MarketStatusInfo`, `ProviderTechnicals`, `MarketDataResponse` | Pydantic data contracts for market data, quotes, and status banners. |
| [`providers/base.py`](file:///e:/Txbot/txcore/marketview/providers/base.py) | `BaseDataProvider` | Abstract base class with async `asyncio.Lock` TTL caching and invalidation. |
| [`providers/tradingview.py`](file:///e:/Txbot/txcore/marketview/providers/tradingview.py) | `TradingViewProvider` | Multi-asset candlestick stream for global equities, forex, and commodities. |
| [`providers/binance.py`](file:///e:/Txbot/txcore/marketview/providers/binance.py) | `BinanceProvider` | Sub-100ms crypto provider using Binance public klines and 24hr ticker REST endpoints. |
| [`providers/yahoo.py`](file:///e:/Txbot/txcore/marketview/providers/yahoo.py) | `YahooFinanceProvider` | Resilient global fallback provider for US Equities, Global Indices, and Forex pairs. |
| [`providers/nse.py`](file:///e:/Txbot/txcore/marketview/providers/nse.py) | `NseDirectProvider` | Official spot quotes, index levels, and India VIX scraper for Indian equities. |
| [`providers/registry.py`](file:///e:/Txbot/txcore/marketview/providers/registry.py) | `ProviderRegistry`, `provider_registry` | Factory registry with market-specific routing and automatic secondary failover. |
| [`session.py`](file:///e:/Txbot/txcore/marketview/session.py) | `BaseMarketCalendar`, `IndianEquityCalendar`, `UsEquityCalendar`, `CryptoCalendar`, `ForexCalendar`, `McxCalendar`, `MarketSessionManager`, `session_manager` | Timezone-aware session evaluators, market-closed detection, holiday schedules, next session open computation, and status banner formatting. |
| [`overlays.py`](file:///e:/Txbot/txcore/marketview/overlays.py) | `compute_market_technicals`, `detect_candlestick_patterns`, `calculate_ema`, `calculate_sma`, `calculate_vwap`, `calculate_rsi`, `calculate_macd`, `calculate_bollinger_bands`, `calculate_atr`, `classify_vix_regime` | Technical indicator engine (EMA, SMA, VWAP, BB, RSI, MACD, ATR), VIX regime classifier, and candle recognition pattern detection. |
| [`incremental.py`](file:///e:/Txbot/txcore/marketview/incremental.py) | `IncrementalMarketState`, `IncrementalEngine`, `incremental_engine` | Strict incremental computation engine with O(1) rolling accumulators, sub-millisecond execution, and forming candle tick synthesis. |
| [`router.py`](file:///e:/Txbot/txcore/marketview/router.py) | `marketview_router` | FastAPI REST router with `/marketview/data` (supporting `indicators` and `candles`), `/marketview/status`, `/marketview/quote` endpoints. |

---

## 3. Class & Method Signatures

### `BaseDataProvider` ([`txcore/marketview/providers/base.py`](file:///e:/Txbot/txcore/marketview/providers/base.py))
```python
class BaseDataProvider(ABC):
    def __init__(self, name: str, cache_ttl_seconds: float = 3.0): ...
    async def fetch_candles(self, symbol: str, timeframe: str = "5m", lookback: int = 180, ...) -> List[CandleData]: ...
    async def fetch_live_quote(self, symbol: str, **kwargs) -> Optional[LiveQuote]: ...
    async def get_cached_candles(self, symbol: str, timeframe: str = "5m", lookback: int = 180, ...) -> List[CandleData]: ...
    async def get_cached_live_quote(self, symbol: str, **kwargs) -> Optional[LiveQuote]: ...
    async def invalidate_cache(self, symbol: Optional[str] = None) -> None: ...
```

### `ProviderRegistry` ([`txcore/marketview/providers/registry.py`](file:///e:/Txbot/txcore/marketview/providers/registry.py))
```python
class ProviderRegistry:
    def register_provider(self, market: str, primary: BaseDataProvider, fallback: Optional[BaseDataProvider] = None) -> None: ...
    def get_provider(self, market: str) -> BaseDataProvider: ...
    async def fetch_candles_with_fallback(self, symbol: str, market: str, timeframe: str = "5m", lookback: int = 180, ...) -> List[CandleData]: ...
    async def fetch_live_quote_with_fallback(self, symbol: str, market: str, ...) -> Optional[LiveQuote]: ...
```

### `MarketSessionManager` ([`txcore/marketview/session.py`](file:///e:/Txbot/txcore/marketview/session.py))
```python
class MarketSessionManager:
    def get_calendar(self, market: str) -> BaseMarketCalendar: ...
    def get_market_status(
        self, market: str, last_price: Optional[float] = None, last_time: Optional[datetime] = None,
        dt: Optional[datetime] = None, exchange: Optional[str] = None
    ) -> MarketStatusInfo: ...
```

### `IncrementalEngine` ([`txcore/marketview/incremental.py`](file:///e:/Txbot/txcore/marketview/incremental.py))
```python
class IncrementalEngine:
    def get_or_create_state(self, symbol: str, timeframe: str = "5m", initial_candles: Optional[List[CandleData]] = None) -> IncrementalMarketState: ...
    def process_closed_candle(self, symbol: str, timeframe: str, candle: CandleData) -> Dict[str, Any]: ...
    def reset_state(self, symbol: Optional[str] = None, timeframe: Optional[str] = None) -> None: ...
```

---

## 4. API Endpoints (`txcore/marketview/router.py`)
Mounted under `/api/marketview` and `/marketview`:
- `GET /marketview/data` — Dual-mode data endpoint (`LIVE` streaming lookback vs `HISTORICAL` date range from `market_candles`), selective technical overlays (`overlays=EMA_9,VWAP,RSI,MACD,BB,PATTERNS`), live quote, session status banner, and latency timer (requires `MARKETVIEW:view`).
- `GET /marketview/status` — Quick market session status and banner message (requires `MARKETVIEW:view`).
- `GET /marketview/quote` — Real-time spot quote for a single asset (requires `MARKETVIEW:view`).
- `GET /api/v1/users/me/terminal-config` — Isolated user terminal preferences for default market, symbol, timeframe, overlays, patterns.
- `PUT /api/v1/users/me/terminal-config` — Persist user terminal configuration with institutional audit tracking (`createdAt`, `updatedAt`, `createdBy`, `updatedBy`).

---

## 5. Feature Delivery Status
- **Feature 3.1: Data Provider Architecture & Unified Adapter Registry**: **100% Completed & Verified**.
- **Feature 3.2: Market-Closed Detection & Timing Engine**: **100% Completed & Verified**.
- **Feature 3.3: Interactive Range & Timeframe Selector API**: **100% Completed & Verified**.
- **Feature 3.4: Technical Overlays & Add-on Engine**: **100% Completed & Verified**.
- **Feature 3.5: Strict Incremental Computation Engine**: **100% Completed & Verified**.
- **Feature 3.6: Precision Invariants, Fast Live Streaming & User Terminal Configuration**: **100% Completed & Verified**.
