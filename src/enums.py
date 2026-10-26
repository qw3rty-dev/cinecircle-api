from enum import Enum


class MediaType(str, Enum):
    tv = "tv"
    movie = "movie"


class SearchMediaType(str, Enum):
    movie = "movie"
    tv = "tv"
    all = "all"


class RequestStatus(str, Enum):
    pending = "pending"


class Action(str, Enum):
    accept = "accept"
    reject = "reject"


class BulkAction(str, Enum):
    accept_all = "accept_all"
    reject_all = "reject_all"


class VoteType(str, Enum):
    upvote = "upvote"
    downvote = "downvote"


class SortComments(str, Enum):
    created_at = "created_at"
    username = "username"


class SortWatchlist(str, Enum):
    created_at = "created_at"
    title = "title"


class WatchlistStatus(str, Enum):
    unwatched = "unwatched"
    watching = "watching"
    watched = "watched"


class SortReviews(str, Enum):
    created_at = "created_at"
    username = "username"
    rating = "rating"


class SortMyReviews(str, Enum):
    created_at = "created_at"
    title = "title"
    rating = "rating"


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class Rating(int, Enum):
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5


class SortUsers(str, Enum):
    username = "username"
    created_at = "created_at"
    last_login = "last_login"

class SortVerificationRequests(str, Enum):
    username = "username"
    created_at = "created_at"
    last_login = "last_login"
    request_created_at = "request_created_at"


class MediaActivityType(str, Enum):
    watched = "watched"
    loved = "loved"
    liked = "liked"
    disliked = "disliked"


class CodePurpose(str, Enum):
    password_reset = "password_reset"
    verification_otp = "verification_otp"

class RelationshipStatus(str, Enum):
    self = "self"
    following = "following"
    follow_request_sent = "follow_request_sent"