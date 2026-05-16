import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Gathering,
    GatheringCreate,
    GatheringPublic,
    GatheringsPublic,
    GatheringUpdate,
    Message,
    get_datetime_utc,
)

router = APIRouter(prefix="/gatherings", tags=["gatherings"])


def _to_public(g: Gathering) -> GatheringPublic:
    return GatheringPublic.model_validate(g)


@router.get("/", response_model=GatheringsPublic)
def read_gatherings(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    sport_type: str | None = None,
    city: str | None = None,
    status: int | None = None,
) -> Any:
    query = select(Gathering)
    if sport_type:
        query = query.where(Gathering.sport_type == sport_type)
    if city:
        query = query.where(Gathering.city == city)
    if status is not None:
        query = query.where(Gathering.status == status)
    count = session.exec(select(func.count()).select_from(query.subquery())).one()
    gatherings = session.exec(
        query.order_by(col(Gathering.starts_at).asc()).offset(skip).limit(limit)
    ).all()
    return GatheringsPublic(data=[_to_public(g) for g in gatherings], count=count)


@router.get("/{id}", response_model=GatheringPublic)
def read_gathering(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    gathering = session.get(Gathering, id)
    if not gathering:
        raise HTTPException(status_code=404, detail="Gathering not found")
    return _to_public(gathering)


@router.post("/", response_model=GatheringPublic)
def create_gathering(
    *, session: SessionDep, current_user: CurrentUser, gathering_in: GatheringCreate
) -> Any:
    vibe_str = ",".join(gathering_in.vibe)
    gathering = Gathering.model_validate(
        gathering_in, update={"host_id": current_user.id, "vibe": vibe_str}
    )
    session.add(gathering)
    session.commit()
    session.refresh(gathering)
    return _to_public(gathering)


@router.put("/{id}", response_model=GatheringPublic)
def update_gathering(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    gathering_in: GatheringUpdate,
) -> Any:
    gathering = session.get(Gathering, id)
    if not gathering:
        raise HTTPException(status_code=404, detail="Gathering not found")
    if not current_user.is_superuser and gathering.host_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    update_data = gathering_in.model_dump(exclude_unset=True)
    if "vibe" in update_data and update_data["vibe"] is not None:
        update_data["vibe"] = ",".join(update_data["vibe"])
    update_data["updated_at"] = get_datetime_utc()
    gathering.sqlmodel_update(update_data)
    session.add(gathering)
    session.commit()
    session.refresh(gathering)
    return _to_public(gathering)


@router.delete("/{id}")
def delete_gathering(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    gathering = session.get(Gathering, id)
    if not gathering:
        raise HTTPException(status_code=404, detail="Gathering not found")
    if not current_user.is_superuser and gathering.host_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    session.delete(gathering)
    session.commit()
    return Message(message="Gathering deleted successfully")
