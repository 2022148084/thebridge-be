import uuid
from datetime import datetime, timezone
from typing import Literal

from pgvector.sqlalchemy import Vector
from pydantic import EmailStr, field_validator
from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

VECTOR_DIM = 3072  # gemini-embedding-exp-03-07 default output dimension


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)
    age: int | None = None
    sex: int | None = Field(default=None, ge=0, le=2)
    city: str | None = Field(default=None, max_length=255)
    avatar_index: int | None = Field(default=None, ge=0)
    lat: float | None = None
    lng: float | None = None

    @field_validator("lat", "lng")
    @classmethod
    def round_coordinates(cls, v: float | None) -> float | None:
        if v is None:
            return None
        return round(v, 6)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    age: int | None = None
    sex: int | None = Field(default=None, ge=0, le=2)
    city: str | None = Field(default=None, max_length=255)
    avatar_index: int | None = Field(default=None, ge=0)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore[assignment]
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    age: int | None = None
    sex: int | None = Field(default=None, ge=0, le=2)
    city: str | None = Field(default=None, max_length=255)
    avatar_index: int | None = Field(default=None, ge=0)


class UserLocationUpdate(SQLModel):
    lat: float
    lng: float

    @field_validator("lat", "lng")
    @classmethod
    def round_coordinates(cls, v: float) -> float:
        return round(v, 6)


class UserLocationPublic(SQLModel):
    id: uuid.UUID
    full_name: str | None = None
    avatar_index: int | None = None
    lat: float | None = None
    lng: float | None = None


class LocationsMapPublic(SQLModel):
    me: UserLocationPublic
    friends: list[UserLocationPublic]


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


FriendshipStatus = Literal["pending", "accepted"]


class Friendship(SQLModel, table=True):
    __tablename__ = "friendship"
    __table_args__ = (
        UniqueConstraint("user_id", "friend_id", name="friendship_user_friend_key"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", index=True
    )
    friend_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", index=True
    )
    status: str = Field(default="pending", max_length=20, index=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    responded_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class FriendshipPublic(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    friend_id: uuid.UUID
    status: FriendshipStatus
    created_at: datetime | None = None
    responded_at: datetime | None = None


class FriendsPublic(SQLModel):
    data: list[UserPublic]
    count: int


class FriendRequestPublic(SQLModel):
    id: uuid.UUID
    requester: UserPublic
    created_at: datetime | None = None


class FriendRequestsPublic(SQLModel):
    data: list[FriendRequestPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore[assignment]


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


# ── New domain models ──────────────────────────────────────────────────────────


class Location(SQLModel, table=True):
    __tablename__ = "location"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255)
    city: str = Field(max_length=255)
    lat: float
    lng: float


class ChatLog(SQLModel, table=True):
    __tablename__ = "chat_log"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, ondelete="CASCADE")
    role: str = Field(max_length=50)
    message: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class UserPreferences(SQLModel, table=True):
    __tablename__ = "user_preferences"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, ondelete="CASCADE")
    core_summary: str | None = None
    core_embedding: list[float] | None = Field(
        default=None, sa_column=Column(Vector(VECTOR_DIM), nullable=True)
    )
    recent_summary: str | None = None
    recent_embedding: list[float] | None = Field(
        default=None, sa_column=Column(Vector(VECTOR_DIM), nullable=True)
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class Gathering(SQLModel, table=True):
    __tablename__ = "gathering"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    host_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, ondelete="CASCADE")
    title: str = Field(max_length=255)
    place_name: str = Field(max_length=255)
    city: str = Field(max_length=50)
    lat: float
    lng: float
    sport_type: str = Field(max_length=100)
    starts_at: datetime = Field(sa_type=DateTime(timezone=True))  # type: ignore
    duration_min: int
    max_participants: int
    level: int
    vibe: str = Field(max_length=100)
    description: str | None = None
    description_embedding: list[float] | None = Field(
        default=None, sa_column=Column(Vector(VECTOR_DIM), nullable=True)
    )
    status: int = Field(default=0)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class Participant(SQLModel, table=True):
    __tablename__ = "participant"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="gathering.id", nullable=False, ondelete="CASCADE")
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, ondelete="CASCADE")
    status: str = Field(max_length=50)
    joined_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class ParticipantPublic(SQLModel):
    id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    joined_at: datetime | None


