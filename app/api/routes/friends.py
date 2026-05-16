import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import and_, or_
from sqlmodel import col, delete, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    FriendRequestPublic,
    FriendRequestsPublic,
    Friendship,
    FriendshipPublic,
    FriendsPublic,
    Message,
    User,
    UserPublic,
    get_datetime_utc,
)

router = APIRouter(prefix="/friends", tags=["friends"])

FRIENDSHIP_PENDING = "pending"
FRIENDSHIP_ACCEPTED = "accepted"


def _get_friendship_between(
    *, session: SessionDep, user_id: uuid.UUID, friend_id: uuid.UUID
) -> Friendship | None:
    statement = select(Friendship).where(
        or_(
            and_(
                col(Friendship.user_id) == user_id,
                col(Friendship.friend_id) == friend_id,
            ),
            and_(
                col(Friendship.user_id) == friend_id,
                col(Friendship.friend_id) == user_id,
            ),
        )
    )
    return session.exec(statement).first()


def _get_other_user_id(
    *, friendship: Friendship, current_user_id: uuid.UUID
) -> uuid.UUID:
    if friendship.user_id == current_user_id:
        return friendship.friend_id
    return friendship.user_id


@router.get("/", response_model=FriendsPublic)
def read_friends(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    query = select(Friendship).where(
        col(Friendship.status) == FRIENDSHIP_ACCEPTED,
        or_(
            col(Friendship.user_id) == current_user.id,
            col(Friendship.friend_id) == current_user.id,
        ),
    )
    count = session.exec(select(func.count()).select_from(query.subquery())).one()
    friendships = session.exec(
        query.order_by(
            col(Friendship.responded_at).desc(),
            col(Friendship.created_at).desc(),
        )
        .offset(skip)
        .limit(limit)
    ).all()

    friends: list[UserPublic] = []
    for friendship in friendships:
        friend = session.get(
            User,
            _get_other_user_id(
                friendship=friendship, current_user_id=current_user.id
            ),
        )
        if friend:
            friends.append(UserPublic.model_validate(friend))
    return FriendsPublic(
        data=friends,
        count=count,
    )


@router.get("/requests", response_model=FriendRequestsPublic)
def read_friend_requests(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    query = select(Friendship).where(
        col(Friendship.friend_id) == current_user.id,
        col(Friendship.status) == FRIENDSHIP_PENDING,
    )
    count = session.exec(select(func.count()).select_from(query.subquery())).one()
    requests = session.exec(
        query.order_by(col(Friendship.created_at).desc()).offset(skip).limit(limit)
    ).all()

    data: list[FriendRequestPublic] = []
    for request in requests:
        requester = session.get(User, request.user_id)
        if requester:
            data.append(
                FriendRequestPublic(
                    id=request.id,
                    requester=UserPublic.model_validate(requester),
                    created_at=request.created_at,
                )
            )
    return FriendRequestsPublic(data=data, count=count)


@router.post("/{friend_id}", response_model=FriendshipPublic)
def add_friend(
    session: SessionDep,
    current_user: CurrentUser,
    friend_id: uuid.UUID,
) -> Any:
    if friend_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot add yourself as a friend")

    friend = session.get(User, friend_id)
    if not friend or not friend.is_active:
        raise HTTPException(status_code=404, detail="User not found")

    existing_friendship = _get_friendship_between(
        session=session, user_id=current_user.id, friend_id=friend_id
    )
    if existing_friendship:
        return existing_friendship

    friendship = Friendship(
        user_id=current_user.id,
        friend_id=friend_id,
        status=FRIENDSHIP_PENDING,
    )
    session.add(friendship)
    session.commit()
    session.refresh(friendship)
    return friendship


@router.post("/requests/{request_id}/accept", response_model=Message)
def accept_friend_request(
    session: SessionDep,
    current_user: CurrentUser,
    request_id: uuid.UUID,
) -> Message:
    friendship = session.get(Friendship, request_id)
    if (
        not friendship
        or friendship.friend_id != current_user.id
        or friendship.status != FRIENDSHIP_PENDING
    ):
        raise HTTPException(status_code=404, detail="Friend request not found")

    friendship.status = FRIENDSHIP_ACCEPTED
    friendship.responded_at = get_datetime_utc()
    session.add(friendship)
    session.commit()
    return Message(message="Friend request accepted successfully")


@router.post("/requests/{request_id}/reject", response_model=Message)
def reject_friend_request(
    session: SessionDep,
    current_user: CurrentUser,
    request_id: uuid.UUID,
) -> Message:
    friendship = session.get(Friendship, request_id)
    if (
        not friendship
        or friendship.friend_id != current_user.id
        or friendship.status != FRIENDSHIP_PENDING
    ):
        raise HTTPException(status_code=404, detail="Friend request not found")

    session.delete(friendship)
    session.commit()
    return Message(message="Friend request rejected successfully")


@router.delete("/{friend_id}", response_model=Message)
def delete_friend(
    session: SessionDep,
    current_user: CurrentUser,
    friend_id: uuid.UUID,
) -> Message:
    statement = delete(Friendship).where(
        col(Friendship.status) == FRIENDSHIP_ACCEPTED,
        or_(
            and_(
                col(Friendship.user_id) == current_user.id,
                col(Friendship.friend_id) == friend_id,
            ),
            and_(
                col(Friendship.user_id) == friend_id,
                col(Friendship.friend_id) == current_user.id,
            ),
        )
    )
    session.exec(statement)
    session.commit()
    return Message(message="Friend deleted successfully")
