"""
run_server.py
~~~~~~~~~~~~~
Runs the TxBot Universal AlgoTrade FastAPI Backend Service with Uvicorn.
Serves REST API, charts, and optional frontend static build.

Usage:
  python run_server.py
  python run_server.py --port 8000 --host 0.0.0.0 --reload
"""

import sys
import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="TxBot AlgoTrade Backend Service Runner")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--reload", action="store_true", default=True, help="Enable auto-reload on code change (default: True)")

    args = parser.parse_args()

    print("=" * 70)
    print("[*] STARTING TXBOT ALGOTRADE BACKEND HTTP SERVICE")
    print(f"[-] API Base URL:  http://{args.host}:{args.port}")
    print(f"[-] OpenAPI Docs:  http://{args.host}:{args.port}/docs")
    print(f"[-] Charts Mount:  http://{args.host}:{args.port}/charts/")
    print("=" * 70)

    uvicorn.run("txcore.service:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
