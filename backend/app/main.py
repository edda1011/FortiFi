from fastapi import FastAPI

from app.api.claims import router as claims_router


app = FastAPI(
    title="FortiFi API",
    version="0.1.0",
)


app.include_router(claims_router)


@app.get("/health")
async def health():
    return {
        "status": "ok"
    }