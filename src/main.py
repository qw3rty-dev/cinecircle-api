import os
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as redis
from dotenv import load_dotenv
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.v1.router import api_router_v1
from src.core.rate_limiting import limiter
from src.home.router import router
from src.scheduler.scheduler import configure_scheduler, scheduler

load_dotenv()
REDIS_URL = os.getenv("REDIS_URL")

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient()
    
    app.state.redis = redis.Redis.from_url(REDIS_URL)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    configure_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown()
    await app.state.http_client.aclose()
    await app.state.redis.aclose()


app = FastAPI(
    title="CineCircle API",
    version="1.0.0",
    description="CineCircle — a backend engineering project focused on API design, data modeling, authentication, and asynchronous application development.",
    lifespan=lifespan,
)

app.include_router(api_router_v1)
app.include_router(router)

# @app.get("/home")
# @limiter.limit("5/minute")
# async def homepage(request: Request):
#     return "test"
# @app.get("/mars")
# @limiter.limit("5/minute")
# async def homepage_s(request: Request):
#     return {"key": "value"}