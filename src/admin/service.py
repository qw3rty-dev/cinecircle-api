from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, literal, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.utils import generate_meta
from src.enums import CodePurpose, MediaType, SortOrder, SortUsers, SortVerificationRequests
from src.models import Comment, Follow, Media, Review, User, Watchlist


class AdminService:
    async def get_users(
        self,
        search: str,
        deactivated: bool,
        verified: bool,
        private: bool,
        limit: int,
        page: int,
        sort_by: SortUsers,
        sort_order: SortOrder,
        db: AsyncSession,
    ):

        query = select(User)

        if search:
            query = query.where(
                or_(User.username.ilike(f"{search}%"), User.email.ilike(f"{search}%"))
            )
        if deactivated is not None:
            query = query.where(User.is_deleted == deactivated)
        if verified is not None:
            query = query.where(User.is_verified == verified)
        if private is not None:
            query = query.where(User.is_private == private)

        sort_fields = {
            SortUsers.created_at: User.created_at,
            SortUsers.username: User.username,
            SortUsers.last_login: User.last_login,
        }
        sort_expression = sort_fields[sort_by]
        order = (
            sort_expression.asc()
            if sort_order == SortOrder.asc
            else sort_expression.desc()
        )
        query = query.order_by(order.nulls_last(), User.created_at.desc())
        total = await db.scalar(select(func.count()).select_from(query.subquery()))
        offset = (page - 1) * limit
        query = query.limit(limit).offset(offset)
        users = (await db.scalars(query)).all()
        meta = generate_meta(page, limit, total)
        return {"meta": meta, "results": users}


    async def show_verification_requests(
            self,
            search: str,
            expired:bool,
            private: bool,
            limit: int,
            page: int,
            sort_by: SortVerificationRequests,
            sort_order: SortOrder,
            db:AsyncSession):
        
        now = datetime.now(UTC)
        query = select(User).where(User.verification_code.is_not(None),User.code_purpose == CodePurpose.verification_otp)
        if search:
            query = query.where(
                or_(User.username.ilike(f"{search}%"), User.email.ilike(f"{search}%"))
            )
        if expired is True:
            query = query.where(User.verification_expires_at<now)
        if expired is False:
            query = query.where(User.verification_expires_at>now)
        if private is not None:
            query = query.where(User.is_private == private)
        
        sort_fields = {
            SortVerificationRequests.created_at: User.created_at,
            SortVerificationRequests.username: User.username,
            SortVerificationRequests.last_login: User.last_login,
            SortVerificationRequests.request_created_at: User.verification_expires_at
        }
        sort_expression = sort_fields[sort_by]
        order = (
            sort_expression.asc()
            if sort_order == SortOrder.asc
            else sort_expression.desc()
        )

        query = query.order_by(order.nulls_last(), User.created_at.desc())
        total = await db.scalar(select(func.count()).select_from(query.subquery()))
        offset = (page - 1) * limit
        query = query.limit(limit).offset(offset)

        requests = []
        users = (await db.scalars(query)).all()

        for user in users:
            requests.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_verified": user.is_verified,
                "code_purpose": user.code_purpose,
                "request_created_at": user.verification_expires_at - timedelta(minutes=10)
                }
            )
        meta = generate_meta(page, limit, total)
        return {"meta": meta, "results": requests}

        
        
    async def verify_users_manually(
            self,
            user_id: int,
            db: AsyncSession
    ):
        user = await db.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")
        if user.is_verified:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="User already verified")
        user.is_verified = True
        if user.verification_expires_at:
            user.verification_code = None
            user.verification_expires_at = None
            user.code_purpose = None
        await db.commit()
        return {"message":"Verification done"}

    async def get_cinecircle_stats(self, db: AsyncSession):

        q1 = select(
            literal("total_users"), func.count().label("total_users")
        ).select_from(User)
        q2 = (
            select(literal("active_users"), func.count().label("active_users"))
            .select_from(User)
            .where(User.is_deleted.is_(False))
        )
        q3 = (
            select(literal("deleted_users"), func.count().label("deleted_users"))
            .select_from(User)
            .where(User.is_deleted.is_(True))
        )
        q4 = select(
            literal("total_reviews"), func.count().label("total_reviews")
        ).select_from(Review)
        q5 = select(
            literal("total_comments"), func.count().label("total_comments")
        ).select_from(Comment)
        q6 = select(
            literal("total_media"), func.count().label("total_media")
        ).select_from(Media)
        q7 = (
            select(literal("movies"), func.count().label("movies"))
            .select_from(Media)
            .where(Media.media_type == MediaType.movie)
        )
        q8 = (
            select(literal("tv_shows"), func.count().label("tv_shows"))
            .select_from(Media)
            .where(Media.media_type == MediaType.tv)
        )
        q9 = select(
            literal("total_follows"), func.count().label("total_follows")
        ).select_from(Follow)
        q10 = select(
            literal("total_watchlist_entries"),
            func.count().label("total_watchlist_entries"),
        ).select_from(Watchlist)

        queries = [q1, q2, q3, q4, q5, q6, q7, q8, q9, q10]
        query = union_all(*queries)
        rows = (await db.execute(query)).all()
        results = {}
        for x, y in rows:
            results[x] = y
        return results

    async def delete_comment(self, comment_id: int, db: AsyncSession):

        comment = await db.scalar(select(Comment).where(Comment.id == comment_id))
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
            )
        await db.delete(comment)
        await db.commit()

    async def delete_review(self, review_id: int, db: AsyncSession):

        review = await db.scalar(select(Review).where(Review.id == review_id))
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
            )
        await db.delete(review)
        await db.commit()
