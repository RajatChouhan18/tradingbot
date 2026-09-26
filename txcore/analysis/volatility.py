"""
txcore.analysis.volatility
~~~~~~~~~~~~~~~~~~~~~~~~~~
Volatility regime classification, India/US VIX analysis, and risk recommendation engine.
Conforms to Stage 3 (Identify) and Stage 5 (Analyze) of the universal pipeline.
"""

from typing import Optional, Dict, Any, Tuple
from txcore.models.types import VixRegime, VixAnalysis
from config.settings import VIX_REGIMES


def analyze_vix(
    vix_value: float,
    change: float = 0.0,
    percent_change: float = 0.0,
    regimes: Optional[Dict[str, Tuple[float, float]]] = None,
) -> VixAnalysis:
    """
    Classifies a VIX volatility level into a standard VixRegime and provides
    market-agnostic trading implications and risk management recommendations.

    Args:
        vix_value: Current value of the volatility index (e.g. India VIX, CBOE VIX).
        change: Point change from previous close.
        percent_change: Percentage change from previous close.
        regimes: Optional dictionary defining volatility thresholds. Defaults to VIX_REGIMES.

    Returns:
        VixAnalysis object with current level, regime, implication, and recommendation.
    """
    thresholds = regimes or VIX_REGIMES
    low_upper = thresholds.get("LOW", (0.0, 13.0))[1]
    normal_upper = thresholds.get("NORMAL", (13.0, 18.0))[1]
    elevated_upper = thresholds.get("ELEVATED", (18.0, 24.0))[1]

    if vix_value < low_upper:
        regime = VixRegime.LOW
        implication = "Low volatility regime. Option premiums are cheap; market is prone to sudden range contraction/chop."
        recommendation = "Be cautious with long options scalping; consider defined-risk credit spreads."
    elif vix_value < normal_upper:
        regime = VixRegime.NORMAL
        implication = "Normal volatility regime. Healthy directional trends and standard momentum moves."
        recommendation = "Ideal for directional price action setups and momentum option buying."
    elif vix_value < elevated_upper:
        regime = VixRegime.ELEVATED
        implication = "Elevated volatility regime. Wider price swings and expanding option premiums."
        recommendation = "Use wider stop-losses; target larger reward:risk; watch for abrupt reversals."
    else:
        regime = VixRegime.EXTREME
        implication = "Extreme fear regime. Intense market turbulence and sky-high option premiums."
        recommendation = "Severe IV crush risk. Avoid naked buying; use hedged debit spreads or stay cash."

    return VixAnalysis(
        current_vix=vix_value,
        regime=regime,
        change=change,
        percent_change=percent_change,
        implication=implication,
        recommendation=recommendation,
    )
