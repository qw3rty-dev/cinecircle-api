import httpx
import redis.asyncio as redis
from fastapi import HTTPException, status
from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.common.utils import generate_meta, str_to_date
from src.enums import (
    MediaActivityType,
    MediaType,
    Rating,
    SortComments,
    SortMyReviews,
    SortOrder,
    SortReviews,
    VoteType,
)
from src.media.service import MediaService
from src.models import Comment, Media, MediaActivity, Review, ReviewVote, User
from src.services.tmdb.service import get_by_id

from .schemas import MediaMetadata, UpdateCommentRequest, UpdateReviewRequest


async def extract_votes_of_reviews(
    review_ids: list, db: AsyncSession, current_user: User
):
    if not review_ids:
        return {}, {}
    vote_count = (
        await db.execute(
            select(
                ReviewVote.review_id,
                func.count()
                .filter(ReviewVote.vote_type == VoteType.upvote)
                .label("upvote"),
                func.count()
                .filter(ReviewVote.vote_type == VoteType.downvote)
                .label("downvote"),
            )
            .join(ReviewVote.user)
            .where(ReviewVote.review_id.in_(review_ids), User.is_deleted.is_(False))
            .group_by(ReviewVote.review_id)
        )
    ).all()

    if current_user:
        my_votes = (
            await db.execute(
                select(ReviewVote.review_id, ReviewVote.vote_type).where(
                    ReviewVote.user_id == current_user.id,
                    ReviewVote.review_id.in_(review_ids),
                )
            )
        ).all()

    vote_counts = {
        review_id: {"upvotes": upvotes, "downvotes": downvotes}
        for review_id, upvotes, downvotes in vote_count
    }
    my_vote_types = (
        {review_id: vote_type for review_id, vote_type in my_votes}
        if current_user
        else {review_id: None for review_id in review_ids}
    )

    return vote_counts, my_vote_types


async def get_review_comments_query(
    review_id: int,
    search: str,
    sort_by: SortComments,
    sort_order: SortOrder,
    limit: int,
    page: int,
    db: AsyncSession,
):

    review = await db.scalar(
        select(Review)
        .join(Review.user)
        .where(Review.id == review_id, User.is_deleted.is_(False))
        .options(selectinload(Review.user))
    )
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )

    query = select(Comment).where(Comment.review_id == review_id)
    query = (
        query.join(Comment.user)
        .where(User.is_deleted.is_(False))
        .options(selectinload(Comment.user))
    )
    if search:
        search = search.strip()
        query = query.where(Comment.content.ilike(f"%{search}%"))
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    sort_fields = {
        SortComments.created_at: Comment.created_at,
        SortComments.username: func.lower(User.username),
    }
    sort_expression = sort_fields[sort_by]
    order = (
        sort_expression.asc() if sort_order == SortOrder.asc else sort_expression.desc()
    )
    query = query.order_by(order, Comment.id.desc())
    offset = (page - 1) * limit
    query = query.limit(limit).offset(offset)
    comments = (await db.scalars(query)).all()
    return comments, review, total


async def extract_reviews_by_tmdb_id(
    tmdb_id: int,
    media_type: MediaType,
    search: str,
    author: str,
    rating: Rating,
    sort_by: SortReviews,
    sort_order: SortOrder,
    limit: int,
    page: int,
    db: AsyncSession,
    client: httpx.AsyncClient,
    redis_client: redis.Redis
):

    media = await db.scalar(select(Media).where(Media.tmdb_id == tmdb_id, Media.media_type == media_type))
    if not media:
        media_raw = await get_by_id(client,redis_client, tmdb_id, media_type)
        media = MediaMetadata(
            tmdb_id= media_raw.get('id'),
            title = media_raw.get('title') or media_raw.get('name'),
            media_type = media_type,
            premiere_date= str_to_date(media_raw.get("release_date") or media_raw.get("first_air_date"))

        )
        return [], media, 0
    
    query = select(Review).where(Review.media_id == media.id)
    query = (
        query.join(Review.user)
        .options(selectinload(Review.user))
        .where(User.is_deleted.is_(False))
    )
    if search:
        search = search.strip()
        query = query.where(Review.content.ilike(f"%{search}%"))
    if author:
        author = author.strip()
        query = query.where(User.username.ilike(f"%{author.strip()}%"))
    if rating:
        query = query.where(Review.rating == rating.value)

    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    sort_fields = {
        SortReviews.created_at: Review.created_at,
        SortReviews.username: func.lower(User.username),
        SortReviews.rating: Review.rating,
    }
    sort_expression = sort_fields[sort_by]
    order = (
        sort_expression.asc() if sort_order == SortOrder.asc else sort_expression.desc()
    )
    query = query.order_by(order, Review.id.desc())

    offset = (page - 1) * limit
    query = query.limit(limit).offset(offset)
    reviews = (await db.scalars(query)).all()
    return reviews, media, total


