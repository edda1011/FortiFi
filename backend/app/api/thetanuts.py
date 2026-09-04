import httpx
from fastapi import APIRouter, HTTPException


router = APIRouter()

THETANUTS_ORDERBOOK_URL = "https://round-snowflake-9c31.devops-118.workers.dev"


@router.get("/orderbook/")
async def get_orderbook():
    """Relay the public Thetanuts orderbook because its API does not allow browser CORS."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(THETANUTS_ORDERBOOK_URL)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Thetanuts orderbook is temporarily unavailable.",
        ) from exc
