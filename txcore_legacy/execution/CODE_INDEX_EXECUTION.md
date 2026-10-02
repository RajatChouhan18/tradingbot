# TxBot Code Index: Execution Module (`txcore/execution`)

> **Module Identifier**: `txcore/execution`  
> **Index Suffix**: `EXECUTION`  
> **Source Directory**: [`txcore/execution/`](file:///e:/Txbot/txcore/execution)  
> **Role**: Asynchronous signal dispatchers, multi-chat Telegram notifications with document attachments, and non-blocking file loggers (Stage 9: Dispatch & Stage 10: Logging).

---

## 1. Module Overview & Responsibilities

The `txcore.execution` module dispatches validated trade alerts to configured destination endpoints without blocking the core signal scanning loop.

### Key Responsibilities
- **Multi-Destination Dispatch**: [`TelegramNotifier`](file:///e:/Txbot/txcore/execution/telegram.py) broadcasts formatted alerts and chart HTML attachments across multiple Telegram chat IDs or channels concurrently.
- **Fail-Safe & Non-Crashing**: Gracefully bypasses placeholder/dummy chat IDs, logs errors, and returns per-chat delivery status maps.
- **Audit Integration**: Automatically records every message and attachment delivery attempt into [`DeliveryTracker`](file:///e:/Txbot/txcore/audit/delivery_tracker.py).
- **Persistent Footprints**: [`file_logger.py`](file:///e:/Txbot/txcore/execution/file_logger.py) appends UTC/Local timestamped records to [`signals_history.log`](file:///e:/Txbot/signals_history.log) and [`tv_market_data.log`](file:///e:/Txbot/tv_market_data.log).

---

## 2. File Index & Exported Symbols

| File | Primary Classes & Functions | Key Responsibility |
|---|---|---|
| [`base.py`](file:///e:/Txbot/txcore/execution/base.py) | `BaseNotifier` | Abstract notifier interface for pluggable dispatch channels (Telegram, Discord, Webhooks, WhatsApp). |
| [`telegram.py`](file:///e:/Txbot/txcore/execution/telegram.py) | `TelegramNotifier` | Production Telegram Bot API integration for text alerts and chart document uploads. |
| [`file_logger.py`](file:///e:/Txbot/txcore/execution/file_logger.py) | `log_signal_to_file`, `log_market_data_to_file` | UTF-8 thread-safe append-only file logging with structured header banners. |
| [`paper_engine.py`](file:///e:/Txbot/txcore/execution/paper_engine.py) | `PaperTradingEngine`, `PaperPosition`, `PaperOrder`, `get_paper_engine` | Institutional paper trading simulator, mark-to-market valuations, dynamic trailing stops, and bracket exits. |
| [`broker_adapter.py`](file:///e:/Txbot/txcore/execution/broker_adapter.py) | `BaseBrokerAdapter`, `PaperBrokerAdapter`, `ZerodhaKiteBrokerAdapter`, `InteractiveBrokersAdapter`, `BrokerManager` | Universal broker routing layer with paper, Kite Connect, and IBKR adapters. |
| [`discord.py`](file:///e:/Txbot/txcore/execution/discord.py) | `DiscordNotifier` | Discord Webhook integration with institutional rich embeds and chart uploads. |
| [`webhook.py`](file:///e:/Txbot/txcore/execution/webhook.py) | `WebhookNotifier` | Custom JSON webhook order relay and external REST integration. |

---

## 3. Class & Function Signatures

### 3.1 [`BaseNotifier`](file:///e:/Txbot/txcore/execution/base.py) (ABC)
```python
class BaseNotifier(ABC):
    @abstractmethod
    def send(
        self,
        message: str,
        signal: Optional[Signal] = None,
        chart_path: Optional[str] = None,
    ) -> Any:
        """Dispatches an alert message and optional chart attachment."""
```

### 3.2 [`TelegramNotifier`](file:///e:/Txbot/txcore/execution/telegram.py#L16-L177)
```python
class TelegramNotifier(BaseNotifier):
    def __init__(
        self,
        bot_token: str = "",
        chat_id: Optional[str] = None,
        chat_ids: Optional[List[str]] = None,
        tracker: Optional[DeliveryTracker] = None,
    ):
        ...

    def send(
        self,
        message: str,
        signal: Optional[Signal] = None,
        chart_path: Optional[str] = None,
    ) -> Dict[str, bool]:
        """
        Broadcasts message to all configured chat IDs.
        If chart_path exists, calls send_document to upload the interactive HTML chart.
        Returns: {chat_id: True/False}
        """

    def send_document(self, file_path: str, caption: str = "") -> Dict[str, bool]:
        """Sends a document/file attachment to all configured chat IDs."""
```

### 3.3 File Loggers (`file_logger.py`)
```python
def log_signal_to_file(content: str, filename: Optional[str] = None) -> str:
    """Appends signal text with UTC + Local timestamps to signals_history.log."""

def log_market_data_to_file(
    symbol_or_content: Union[str, Any],
    df: Optional[pd.DataFrame] = None,
    filename: Optional[str] = None,
    provider_name: str = "TRADINGVIEW (FX_IDC)",
) -> str:
    """Appends OHLCV market snapshot to tv_market_data.log."""
```

### 3.4 [`PaperTradingEngine`](file:///e:/Txbot/txcore/execution/paper_engine.py)
```python
class PaperTradingEngine:
    def __init__(self, initial_capital: float = 1_000_000.0, currency: str = "INR"): ...
    def get_portfolio_summary(self) -> Dict[str, Any]: ...
    def get_open_positions(self) -> List[Dict[str, Any]]: ...
    def get_closed_trades(self, limit: int = 100) -> List[Dict[str, Any]]: ...
    def open_position_from_signal(self, signal: Signal, algo_id: str, algo_name: str, risk_capital_pct: float = 0.02, slippage_pct: float = 0.0005) -> Optional[PaperPosition]: ...
    def update_price_tick(self, symbol: str, ltp: float, high: Optional[float] = None, low: Optional[float] = None) -> List[Dict[str, Any]]: ...
    def close_position_manually(self, position_id: str, exit_price: Optional[float] = None, reason: str = "MANUAL_SQUARE_OFF") -> Optional[Dict[str, Any]]: ...
    def modify_position(self, position_id: str, stop_loss: Optional[float] = None, target: Optional[float] = None) -> Optional[PaperPosition]: ...
    def reset_account(self, initial_capital: float = 1_000_000.0) -> Dict[str, Any]: ...

def get_paper_engine() -> PaperTradingEngine:
    """Returns thread-safe singleton PaperTradingEngine instance."""
```

### 3.5 [`BaseBrokerAdapter`](file:///e:/Txbot/txcore/execution/broker_adapter.py) & Adapters
```python
class BaseBrokerAdapter(ABC):
    @property
    def broker_name(self) -> str: ...
    def connect(self, **credentials) -> bool: ...
    def disconnect(self) -> bool: ...
    def is_connected(self) -> bool: ...
    def get_account_profile(self) -> Dict[str, Any]: ...
    def get_margins(self) -> Dict[str, float]: ...
    def get_positions(self) -> List[BrokerPosition]: ...
    def place_order(self, symbol: str, side: OrderSide, quantity: int, order_type: OrderType = OrderType.MARKET, price: float = 0.0, stop_loss: Optional[float] = None, target: Optional[float] = None, product: ProductType = ProductType.INTRADAY, exchange: str = "NSE", tag: str = "", **kwargs) -> BrokerOrder: ...
    def cancel_order(self, order_id: str) -> bool: ...
    def close_position(self, position_id_or_symbol: str) -> bool: ...
    def square_off_all(self) -> List[str]: ...

class PaperBrokerAdapter(BaseBrokerAdapter): ...
class ZerodhaKiteBrokerAdapter(BaseBrokerAdapter): ...
class InteractiveBrokersAdapter(BaseBrokerAdapter): ...

class BrokerManager:
    def get_adapter(self, name: Optional[str] = None) -> BaseBrokerAdapter: ...
    def set_active_broker(self, name: str) -> bool: ...
    def list_brokers(self) -> List[Dict[str, Any]]: ...

def get_broker_manager() -> BrokerManager: ...
```

### 3.6 [`DiscordNotifier`](file:///e:/Txbot/txcore/execution/discord.py)
```python
class DiscordNotifier(BaseNotifier):
    def __init__(self, webhook_url: str = "", tracker: Optional[DeliveryTracker] = None): ...
    def send(self, message: str, signal: Optional[Signal] = None, chart_path: Optional[str] = None) -> bool: ...
```

### 3.7 [`WebhookNotifier`](file:///e:/Txbot/txcore/execution/webhook.py)
```python
class WebhookNotifier(BaseNotifier):
    def __init__(self, endpoint_url: str = "", auth_token: Optional[str] = None, custom_headers: Optional[Dict[str, str]] = None, tracker: Optional[DeliveryTracker] = None): ...
    def send(self, message: str, signal: Optional[Signal] = None, chart_path: Optional[str] = None) -> bool: ...
```

---

## 4. Signal Dispatch Pipeline

```mermaid
flowchart TD
    Signal[Stage 7: Approved Signal] --> Notifier[TelegramNotifier: send]
    Notifier --> Msg[POST https://api.telegram.org/bot.../sendMessage]
    
    opt Chart Exists
        Notifier --> Doc[POST https://api.telegram.org/bot.../sendDocument]
    end
    
    Msg & Doc --> Delivery[DeliveryTracker: record_dispatch]
    Delivery --> DB[(SQLite: trading_audit.db)]
    Delivery --> AuditLog[telegram_delivery.log]
    Signal --> FLog[log_signal_to_file: signals_history.log]
```

---

## 5. Token-Saving AI Guide

- To send an alert with chart, instantiate `TelegramNotifier(bot_token, chat_ids)` and call `send(msg, signal=sig, chart_path=path)`.
- If Telegram token is missing, `is_configured` returns `False` and operations log a skip instead of raising uncaught exceptions.
- Destination logs are anchored to project workspace root: [`signals_history.log`](file:///e:/Txbot/signals_history.log), [`tv_market_data.log`](file:///e:/Txbot/tv_market_data.log), [`telegram_delivery.log`](file:///e:/Txbot/telegram_delivery.log).
