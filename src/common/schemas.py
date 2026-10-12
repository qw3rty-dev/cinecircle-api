from datetime import date

from pydantic import BaseModel, ConfigDict

from src.enums import MediaType


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str
    model_config = ConfigDict(from_attributes=True)


class MediaResponse(BaseModel):
    id: int
    title: str
    media_type: MediaType
    premiere_date: date | None
    model_config = ConfigDict(from_attributes=True)
