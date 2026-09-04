from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.claims import router as claims_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.risk import router as risk_router
from app.api.thetanuts import router as thetanuts_router
from app.api.wallet import router as wallet_router
from app.database.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create any tables that don't exist yet (SQLite, no Alembic).
    init_db()
    yield


app = FastAPI(
    title="FortiFi API",
    version="0.1.0",
    lifespan=lifespan,
)


# Allow the local Vite development server to communicate
# with the FastAPI backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    claims_router,
    prefix="/api/claims",
    tags=["Claims"],
)


app.include_router(
    wallet_router,
    prefix="/api/wallet",
    tags=["Wallet"],
)


app.include_router(
    risk_router,
    prefix="/api/risk",
    tags=["Risk"],
)


app.include_router(
    dashboard_router,
    prefix="/api/dashboard",
    tags=["Dashboard"],
)


app.include_router(
    thetanuts_router,
    prefix="/api/thetanuts",
    tags=["Thetanuts"],
)


@app.get("/")
def root():
    return {
        "name": "FortiFi API",
        "status": "online",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }
