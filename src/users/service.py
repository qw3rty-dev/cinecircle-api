from fastapi import HTTPException, status
from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.common.utils import generate_meta
from src.enums import Action, BulkAction, RelationshipStatus, SortOrder, SortUsers
from src.models import Follow, FollowRequest, User


async def get_incoming_follow_requests(
    user: User,
    search: str,
    limit: int,
    page: int,
    sort_by: SortUsers,
    sort_order: SortOrder,
    db: AsyncSession,
):

    query = select(FollowRequest).where(FollowRequest.following_id == user.id)
    query = (
        query.join(FollowRequest.follower)
        .options(selectinload(FollowRequest.follower))
        .where(User.is_deleted.is_(False))
    )
    if search:
        search = search.strip().lower()
        query = query.where(User.username.ilike(f"{search}%"))

    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    sort_fields = {
        SortUsers.created_at: FollowRequest.created_at,
        SortUsers.username: func.lower(User.username),
    }
    sort_expression = sort_fields[sort_by]
    order = (
        sort_expression.asc() if sort_order == SortOrder.asc else sort_expression.desc()
    )
    query = query.order_by(order, FollowRequest.id.desc())
    offset = (page - 1) * limit
    query = query.limit(limit).offset(offset)
    request_list = (await db.scalars(query)).all()
    results = []
    for request in request_list:
        account = {
            "request_id": request.id,
            "username": request.follower.username,
            "user_id": request.follower_id,
            "created_at": request.created_at,
        }
        results.append(account)
    return results, total

async def get_outgoing_follow_requests(
    user: User,
    search: str,
    limit: int,
    page: int,
    sort_by: SortUsers,
    sort_order: SortOrder,
    db: AsyncSession,
):

    query = select(FollowRequest).where(FollowRequest.follower_id == user.id)
    query = (
        query.join(FollowRequest.following)
        .options(selectinload(FollowRequest.following))
        .where(User.is_deleted.is_(False))
    )
    if search:
        search = search.strip().lower()
        query = query.where(User.username.ilike(f"{search}%"))

    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    sort_fields = {
        SortUsers.created_at: FollowRequest.created_at,
        SortUsers.username: func.lower(User.username),
    }
    sort_expression = sort_fields[sort_by]
    order = (
        sort_expression.asc() if sort_order == SortOrder.asc else sort_expression.desc()
    )
    query = query.order_by(order, FollowRequest.id.desc())
    offset = (page - 1) * limit
    query = query.limit(limit).offset(offset)
    request_list = (await db.scalars(query)).all()
    results = []
    for request in request_list:
        account = {
            "request_id": request.id,
            "username": request.following.username,
            "user_id": request.following_id,
            "created_at": request.created_at,
        }
        results.append(account)
    return results, total


async def check_profile_access(user_id: int, current_user: User, db: AsyncSession):

    user = await db.scalar(
        select(User).where(User.id == user_id, User.is_deleted.is_(False))
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if not current_user.is_verified:
        if user.id == current_user.id:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email to use this feature.",
        )
    if not user.is_private or user.id == current_user.id:
        return user

    is_following = await db.scalar(
        select(
            exists().where(
                Follow.follower_id == current_user.id, Follow.following_id == user_id
            )
        )
    )

    if not is_following:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User profile is private"
        )
    return user


async def get_followers(
    user: User,
    search: str,
    limit: int,
    page: int,
    sort_by: SortUsers,
    sort_order: SortOrder,
    db: AsyncSession,
):

    query = select(Follow).where(Follow.following_id == user.id)
    query = (
        query.join(Follow.follower)
        .options(selectinload(Follow.follower))
        .where(User.is_deleted.is_(False))
    )
    if search:
        search = search.strip().lower()
        query = query.where(User.username.ilike(f"{search}%"))

    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    sort_fields = {
        SortUsers.created_at: Follow.created_at,
        SortUsers.username: func.lower(User.username),
    }
    sort_expression = sort_fields[sort_by]
    order = (
        sort_expression.asc() if sort_order == SortOrder.asc else sort_expression.desc()
    )
    query = query.order_by(order, Follow.id.desc())
    offset = (page - 1) * limit
    query = query.limit(limit).offset(offset)
    follower_list = (await db.scalars(query)).all()
    results = []
    for follower in follower_list:
        account = {
            "username": follower.follower.username,
            "user_id": follower.follower_id,
            "created_at": follower.created_at,
        }
        results.append(account)
    return results, total


