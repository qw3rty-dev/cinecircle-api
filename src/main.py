from contextlib import asynccontextmanager

import httpx
import redis.asyncio as redis
from fastapi import FastAPI

from src.api.v1.router import api_router_v1
from src.home.router import router
from src.scheduler.scheduler import configure_scheduler, scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient()
    app.state.redis = redis.Redis(host="localhost",port=6379,db=0,decode_responses=True)
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
