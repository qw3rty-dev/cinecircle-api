import httpx
import redis.asyncio as redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.common.utils import generate_meta, get_media_info
from src.enums import MediaActivityType, MediaType
from src.media.service import get_genre_names
from src.models import Follow, Media, MediaActivity, Review, User
from src.reviews.service import extract_votes_of_reviews
from src.services.tmdb.service import get_recommendation

ACTIVITY_SCORE = {
    MediaActivityType.loved: 5,
    MediaActivityType.liked: 3,
    MediaActivityType.disliked: -5,
    "reviewed": 2,
}


async def following_activity_reviews(
    limit: int, page: int, db: AsyncSession, current_user: User
):

    following = (
        await db.scalars(
            select(Follow.following_id)
            .join(Follow.following)
            .where(Follow.follower_id == current_user.id, User.is_deleted.is_(False))
        )
    ).all()
    if not following:
        meta = generate_meta(page, limit, 0)
        return [], meta
    query = (
        select(Review)
        .options(selectinload(Review.media), selectinload(Review.user))
        .where(Review.user_id.in_(following))
        .order_by(Review.created_at.desc())
    )
    total = await db.scalar(select(func.count()).where(Review.user_id.in_(following)))
    offset = (page - 1) * limit
    query = query.limit(limit).offset(offset)
    following_reviews = (await db.scalars(query)).all()
    meta = generate_meta(page, limit, total)

    return following_reviews, meta


async def get_user_sentiments(
    media_type: MediaType | None, db: AsyncSession, user_ids: list
):

    query = (
        select(Media.tmdb_id, Media.media_type, MediaActivity.activity)
        .join(MediaActivity, Media.id == MediaActivity.media_id)
        .where(
            MediaActivity.user_id.in_(user_ids),
            MediaActivity.activity != MediaActivityType.watched,
        )
    )
    if media_type:
        query = query.where(Media.media_type == media_type)
    data = (await db.execute(query)).all()
    if not data:
        return []
    user_activity = []
    for tmdb_id, media_type, activity in data:
        user_activity.append(
            {"tmdb_id": tmdb_id, "media_type": media_type, "activity": activity}
        )

    return user_activity


async def get_following_activity(
    media_type: MediaType | None, db: AsyncSession, current_user: User
):

    following = (
        await db.scalars(
            select(Follow.following_id)
            .join(Follow.following)
            .where(Follow.follower_id == current_user.id, User.is_deleted.is_(False))
        )
    ).all()
    if not following:
        return []
    query = (
        select(Media.tmdb_id, Media.media_type)
        .join(Review.media)
        .where(Review.user_id.in_(following), Review.rating > 0)
    )
    if media_type:
        query = query.where(Media.media_type == media_type)
    following_review_activity = (await db.execute(query)).all()
    following_media_activity = await get_user_sentiments(media_type, db, following)
    for tmdb_id, media_type in following_review_activity:
        following_media_activity.append(
            {"tmdb_id": tmdb_id, "media_type": media_type, "activity": "reviewed"}
        )
    return following_media_activity


def score_media_for_recommendations(
    user_activity: list | None, following_activity: list | None
):

    scored_media = dict()
    for item in user_activity:
        key = (item["tmdb_id"], item["media_type"])
        if key in scored_media:
            scored_media[key] += ACTIVITY_SCORE[item["activity"]]
        else:
            scored_media[key] = ACTIVITY_SCORE[item["activity"]]

    for item in following_activity:
        key = (item["tmdb_id"], item["media_type"])
        if key in scored_media:
            scored_media[key] += ACTIVITY_SCORE[item["activity"]]
        else:
            scored_media[key] = ACTIVITY_SCORE[item["activity"]]

    return scored_media


async def recommendation_candidates(
    media_type: MediaType | None, db: AsyncSession, current_user: User
):

    user_activity = await get_user_sentiments(media_type, db, [current_user.id])
    following_activity = await get_following_activity(media_type, db, current_user)
    scored_media = score_media_for_recommendations(user_activity, following_activity)
    if not scored_media:
        return {}
    sorted_ids = dict(sorted(scored_media.items(), key=lambda x: x[1], reverse=True))
    top_five = dict(list(sorted_ids.items())[:5])
    candidates = {
        tmdb_id: media_type
        for (tmdb_id, media_type), score in top_five.items()
        if score > 0
    }

    return candidates


async def watched_ids(db: AsyncSession, current_user: User):
    query = (
        select(Media.tmdb_id, Media.media_type)
        .join(MediaActivity, Media.id == MediaActivity.media_id)
        .where(
            MediaActivity.user_id == current_user.id,
            MediaActivity.activity == MediaActivityType.watched,
        )
    )
    watched = (await db.execute(query)).all()
    return {(tmdb_id, media_type) for tmdb_id, media_type in watched}


async def recommendations(
    media_type: MediaType | None,
    page: int,
    db: AsyncSession,
    client: httpx.AsyncClient,
    redis_client: redis,
    current_user: User,
):
    candidates = await recommendation_candidates(media_type, db, current_user)
    if not candidates:
        return {"page": page, "results": []}
    candidates_items = list(candidates.items())
    if not 1 <= page <= len(candidates_items):
        return {"page": page, "results": []}
    (selected_id, selected_media_type) = candidates_items[page - 1]
    results = (await get_recommendation(selected_media_type, selected_id, redis_client, client))[
        "results"
    ]
    watched = await watched_ids(db, current_user)
    genres_info = await get_genre_names(db)
    recommendation_results = []
    for item in results:
        if (item["id"], selected_media_type) not in watched:
            recommendation_results.append(
                get_media_info(
                    item, item.get("media_type", selected_media_type.value), genres_info
                )
            )
    return {"page": page, "results": recommendation_results}


class FeedService:
    async def get_recommendations(
        self,
        media_type: MediaType | None,
        page,
        db: AsyncSession,
        client: httpx.AsyncClient,
        redis_client: redis,
        current_user: User,
    ):
        return await recommendations(media_type, page, db, client,redis_client, current_user)

    async def following_activity_reviews(
        self, limit: int, page: int, db: AsyncSession, current_user: User
    ):
        reviews, meta = await following_activity_reviews(limit, page, db, current_user)

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
                "media": {
                    "id": review.media.id,
                    "title": review.media.title,
                    "media_type": review.media.media_type,
                    "premiere_date": review.media.premiere_date,
                },
            }
            results.append(item)

        return {"meta": meta, "reviews": results}
