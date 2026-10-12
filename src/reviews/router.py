from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.enums import (
    Rating,
    SortComments,
    SortMyReviews,
    SortOrder,
    SortReviews,
    VoteType,
)
from src.models import User
from src.security.jwt_handler import (
    get_current_user_optional,
    get_current_verified_user,
)
from src.services.tmdb.exceptions import TMDBServiceError

from .schemas import (
    CommentResponse,
    CreateComment,
    CreateReviewRequest,
    MyReviewResponse,
    NewCommentResponse,
    PaginatedCommentResponse,
    PaginatedMyReviewResponse,
    PaginatedReviewResponse,
    ReviewResponse,
    UpdateCommentRequest,
    UpdateReviewRequest,
    VoteResponse,
)
from .service import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


review_service = ReviewService()


@router.post("", response_model=MyReviewResponse, status_code=status.HTTP_201_CREATED)
async def add_review(
    request: Request,
    data: CreateReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    try:
        client = request.app.state.http_client
        return await review_service.add_review(
            data.tmdb_id,
            data.media_type,
            data.rating,
            data.content,
            db,
            current_user,
            client,
        )

    except TMDBServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TMDB service didn't respond.",
        )


@router.post(
    "/{review_id}/comments",
    response_model=NewCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def comment(
    review_id: int,
    comment: CreateComment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):

    return await review_service.comment(review_id, comment.content, db, current_user)


@router.put(
    "/{review_id}/vote", response_model=VoteResponse, status_code=status.HTTP_200_OK
)
async def vote(
    review_id: int,
    vote_type: VoteType,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):

    return await review_service.vote(review_id, vote_type, db, current_user)


@router.get(
    "/media/{media_id}",
    response_model=PaginatedReviewResponse,
    status_code=status.HTTP_200_OK,
)
async def get_media_reviews(
    media_id: int,
    search: str | None = Query(default=None),
    author: str | None = Query(default=None),
    rating: Rating | None = Query(default=None, ge=1, le=5),
    sort_by: SortReviews = Query(default=SortReviews.created_at),
    sort_order: SortOrder = Query(default=SortOrder.desc),
    limit: int | None = Query(default=20, ge=1, le=100),
    page: int | None = Query(default=1, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):

    return await review_service.get_reviews(
        media_id,
        search,
        author,
        rating,
        sort_by,
        sort_order,
        limit,
        page,
        db,
        current_user,
    )


@router.get(
    "/me", response_model=PaginatedMyReviewResponse, status_code=status.HTTP_200_OK
)
async def get_my_reviews(
    search: str | None = Query(default=None),
    rating: Rating | None = Query(default=None, ge=1, le=5),
    sort_by: SortMyReviews = Query(default=SortMyReviews.created_at),
    sort_order: SortOrder = Query(default=SortOrder.desc),
    limit: int | None = Query(default=20, ge=1, le=100),
    page: int | None = Query(default=1, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    return await review_service.get_my_reviews(
        search, rating, sort_by, sort_order, limit, page, db, current_user
    )


@router.get(
    "/{review_id}", response_model=ReviewResponse, status_code=status.HTTP_200_OK
)
async def get_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    return await review_service.get_review_by_id(review_id, db, current_user)


@router.get(
    "/{review_id}/comments",
    response_model=PaginatedCommentResponse,
    status_code=status.HTTP_200_OK,
)
async def get_comments(
    review_id: int,
    search: str | None = Query(default=None),
    sort_by: SortComments = Query(default=SortComments.created_at),
    order: SortOrder = Query(default=SortOrder.desc),
    limit: int | None = Query(default=20, ge=1, le=100),
    page: int | None = Query(default=1, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    return await review_service.get_comments(
        review_id, search, sort_by, order, limit, page, db, current_user
    )


@router.patch(
    "/{review_id}", response_model=MyReviewResponse, status_code=status.HTTP_200_OK
)
async def edit_review(
    review_id: int,
    update: UpdateReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    return await review_service.edit_review(review_id, update, db, current_user)


@router.patch(
    "/{comment_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_200_OK,
)
async def edit_comment(
    comment_id: int,
    update: UpdateCommentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    return await review_service.edit_comment(comment_id, update, db, current_user)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    return await review_service.delete_review(review_id, db, current_user)


@router.delete("/{comment_id}/comments", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    return await review_service.delete_comment(comment_id, db, current_user)
