from pydantic import BaseModel, ConfigDict

from src.common.schemas import PaginationMeta
from src.media.schemas import MovieResult, TvResult
from src.reviews.schemas import MediaResponse, ReviewInfo


class RecommendationResponse(BaseModel):
    page: int
    results: list[MovieResult | TvResult]
    model_config = ConfigDict(from_attributes=True)


class ReviewsFeed(ReviewInfo):
    media: MediaResponse
    model_config = ConfigDict(from_attributes=True)


class PaginatedReviewResponse(BaseModel):
    meta: PaginationMeta
    reviews: list[ReviewsFeed]
    model_config = ConfigDict(from_attributes=True)