async def get_following(
    user: User,
    search: str,
    limit: int,
    page: int,
    sort_by: SortUsers,
    sort_order: SortOrder,
    db: AsyncSession,
):
    query = select(Follow).where(Follow.follower_id == user.id)
    query = (
        query.join(Follow.following)
        .options(selectinload(Follow.following))
        .where(User.is_deleted.is_(False))
    )

    if search:
        search = search.strip().lower()
        query = query.where(User.username.ilike(f"{search}%"))
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    sort_fields = {
        SortUsers.created_at: Follow.created_at,
        SortUsers.username: func.lower(User.username),
    }

    sort_expression = sort_fields[sort_by]
    order = (
        sort_expression.asc() if sort_order == SortOrder.asc else sort_expression.desc()
    )
    query = query.order_by(order, Follow.id.desc())
    offset = (page - 1) * limit
    query = query.limit(limit).offset(offset)
    following_list = (await db.scalars(query)).all()
    results = []
    for following in following_list:
        account = {
            "username": following.following.username,
            "user_id": following.following_id,
            "created_at": following.created_at,
        }
        results.append(account)
    return results, total


async def search_user_results(
    search: str,
    limit: int,
    page: int,
    sort_by: SortUsers,
    sort_order: SortOrder,
    db: AsyncSession,
):
    search = search.strip().lower()
    query = select(User).where(
        User.username.ilike(f"{search}%"), User.is_deleted.is_(False)
    )
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    sort_fields = {
        SortUsers.created_at: User.created_at,
        SortUsers.username: func.lower(User.username),
    }

    sort_expression = sort_fields[sort_by]
    order = (
        sort_expression.asc() if sort_order == SortOrder.asc else sort_expression.desc()
    )
    query = query.order_by(order, User.id.desc())
    offset = (page - 1) * limit
    query = query.limit(limit).offset(offset)
    users = (await db.scalars(query)).all()
    results = []
    for user in users:
        account = {
            "username": user.username,
            "user_id": user.id,
            "created_at": user.created_at,
        }
        results.append(account)
    return results, total


