from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.common.schemas import MediaResponse, PaginationMeta
from src.enums import MediaType, VoteType


class CreateReviewRequest(BaseModel):
    tmdb_id: int
    media_type: MediaType
    rating: int = Field(ge=1, le=5)
    content: str = Field(min_length=1, max_length=1000)
    model_config = ConfigDict(extra="forbid")


class UpdateReviewRequest(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    content: str | None = Field(default=None, min_length=1, max_length=1000)
    model_config = ConfigDict(extra="forbid")


class UpdateCommentRequest(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=1000)
    model_config = ConfigDict(extra="forbid")


class CreateComment(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    model_config = ConfigDict(extra="forbid")


class AuthorResponse(BaseModel):
    id: int
    username: str
    model_config = ConfigDict(from_attributes=True)


class ReviewInfo(BaseModel):  ## single review, single author
    id: int
    user: AuthorResponse
    rating: int
    content: str
    upvotes: int
    downvotes: int
    my_vote: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReviewResponse(
    BaseModel
):  ## single media, single author (used in get review by id)
    media: MediaResponse
    review: ReviewInfo
    model_config = ConfigDict(from_attributes=True)


class PaginatedReviewResponse(
    BaseModel
):  ## single media, multiple authors reviews (used in get reviews by media id)
    meta: PaginationMeta
    media: MediaResponse
    results: list[ReviewInfo]
    model_config = ConfigDict(from_attributes=True)


class MyReviewResponse(
    BaseModel
):  ## single author(current_user), single media (used in add & edit review)
    id: int
    rating: int
    content: str
    upvotes: int
    downvotes: int
    my_vote: str | None
    created_at: datetime
    media: MediaResponse
    model_config = ConfigDict(from_attributes=True)


class PaginatedMyReviewResponse(
    BaseModel
):  ## multiple reviews of multiple media made by current user (used in get my reviews)
    meta: PaginationMeta
    results: list[MyReviewResponse]
    model_config = ConfigDict(from_attributes=True)


class CommentResponse(BaseModel):
    id: int
    content: str
    created_at: datetime
    user: AuthorResponse
    model_config = ConfigDict(from_attributes=True)


class NewCommentResponse(CommentResponse):
    review_id: int
    model_config = ConfigDict(from_attributes=True)


class PaginatedCommentResponse(BaseModel):
    meta: PaginationMeta
    review: ReviewInfo
    results: list[CommentResponse]
    model_config = ConfigDict(from_attributes=True)


class VoteResponse(BaseModel):
    vote_type: VoteType | None
    model_config = ConfigDict(from_attributes=True)
