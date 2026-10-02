# AuraTrade Code Index: Event Triggers Module (`txcore.events`)

> **Repository Identifier**: `txcore.events`  
> **Index Suffix**: `EVENTS`  
> **Source Directory**: [`txcore/events/`](file:///e:/Txbot/txcore/events)  
> **Role**: Standalone Named Signal Watchers & Multi-Channel Alert Dispatching (without trade execution).

---

## 1. Module Overview
The `txcore.events` package provides the complete backend engine for **Module 4: Event Triggers**. It enables users and automated systems to configure standalone watchers on any market symbol, evaluate rule conditions against real-time and historical candles, and dispatch instant notifications to Telegram, WhatsApp, and Webhooks with zero data loss.

---

## 2. File & Component Registry

| File | Primary Classes / Functions | Purpose & Responsibilities |
|---|---|---|
| [`txcore/events/models.py`](file:///e:/Txbot/txcore/events/models.py) | `TriggerType`, `TriggerStatus`, `ChannelType`, `CreateEventTriggerRequest`, `UpdateEventTriggerRequest`, `EventTriggerResponse`, `TriggerExecutionLogResponse`, `TestTriggerRequest`, `TestTriggerResponse` | Pydantic data schemas, request/response validators, and condition threshold models. |
| [`txcore/events/evaluators.py`](file:///e:/Txbot/txcore/events/evaluators.py) | `SignalEvaluatorEngine`, `EvaluationResult` | Pure signal rule evaluators for Price Spike, Volume Surge, S/R Breakout/Breakdown, Candlestick Patterns, and Indicator Crossovers. |
| [`txcore/events/dispatcher.py`](file:///e:/Txbot/txcore/events/dispatcher.py) | `MultiChannelAlertDispatcher`, `TelegramDispatcher`, `WhatsAppDispatcher`, `WebhookDispatcher`, `AlertPayload`, `format_institutional_alert_text` | Multi-channel async alert dispatcher, message formatter, and ACID `TriggerExecutionLog` persistence. |
| [`txcore/events/router.py`](file:///e:/Txbot/txcore/events/router.py) | `events_router`, `list_event_triggers`, `create_event_trigger`, `get_event_trigger`, `update_event_trigger`, `toggle_trigger_status`, `delete_event_trigger`, `simulate_trigger_evaluation`, `test_existing_trigger`, `get_trigger_logs` | FastAPI REST endpoints for full CRUD, quick status toggle, live dry-run simulator, and log querying. |
| [`txcore/events/worker.py`](file:///e:/Txbot/txcore/events/worker.py) | `EventEvaluationWorker`, `event_worker` | Background polling loop, batch grouping by `(symbol, market, timeframe)`, and candle-level deduplication locks. |

---

## 3. Database Schema Models (Prisma)

- **`EventTrigger`**:
  - `id`: String (UUID)
  - `name`: String
  - `symbol`: String
  - `market`: String
  - `timeframe`: String
  - `triggerType`: `TriggerType`
  - `thresholdConfig`: Json
  - `channels`: Json
  - `channelTargets`: Json
  - `status`: `TriggerStatus`
  - `lastTriggeredAt`: DateTime?
  - `triggerCount`: Int @default(0)
  - `isDeleted`: Boolean @default(false)
  - `deletedAt`: DateTime?
  - `createdAt`, `updatedAt`, `createdBy`, `updatedBy`

- **`TriggerExecutionLog`**:
  - `id`: String (UUID)
  - `triggerId`: String (Relation to `EventTrigger`)
  - `symbol`: String
  - `market`: String
  - `timeframe`: String
  - `triggerType`: `TriggerType`
  - `triggerPrice`: Float
  - `conditionsMet`: Json
  - `candleTimestamp`: DateTime
  - `channelsNotified`: Json
  - `dispatchSuccess`: Boolean
  - `latencyMs`: Int
  - `errorMessage`: String?
  - `createdAt`, `createdBy`, `updatedBy`
