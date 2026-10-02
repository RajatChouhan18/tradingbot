from txcore.visualization.chart_builder import (
    create_interactive_chart,
    build_tradingview_chart_html,
    build_plotly_chart,
    recreate_tradingview_chart,
    audit_pair_patterns,
    run_test_signal,
)

__all__ = [
    "create_interactive_chart",
    "build_tradingview_chart_html",
    "build_plotly_chart",
    "recreate_tradingview_chart",
    "audit_pair_patterns",
    "run_test_signal",
    "run_chart_cli",
    "build_cli_parser",
]


def __getattr__(name: str):
    if name in ("run_chart_cli", "build_cli_parser"):
        from txcore.visualization import chart_cli
        return getattr(chart_cli, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
