from fastapi import APIRouter, Request

from src.core.rate_limiting import limiter

from .schemas import HomeResponse

router = APIRouter()


@router.get("/", response_model=HomeResponse, include_in_schema=False)
@limiter.limit("120/minute")
@limiter.limit("10/second")
def home(request:Request):
    return HomeResponse(
        name="CineCircle API",
        version="1.0.0",
        description="Backend API for CineCircle",
        status="running",
        documentation="/docs",
    )