async def extract_my_reviews(
    user_id: int,
    search: str,
    rating: Rating,
    sort_by: SortMyReviews,
    sort_order: SortOrder,
    limit: int,
    page: int,
    db: AsyncSession,
):
    query = select(Review).where(Review.user_id == user_id)
    query = query.join(Review.media).options(selectinload(Review.media))

    if search:
        query = query.where(
            or_(
                Review.content.ilike(f"%{search}%"),
                Media.title.ilike(f"%{search.strip()}%"),
            )
        )
    if rating:
        query = query.where(Review.rating == rating.value)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    sort_fields = {
        SortMyReviews.created_at: Review.created_at,
        SortMyReviews.rating: Review.rating,
        SortMyReviews.title: func.lower(Media.title),
    }
    sort_expression = sort_fields[sort_by]
    order = (
        sort_expression.asc() if sort_order == SortOrder.asc else sort_expression.desc()
    )
    query = query.order_by(order, Review.id.desc())

    offset = (page - 1) * limit
    query = query.limit(limit).offset(offset)
    reviews = (await db.scalars(query)).all()
    return reviews, total


class ReviewService:
    async def add_review(
        self,
        tmdb_id: int,
        media_type: MediaType,
        rating: int,
        content: str,
        db: AsyncSession,
        current_user: User,
        client: httpx.AsyncClient,
        redis_client:redis.Redis
    ):

        media_id = await MediaService.get_or_create_media(
            tmdb_id, media_type, db, client, redis_client
        )

        review = Review(
            media_id=media_id, user_id=current_user.id, rating=rating, content=content
        )
        existing_activity = await db.scalar(
            select(
                exists().where(
                    MediaActivity.media_id == media_id,
                    MediaActivity.user_id == current_user.id,
                )
            )
        )
        if not existing_activity:
            user_activity = MediaActivity(
                media_id=media_id,
                user_id=current_user.id,
                activity=MediaActivityType.watched,
            )
            db.add(user_activity)
        try:
            db.add(review)
            await db.commit()
            review = await db.scalar(
                select(Review)
                .options(selectinload(Review.media))
                .where(Review.id == review.id)
            )

        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Review already exists"
            )

        return {
            "id": review.id,
            "rating": review.rating,
            "content": review.content,
            "upvotes": 0,
            "downvotes": 0,
            "my_vote": None,
            "created_at": review.created_at,
            "media": {
                "id": review.media.id,
                "title": review.media.title,
                "media_type": review.media.media_type,
                "premiere_date": review.media.premiere_date,
            },
        }

    async def vote(
        self, review_id: int, vote_type: VoteType, db: AsyncSession, current_user: User
    ):

        review = await db.scalar(
            select(Review)
            .join(Review.user)
            .options(selectinload(Review.user))
            .where(Review.id == review_id, User.is_deleted.is_(False))
        )
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
            )
        existing_vote = await db.scalar(
            select(ReviewVote).where(
                ReviewVote.review_id == review_id, ReviewVote.user_id == current_user.id
            )
        )
        if not existing_vote:
            vote = ReviewVote(
                review_id=review_id, user_id=current_user.id, vote_type=vote_type
            )

            db.add(vote)
            await db.commit()
            return {"vote_type": vote.vote_type}
        if existing_vote.vote_type == vote_type:
            await db.delete(existing_vote)
            await db.commit()
            return {"vote_type": None}
        existing_vote.vote_type = vote_type
        await db.commit()
        return {"vote_type": existing_vote.vote_type}

    async def comment(
        self, review_id: int, content: str, db: AsyncSession, current_user: User
    ):

        review = await db.scalar(
            select(Review)
            .join(Review.user)
            .where(Review.id == review_id, User.is_deleted.is_(False))
        )
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
            )
        comment = Comment(review_id=review_id, user_id=current_user.id, content=content)
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        return {
            "id": comment.id,
            "content": comment.content,
            "created_at": comment.created_at,
            "user": {"id": current_user.id, "username": current_user.username},
            "review_id": review_id,
        }

    async def edit_comment(
        self,
        comment_id: int,
        update: UpdateCommentRequest,
        db: AsyncSession,
        current_user: User,
    ):

        comment = await db.scalar(
            select(Comment).where(
                Comment.id == comment_id, Comment.user_id == current_user.id
            )
        )
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
            )

        update = update.model_dump(exclude_unset=True)
        for field, value in update.items():
            setattr(comment, field, value)

        await db.commit()
        await db.refresh(comment)
        return {
            "id": comment.id,
            "content": comment.content,
            "created_at": comment.created_at,
            "user": {"id": current_user.id, "username": current_user.username},
            "review_id": comment.review_id,
        }

    async def get_comments(
        self,
        review_id: int,
        search: str,
        sort_by: SortComments,
        order: SortOrder,
        limit: int,
        page: int,
        db: AsyncSession,
        current_user: User,
    ):

        comments, review, total = await get_review_comments_query(
            review_id, search, sort_by, order, limit, page, db
        )
        results = []
        for comment in comments:
            item = {
                "id": comment.id,
                "content": comment.content,
                "created_at": comment.created_at,
                "user": {"id": comment.user_id, "username": comment.user.username},
            }

            results.append(item)

        meta = generate_meta(page, limit, total)

        vote_counts, my_vote_types = await extract_votes_of_reviews(
            [review_id], db, current_user
        )
        votes = vote_counts.get(review.id, {"upvotes": 0, "downvotes": 0})
        upvotes = votes["upvotes"]
        downvotes = votes["downvotes"]
        my_vote = my_vote_types.get(review_id)

        review = {
            "id": review.id,
            "rating": review.rating,
            "content": review.content,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "my_vote": my_vote,
            "created_at": review.created_at,
            "user": {"id": review.user_id, "username": review.user.username},
        }

        return {"meta": meta, "review": review, "results": results}


    async def get_reviews(
        self,
        tmdb_id: int,
        media_type: MediaType,
        search: str,
        author: str,
        rating: Rating,
        sort_by: SortReviews,
        sort_order: SortOrder,
        limit: int,
        page: int,
        db: AsyncSession,
        current_user: User | None,
        client: httpx.AsyncClient,
        redis_client:redis.Redis
    ):

        reviews, media, total = await extract_reviews_by_tmdb_id(
            tmdb_id,media_type, search, author, rating, sort_by, sort_order, limit, page, db, client, redis_client
        )
        review_ids = [review.id for review in reviews]
        vote_counts, my_vote_types = await extract_votes_of_reviews(
            review_ids, db, current_user
        )
        results = []
        for review in reviews:
            votes = vote_counts.get(review.id, {"upvotes": 0, "downvotes": 0})
            item = {
                "id": review.id,
                "user": {"id": review.user.id, "username": review.user.username},
                "rating": review.rating,
                "content": review.content,
                "upvotes": votes["upvotes"],
                "downvotes": votes["downvotes"],
                "my_vote": my_vote_types.get(review.id),
                "created_at": review.created_at,
            }

            results.append(item)

        meta = generate_meta(page, limit, total)
        media = {
            "tmdb_id": media.tmdb_id,
            "title": media.title,
            "media_type": media.media_type,
            "premiere_date": media.premiere_date,
        }
        return {"meta": meta, "media": media, "results": results}

    async def delete_comment(
        self, comment_id: int, db: AsyncSession, current_user: User
    ):

        comment = await db.scalar(
            select(Comment).where(
                Comment.id == comment_id, Comment.user_id == current_user.id
            )
        )
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
            )
        await db.delete(comment)
        await db.commit()

    async def get_my_reviews(
        self,
        search: str,
        rating: Rating,
        sort_by: SortMyReviews,
        sort_order: SortOrder,
        limit: int,
        page: int,
        db: AsyncSession,
        current_user: User,
    ):

        reviews, total = await extract_my_reviews(
            current_user.id, search, rating, sort_by, sort_order, limit, page, db
        )
        review_ids = [review.id for review in reviews]
        vote_counts, my_vote_types = await extract_votes_of_reviews(
            review_ids, db, current_user
        )
        results = []
        for review in reviews:
            votes = vote_counts.get(review.id, {"upvotes": 0, "downvotes": 0})
            item = {
                "id": review.id,
                "rating": review.rating,
                "content": review.content,
                "upvotes": votes["upvotes"],
                "downvotes": votes["downvotes"],
                "my_vote": my_vote_types.get(review.id),
                "created_at": review.created_at,
                "media": {
                    "id": review.media.id,
                    "title": review.media.title,
                    "media_type": review.media.media_type,
                    "premiere_date": review.media.premiere_date,
                },
            }
            results.append(item)

        meta = generate_meta(page, limit, total)

        return {"meta": meta, "results": results}

    async def get_review_by_id(
        self, review_id: int, db: AsyncSession, current_user: User
    ):

        review = await db.scalar(
            select(Review)
            .join(Review.user)
            .options(selectinload(Review.media), selectinload(Review.user))
            .where(Review.id == review_id, User.is_deleted.is_(False))
        )
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
            )

        vote_counts, my_vote_types = await extract_votes_of_reviews(
            [review_id], db, current_user
        )
        votes = vote_counts.get(review.id, {"upvotes": 0, "downvotes": 0})
        upvotes = votes["upvotes"]
        downvotes = votes["downvotes"]
        my_vote = my_vote_types.get(review_id)

        return {
            "media": {
                "id": review.media.id,
                "title": review.media.title,
                "media_type": review.media.media_type,
                "premiere_date": review.media.premiere_date,
            },
            "review": {
                "id": review.id,
                "user": {"id": review.user.id, "username": review.user.username},
                "rating": review.rating,
                "content": review.content,
                "upvotes": upvotes,
                "downvotes": downvotes,
                "my_vote": my_vote,
                "created_at": review.created_at,
            },
        }

    async def edit_review(
        self,
        review_id: int,
        update: UpdateReviewRequest,
        db: AsyncSession,
        current_user: User,
    ):

        review = await db.scalar(
            select(Review)
            .options(selectinload(Review.media))
            .where(Review.id == review_id, Review.user_id == current_user.id)
        )
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
            )

        update = update.model_dump(exclude_unset=True)
        for field, value in update.items():
            setattr(review, field, value)

        await db.commit()
        await db.refresh(review)
        vote_counts, my_vote_types = await extract_votes_of_reviews(
            [review_id], db, current_user
        )
        votes = vote_counts.get(review.id, {"upvotes": 0, "downvotes": 0})
        upvotes = votes["upvotes"]
        downvotes = votes["downvotes"]
        my_vote = my_vote_types.get(review_id)
        return {
            "id": review.id,
            "rating": review.rating,
            "content": review.content,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "my_vote": my_vote,
            "created_at": review.created_at,
            "media": {
                "id": review.media.id,
                "title": review.media.title,
                "media_type": review.media.media_type,
                "premiere_date": review.media.premiere_date,
            },
        }

    async def delete_review(self, review_id: int, db: AsyncSession, current_user: User):

        review = await db.scalar(
            select(Review).where(
                Review.id == review_id, Review.user_id == current_user.id
            )
        )
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
            )
        await db.delete(review)
        await db.commit()
