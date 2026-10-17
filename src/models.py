from datetime import UTC, date, datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base
from src.enums import (
    CodePurpose,
    MediaActivityType,
    MediaType,
    RequestStatus,
    VoteType,
    WatchlistStatus,
)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    is_private: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(default=False)
    is_admin: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verification_code: Mapped[str | None] = mapped_column(nullable=True)
    code_purpose: Mapped[CodePurpose| None] = mapped_column(default=None,nullable=True)
    verification_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    refresh_token: Mapped[str | None] = mapped_column(nullable=True)
    watchlist: Mapped[list["Watchlist"]] = relationship(
        back_populates="user", passive_deletes=True
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="user", passive_deletes=True
    )
    outgoing_follows: Mapped[list["Follow"]] = relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        back_populates="follower",
        passive_deletes=True,
    )
    incoming_follows: Mapped[list["Follow"]] = relationship(
        "Follow",
        foreign_keys="Follow.following_id",
        back_populates="following",
        passive_deletes=True,
    )
    sent_follow_requests: Mapped[list["FollowRequest"]] = relationship(
        "FollowRequest",
        foreign_keys="FollowRequest.follower_id",
        back_populates="follower",
        passive_deletes=True,
    )
    received_follow_requests: Mapped[list["FollowRequest"]] = relationship(
        "FollowRequest",
        foreign_keys="FollowRequest.following_id",
        back_populates="following",
        passive_deletes=True,
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="user", passive_deletes=True
    )
    votes: Mapped[list["ReviewVote"]] = relationship(
        back_populates="user", passive_deletes=True
    )


class Media(Base):
    __tablename__ = "media"
    __table_args__ = (UniqueConstraint("tmdb_id", "media_type"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(nullable=False)
    media_type: Mapped[MediaType] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    premiere_date: Mapped[date | None] = mapped_column(nullable=True)
    poster_path: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    last_synced: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    saved_by: Mapped[list["Watchlist"]] = relationship(back_populates="media")
    reviews: Mapped[list["Review"]] = relationship(back_populates="media")
    media_genres: Mapped[list["MediaGenre"]] = relationship(
        back_populates="media", passive_deletes=True
    )


class Watchlist(Base):
    __tablename__ = "watchlist"
    __table_args__ = (UniqueConstraint("media_id", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    status: Mapped[WatchlistStatus] = mapped_column(default=WatchlistStatus.unwatched)
    user: Mapped["User"] = relationship(back_populates="watchlist")
    media: Mapped["Media"] = relationship(back_populates="saved_by")


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("media_id", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(nullable=False)
    rating: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    media: Mapped["Media"] = relationship(back_populates="reviews")
    user: Mapped["User"] = relationship(back_populates="reviews")
    votes: Mapped[list["ReviewVote"]] = relationship(
        back_populates="review", passive_deletes=True
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="review", passive_deletes=True
    )


class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("follower_id", "following_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    following_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    follower: Mapped["User"] = relationship(
        "User", foreign_keys=[follower_id], back_populates="outgoing_follows"
    )
    following: Mapped["User"] = relationship(
        "User", foreign_keys=[following_id], back_populates="incoming_follows"
    )


class FollowRequest(Base):
    __tablename__ = "follow_requests"
    __table_args__ = (UniqueConstraint("follower_id", "following_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    following_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[RequestStatus] = mapped_column(
        default=RequestStatus.pending, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    follower: Mapped["User"] = relationship(
        "User", foreign_keys=[follower_id], back_populates="sent_follow_requests"
    )
    following: Mapped["User"] = relationship(
        "User", foreign_keys=[following_id], back_populates="received_follow_requests"
    )


class ReviewVote(Base):
    __tablename__ = "review_votes"
    __table_args__ = (UniqueConstraint("review_id", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(
        ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    vote_type: Mapped[VoteType] = mapped_column(default=VoteType.upvote, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    review: Mapped["Review"] = relationship(back_populates="votes")
    user: Mapped["User"] = relationship(back_populates="votes")


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(
        ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    review: Mapped["Review"] = relationship(back_populates="comments")
    user: Mapped["User"] = relationship(back_populates="comments")


class Genre(Base):
    __tablename__ = "genres"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    media_genres: Mapped[list["MediaGenre"]] = relationship(
        back_populates="genre", passive_deletes=True
    )


class MediaGenre(Base):
    __tablename__ = "media_genres"
    media_id: Mapped[int] = mapped_column(
        ForeignKey("media.id", ondelete="CASCADE"), primary_key=True
    )
    genre_id: Mapped[int] = mapped_column(
        ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True
    )
    media: Mapped["Media"] = relationship(back_populates="media_genres")
    genre: Mapped["Genre"] = relationship(back_populates="media_genres")


class MediaActivity(Base):
    __tablename__ = "media_activities"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    media_id: Mapped[int] = mapped_column(
        ForeignKey("media.id", ondelete="CASCADE"), primary_key=True
    )
    activity: Mapped[MediaActivityType] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
