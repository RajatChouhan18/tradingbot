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
