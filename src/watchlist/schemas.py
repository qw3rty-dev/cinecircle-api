from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.common.schemas import MediaResponse, PaginationMeta
from src.enums import MediaType, WatchlistStatus


class AddToWatchlistRequest(BaseModel):
    tmdb_id: int
    media_type: MediaType
    model_config = ConfigDict(extra="forbid")


class UpdateWatchlistRequest(BaseModel):
    status: WatchlistStatus
    model_config = ConfigDict(extra="forbid")


class WatchlistResponse(BaseModel):
    id: int
    status: WatchlistStatus
    created_at: datetime
    media: MediaResponse
    model_config = ConfigDict(from_attributes=True)


class PaginatedWatchlistResponse(BaseModel):
    meta: PaginationMeta
    results: list[WatchlistResponse]
    model_config = ConfigDict(from_attributes=True)
