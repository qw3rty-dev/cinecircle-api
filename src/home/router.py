from fastapi import APIRouter

from .schemas import HomeResponse

router = APIRouter()


@router.get("/", response_model=HomeResponse, include_in_schema=False)
def home():
    return HomeResponse(
        name="CineCircle API",
        version="1.0.0",
        description="Backend API for CineCircle",
        status="running",
        documentation="/docs",
    )
