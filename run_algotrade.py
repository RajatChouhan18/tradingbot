"""
run_algotrade.py
~~~~~~~~~~~~~~~~
Executable entry point for spinning up and monitoring named AlgoTrade process instances.
Conforms to the TxBot Market-Agnostic High-Performance Architecture.

Usage:
  # Run a named AlgoTrade on Indian Equities
  python run_algotrade.py --name "Ishaq strategy 1" --market INDIAN_EQUITY --stock RELIANCE

  # Run on Benchmark Index with chart generation
  python run_algotrade.py --name "NiftyScalper" --index NIFTY --timeframe 5m --chart

  # Run on Forex pair
  python run_algotrade.py --name "Forex Majors" --market FOREX --symbol EUR/USD
"""

import sys
from txcore.cli import main

if __name__ == "__main__":
    # Ensure '--algo' flag is present if not already passed
    if "--algo" not in sys.argv and not any(arg in sys.argv for arg in ["--snapshot", "-s", "--breadth", "--sectors", "--trend", "--audit", "--scan-signal"]):
        sys.argv.append("--algo")
    main()
