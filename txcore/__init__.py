"""
AuraTrade Core Architecture (txcore)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Institutional ecosystem to monitor paper trades, strategies, and portfolio performance.

Modules:
    - auth: User & Role Management, Sessions & Permissions Matrix, Cash Management.
    - catalog: Market Catalog & Asset Directory with live search verification.
    - marketview: Data Provider Layer, Live Data, Market-Closed Overlays, Incremental Engine.
    - events: Event Triggers & Standalone Signal Generator (Telegram/WhatsApp).
    - algotrade: Composite Trigger Logic & Configurable Predefined Strategies.
    - paper: Paper Trading Execution Module (Multi-Leg & Standalone Trades, Full Evaluation Matrix).
    - visualization: Pure Data-Driven Charting & Progressive Diagnostic Rendering.
    - test_engine: In-App Interactive Test Workbench & Loophole Test Suite.
"""

__app_name__ = "AuraTrade"
__version__ = "2.0.0"
__author__ = "AuraTrade Engineering Team"