class MatchScore(SQLModel, table=True):
    __tablename__ = "match_score"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="gathering.id", nullable=False, ondelete="CASCADE")
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, ondelete="CASCADE")
    score: float
    calculated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class Review(SQLModel, table=True):
    __tablename__ = "review"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="gathering.id", nullable=False, ondelete="CASCADE")
    reviewer_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, ondelete="CASCADE")
    rating: int
    comment: str | None = None
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


# ── Gathering API schemas ──────────────────────────────────────────────────────

SportType = Literal[
    "running", "cycling", "yoga", "stretching", "dancing", "walking", "hiking"
]
VibeTag = Literal["quiet pace", "social energy", "locked in", "reset mode"]


class GatheringBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    place_name: str = Field(max_length=255)
    city: str = Field(max_length=50)
    lat: float
    lng: float
    sport_type: SportType
    starts_at: datetime
    duration_min: int = Field(gt=0)
    max_participants: int = Field(gt=0)
    level: int = Field(ge=1, le=5)
    vibe: list[VibeTag]
    description: str | None = None
    status: int = Field(default=0, ge=0, le=2)

    @field_validator("lat", "lng")
    @classmethod
    def round_coordinates(cls, v: float) -> float:
        return round(v, 6)


class GatheringCreate(GatheringBase):
    @field_validator("vibe")
    @classmethod
    def vibe_no_duplicates(cls, v: list[str]) -> list[str]:
        if len(v) != len(set(v)):
            raise ValueError("vibe tags must be unique")
        return v


class GatheringUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    place_name: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=50)
    lat: float | None = None
    lng: float | None = None
    sport_type: SportType | None = None
    starts_at: datetime | None = None
    duration_min: int | None = Field(default=None, gt=0)
    max_participants: int | None = Field(default=None, gt=0)
    level: int | None = Field(default=None, ge=1, le=5)
    vibe: list[VibeTag] | None = None
    description: str | None = None
    status: int | None = Field(default=None, ge=0, le=2)

    @field_validator("lat", "lng", mode="before")
    @classmethod
    def round_coordinates(cls, v: float | None) -> float | None:
        return round(v, 6) if v is not None else None

    @field_validator("vibe")
    @classmethod
    def vibe_no_duplicates(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and len(v) != len(set(v)):
            raise ValueError("vibe tags must be unique")
        return v


class GatheringPublic(SQLModel):
    id: uuid.UUID
    host_id: uuid.UUID
    title: str
    place_name: str
    city: str
    lat: float
    lng: float
    sport_type: str
    starts_at: datetime
    duration_min: int
    max_participants: int
    level: int
    vibe: list[str]
    description: str | None
    status: int
    created_at: datetime | None
    updated_at: datetime | None

    @field_validator("vibe", mode="before")
    @classmethod
    def parse_vibe(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [x for x in v.split(",") if x]
        return v


class GatheringsPublic(SQLModel):
    data: list[GatheringPublic]
    count: int


class ParticipatingGatheringPublic(GatheringPublic):
    participant_id: uuid.UUID
    participant_status: str
    joined_at: datetime | None


class ParticipatingGatheringsPublic(SQLModel):
    data: list[ParticipatingGatheringPublic]
    count: int


# ── Chat & Preferences API schemas ────────────────────────────────────────────

class ChatMessageInput(SQLModel):
    message: str


class ChatMessagePublic(SQLModel):
    id: uuid.UUID
    role: str
    message: str
    created_at: datetime | None


class ChatHistoryPublic(SQLModel):
    data: list[ChatMessagePublic]


class UserPreferencesPublic(SQLModel):
    core_summary: str | None
    recent_summary: str | None
    updated_at: datetime | None


class GatheringRecommendPublic(GatheringPublic):
    match_percentage: float  # 0.0 ~ 100.0


class GatheringsRecommendPublic(SQLModel):
    data: list[GatheringRecommendPublic]
    count: int


class ChatResponse(SQLModel):
    message: ChatMessagePublic
    recommendations: list[GatheringRecommendPublic] | None = None
