"""
AuraTrade Modular REST API Service (txcore.service)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
FastAPI application service mounting modular routers (Auth, Roles, Users,
and upcoming MarketView, Events, AlgoTrade, Paper Trading, and Test Workbench).
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from txcore.database import connect_db, disconnect_db, check_db_health
from txcore.auth import auth_router, user_router, seed_system_roles_and_superadmin
from txcore.catalog.seeder import seed_benchmarks

logger = logging.getLogger("auratrade.service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("[*] Starting AuraTrade Core Service...")
    await connect_db()
    logger.info("[*] Ensuring System Roles and SuperAdmin are seeded...")
    seed_result = await seed_system_roles_and_superadmin()
    logger.info(f"[*] Auth Seeding complete: {seed_result}")

    logger.info("[*] Ensuring Benchmark Catalog (NSE, US, Crypto, Forex, MCX) is seeded...")
    catalog_result = await seed_benchmarks()
    logger.info(f"[*] Benchmark Catalog Seeding complete: {catalog_result}")
    yield
    # Shutdown
    logger.info("[*] Shutting down AuraTrade Core Service...")
    await disconnect_db()


app = FastAPI(
    title="AuraTrade API",
    description="Institutional ecosystem to monitor paper trades, strategies, and portfolio performance.",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Modular Routers
from txcore.catalog.router import catalog_router
from txcore.marketview.router import marketview_router

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(catalog_router, prefix="/api")
app.include_router(catalog_router)
app.include_router(marketview_router, prefix="/api")
app.include_router(marketview_router)


# Status & Health Endpoints
@app.get("/api/status")
@app.get("/api/health")
async def health_check():
    db_health = await check_db_health()
    return {
        "status": "ONLINE",
        "app": "AuraTrade",
        "version": "2.0.0",
        "database": db_health,
    }


@app.get("/")
async def root():
    return {
        "app": "AuraTrade",
        "version": "2.0.0",
        "docs_url": "/docs",
        "status_url": "/api/status",
    }
