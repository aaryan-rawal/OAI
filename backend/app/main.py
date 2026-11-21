from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.auth import router as auth_router
from app.api.routes import router as routes_router
from app.api.cargo import router as cargo_router
from app.api.matching import router as matching_router
from app.api.shipments import router as shipments_router
from app.api.fleet import router as fleet_router
from app.api.admin import router as admin_router
from app.api.integrations import router as integrations_router
from app.api.documents import router as documents_router
from app.api.driver_verification import router as driver_verification_router
from app.api.workflows import router as workflows_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.driver_compliance_monitor import monitor_loop
    task = asyncio.create_task(monitor_loop())
    try:
        yield
    finally:
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass
        from app.db import dispose_engine
        await dispose_engine()

app = FastAPI(
    lifespan=lifespan,
    title="OptiFreight AI — Intelligent Freight Optimization",
    version="1.0.0",
    description="Post-delivery backhaul cargo matching with fail-closed deterministic eligibility rules.",
)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True,
                   allow_methods=["GET","POST","PUT","DELETE","OPTIONS"], allow_headers=["Authorization","Content-Type"])
for router in [auth_router,routes_router,cargo_router,matching_router,shipments_router,fleet_router,admin_router,integrations_router,documents_router,driver_verification_router,workflows_router]:
    app.include_router(router, prefix="/api")

@app.get("/health", tags=["health"])
async def health():
    return {"status":"ok","service":"optifreight-api","version":"1.0.0"}

@app.get("/health/ready", tags=["health"])
async def readiness():
    from sqlalchemy import text
    from app.db import get_engine
    async with get_engine().connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status":"ready","database":"connected"}
