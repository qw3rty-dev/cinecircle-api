from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.common.schemas import PaginationMeta
from src.enums import RelationshipStatus


class UserProfile(BaseModel):
    username: str
    is_private: bool = True
    followers: int
    following: int
    my_profile: bool
    relationship_status: RelationshipStatus|None
    can_view_content: bool
    model_config = ConfigDict(from_attributes=True)


class FollowRequestResponse(BaseModel):
    request_id: int
    username: str
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class FollowAccountResponse(BaseModel):
    username: str
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaginatedFollowRequestResponse(BaseModel):
    meta: PaginationMeta
    results: list[FollowRequestResponse]
    model_config = ConfigDict(from_attributes=True)


class PaginatedUserResponse(BaseModel):
    meta: PaginationMeta
    results: list[FollowAccountResponse]
    model_config = ConfigDict(from_attributes=True)


class PrivacyPreference(BaseModel):
    is_private: bool
    model_config = ConfigDict(from_attributes=True)
