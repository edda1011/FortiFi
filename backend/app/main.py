from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.claims import router as claims_router


app = FastAPI(
    title="FortiFi API",
    version="0.1.0",
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