class UserService:
    async def show_user_profile(self, id: int, current_user: User, db: AsyncSession):

        user = await db.scalar(
            select(User).where(User.id == id, User.is_deleted.is_(False))
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        my_profile = current_user.id == id

        if not current_user.is_verified:
            if not my_profile:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Please verify your email to use this feature.",
                 )
            can_view_content = True
            relationship_status = "self"
                
        else:
            is_following = await db.scalar(
                    select(
                        exists().where(
                            Follow.follower_id == current_user.id,
                            Follow.following_id == user.id,
                        )
                    )
                )
            can_view_content = my_profile or not user.is_private or is_following
            pending_follow_request = False
            if not is_following:
                pending_follow_request = await db.scalar(
                    select(
                        exists().where(
                            FollowRequest.follower_id == current_user.id,
                            FollowRequest.following_id == user.id,
                        )
                    )
                )
            relationship_status = None
            if my_profile:
                relationship_status = RelationshipStatus.self
            if is_following:
                relationship_status = RelationshipStatus.following
            if pending_follow_request:
                relationship_status = RelationshipStatus.follow_request_sent

        followers_len = await db.scalar(
            select(func.count())
            .join(Follow.follower)
            .where(Follow.following_id == user.id, User.is_deleted.is_(False))
        )
        following_len = await db.scalar(
            select(func.count())
            .join(Follow.following)
            .where(Follow.follower_id == user.id, User.is_deleted.is_(False))
        )
        

        return {
            "username": user.username,
            "is_private": user.is_private,
            "followers": followers_len,
            "following": following_len,
            "my_profile": my_profile,
            "relationship_status": relationship_status,
            "can_view_content": can_view_content,
        }

    async def search_user(
        self,
        search: str,
        limit: int,
        page: int,
        sort_by: SortUsers,
        sort_order: SortOrder,
        db: AsyncSession,
    ):
        total = 0
        users = []
        if search.strip():
            users, total = await search_user_results(
                search, limit, page, sort_by, sort_order, db
            )

        meta = generate_meta(page, limit, total)
        return {"meta": meta, "results": users}

    async def follow_user(self, user_id: int, db: AsyncSession, current_user: User):

        user = await db.scalar(
            select(User).where(User.id == user_id, User.is_deleted.is_(False))
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot follow yourself",
            )

        existing_follow = await db.scalar(
            select(
                exists().where(
                    Follow.follower_id == current_user.id,
                    Follow.following_id == user_id,
                )
            )
        )
        if existing_follow:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Already following"
            )

        existing_follow_request = await db.scalar(
            select(FollowRequest).where(
                FollowRequest.follower_id == current_user.id,
                FollowRequest.following_id == user_id,
            )
        )
        if user.is_private:
            if existing_follow_request:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Request already sent"
                )
            new_follow_request = FollowRequest(
                follower_id=current_user.id, following_id=user_id
            )
            try:
                db.add(new_follow_request)
                await db.commit()
                await db.refresh(new_follow_request)
                return {"message": "Follow request sent"}
            except IntegrityError:
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Request already sent"
                )

        if existing_follow_request:
            await db.delete(existing_follow_request)

        new_following = Follow(follower_id=current_user.id, following_id=user_id)
        try:
            db.add(new_following)
            await db.commit()
            await db.refresh(new_following)
            return {"message": "Following"}
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Already following"
            )

    async def unfollow_user_or_unsend_request(
        self, user_id: int, db: AsyncSession, current_user: User
    ):

        existing_follow = await db.scalar(
            select(Follow)
            .join(Follow.following)
            .where(
                Follow.follower_id == current_user.id,
                Follow.following_id == user_id,
                User.is_deleted.is_(False),
            )
        )

        if not existing_follow:
            existing_follow_request = await db.scalar(
                select(FollowRequest)
                .join(FollowRequest.following)
                .where(
                    FollowRequest.follower_id == current_user.id,
                    FollowRequest.following_id == user_id,
                    User.is_deleted.is_(False),
                )
            )

            if not existing_follow_request:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No follow or follow request exists",
                )
            await db.delete(existing_follow_request)
            await db.commit()
            return

        await db.delete(existing_follow)
        await db.commit()
        return

    async def request_action(
        self, request_id: int, action: Action, db: AsyncSession, current_user: User
    ):
        request = await db.scalar(
            select(FollowRequest)
            .join(FollowRequest.follower)
            .options(selectinload(FollowRequest.follower))
            .where(
                FollowRequest.id == request_id,
                FollowRequest.following_id == current_user.id,
                User.is_deleted.is_(False),
            )
        )
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Request not found"
            )

        if action == Action.accept:
            new_follow = Follow(
                follower_id=request.follower_id, following_id=request.following_id
            )
            try:
                db.add(new_follow)
                await db.delete(request)
                await db.commit()
                await db.refresh(new_follow)
            except IntegrityError:
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Already accepted"
                )
            return {"message": "Request accepted"}
        if action == Action.reject:
            await db.delete(request)
            await db.commit()
            return {"message": "Request rejected"}

    async def request_action_bulk(
        self, action: BulkAction, db: AsyncSession, current_user: User
    ):
        requests = (
            await db.scalars(
                select(FollowRequest)
                .join(FollowRequest.follower)
                .options(selectinload(FollowRequest.follower))
                .where(
                    FollowRequest.following_id == current_user.id,
                    User.is_deleted.is_(False),
                )
            )
        ).all()
        if not requests:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No pending request"
            )

        if action == BulkAction.accept_all:
            for request in requests:
                new_follow = Follow(
                    follower_id=request.follower_id, following_id=request.following_id
                )
                db.add(new_follow)
                await db.delete(request)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Could not accept requests",
                )
            return {"message": "Requests accepted"}

        if action == BulkAction.reject_all:
            for request in requests:
                await db.delete(request)
            await db.commit()
            return {"message": "Requests rejected"}

    async def show_follow_requests_received(
        self,
        search: str,
        limit: int,
        page: int,
        sort_by: SortUsers,
        sort_order: SortOrder,
        db: AsyncSession,
        current_user: User,
    ):

        follow_requests, total = await get_incoming_follow_requests(
            current_user, search, limit, page, sort_by, sort_order, db
        )
        meta = generate_meta(page, limit, total)

        return {"meta": meta, "results": follow_requests}
    
    async def show_follow_requests_sent(
        self,
        search: str,
        limit: int,
        page: int,
        sort_by: SortUsers,
        sort_order: SortOrder,
        db: AsyncSession,
        current_user: User,
    ):

        follow_requests, total = await get_outgoing_follow_requests(
            current_user, search, limit, page, sort_by, sort_order, db
        )
        meta = generate_meta(page, limit, total)

        return {"meta": meta, "results": follow_requests}

    async def show_followers(
        self,
        user_id: int,
        search: str,
        limit: int,
        page: int,
        sort_by: SortUsers,
        sort_order: SortOrder,
        db: AsyncSession,
        current_user: User,
    ):

        user = await check_profile_access(user_id, current_user, db)

        followers, total = await get_followers(
            user, search, limit, page, sort_by, sort_order, db
        )
        meta = generate_meta(page, limit, total)

        return {"meta": meta, "results": followers}

    async def show_following(
        self,
        user_id: int,
        search: str,
        limit: int,
        page: int,
        sort_by: SortUsers,
        sort_order: SortOrder,
        db: AsyncSession,
        current_user: User,
    ):

        user = await check_profile_access(user_id, current_user, db)

        following, total = await get_following(
            user, search, limit, page, sort_by, sort_order, db
        )
        meta = generate_meta(page, limit, total)

        return {"meta": meta, "results": following}

    async def privacy_preferences(
        self, is_private: bool, db: AsyncSession, current_user: User
    ):

        if current_user.is_private != is_private:
            current_user.is_private = is_private
            await db.commit()
        return {"is_private": current_user.is_private}
