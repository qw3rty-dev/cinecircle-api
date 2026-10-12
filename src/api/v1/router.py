from fastapi import APIRouter

from src.admin.router import router as admin_router
from src.auth.router import router as auth_router
from src.feed.router import router as feed_router

# from src.home.router import router as home_router
from src.media.router import router as media_router
from src.reviews.router import router as reviews_router
from src.users.router import router as connection_router
from src.watchlist.router import router as watchlist_router

api_router_v1 = APIRouter(prefix="/v1")

api_router_v1.include_router(auth_router)
api_router_v1.include_router(media_router)
api_router_v1.include_router(connection_router)
api_router_v1.include_router(reviews_router)
api_router_v1.include_router(watchlist_router)
api_router_v1.include_router(feed_router)
# api_router_v1.include_router(home_router)
api_router_v1.include_router(admin_router)
