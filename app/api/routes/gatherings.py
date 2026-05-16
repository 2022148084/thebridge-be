import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Gathering,
    GatheringCreate,
    GatheringPublic,
    GatheringRecommendPublic,
    GatheringsPublic,
    GatheringsRecommendPublic,
    GatheringUpdate,
    Message,
    Participant,
    ParticipantPublic,
    ParticipatingGatheringPublic,
    ParticipatingGatheringsPublic,
    UserPreferences,
    get_datetime_utc,
)
from app.services import gemini
from app.services.gemini import compute_weighted_embedding

router = APIRouter(prefix="/gatherings", tags=["gatherings"])


def _to_public(g: Gathering) -> GatheringPublic:
    return GatheringPublic.model_validate(g)


def _to_participating_public(
    gathering: Gathering, participant: Participant
) -> ParticipatingGatheringPublic:
    return ParticipatingGatheringPublic(
        **_to_public(gathering).model_dump(),
        participant_id=participant.id,
        participant_status=participant.status,
        joined_at=participant.joined_at,
    )


def _refresh_description_and_embedding(g: Gathering) -> tuple[str, list[float]]:
    vibe = g.vibe if isinstance(g.vibe, str) else ",".join(g.vibe or [])
    desc = gemini.generate_gathering_description(
        city=g.city,
        place_name=g.place_name,
        sport_type=g.sport_type,
        level=g.level,
        vibe=vibe,
        duration_min=g.duration_min,
        max_participants=g.max_participants,
        user_description=g.description,
    )
    return desc, gemini.generate_embedding(desc)


def _recommend_rows(
    session: Any,
    user_vec: list[float],
    exclude_host_id: uuid.UUID,
    limit: int,
    preferred_sports: list[str] | None = None,
) -> list[GatheringRecommendPublic]:
    distance_col = Gathering.description_embedding.cosine_distance(user_vec).label("distance")
    rows = session.exec(
        select(Gathering, distance_col)
        .where(Gathering.description_embedding.isnot(None))
        .where(Gathering.status == 0)
        .where(Gathering.host_id != exclude_host_id)
        .order_by(distance_col.asc())
        .limit(limit)
    ).all()
    result = []
    for g, dist in rows:
        base = round((1 - dist) * 100, 1)
        if preferred_sports and g.sport_type not in preferred_sports:
            base = round(base * 0.5, 1)
        result.append(
            GatheringRecommendPublic(
                **GatheringPublic.model_validate(g).model_dump(),
                match_percentage=base,
            )
        )
    return result


@router.get("/recommended", response_model=GatheringsRecommendPublic)
def get_recommended_gatherings(
    session: SessionDep,
    current_user: CurrentUser,
    limit: int = 10,
) -> Any:
    prefs = session.exec(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    ).first()
    if not prefs or prefs.core_embedding is None or prefs.recent_embedding is None:
        raise HTTPException(
            status_code=404,
            detail="No preference embeddings found. Complete the chat survey first.",
        )
    user_vec = compute_weighted_embedding(prefs.core_embedding, prefs.recent_embedding)
    summary = prefs.core_summary or prefs.recent_summary or ""
    preferred_sports = gemini.extract_preferred_sports(summary)
    data = _recommend_rows(session, user_vec, current_user.id, limit, preferred_sports)
    return GatheringsRecommendPublic(data=data, count=len(data))


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
    _ = current_user
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


@router.get("/me/participating", response_model=ParticipatingGatheringsPublic)
def read_my_participating_gatherings(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    active_participant_statuses = ["pending", "joined"]
    base_filters = (
        col(Participant.user_id) == current_user.id,
        col(Participant.status).in_(active_participant_statuses),
    )
    count = session.exec(
        select(func.count())
        .select_from(Gathering)
        .join(Participant, col(Participant.session_id) == col(Gathering.id))
        .where(*base_filters)
    ).one()
    rows = session.exec(
        select(Gathering, Participant)
        .join(Participant, col(Participant.session_id) == col(Gathering.id))
        .where(*base_filters)
        .order_by(col(Gathering.starts_at).asc())
        .offset(skip)
        .limit(limit)
    ).all()
    return ParticipatingGatheringsPublic(
        data=[
            _to_participating_public(gathering, participant)
            for gathering, participant in rows
        ],
        count=count,
    )


@router.get("/{id}", response_model=GatheringPublic)
def read_gathering(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    _ = current_user
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
    desc, emb = _refresh_description_and_embedding(gathering)
    gathering.description = desc
    gathering.description_embedding = emb
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
    _EMBED_TRIGGER_FIELDS = {
        "sport_type", "level", "vibe", "duration_min",
        "max_participants", "city", "place_name", "description",
    }
    update_data = gathering_in.model_dump(exclude_unset=True)
    if "vibe" in update_data and update_data["vibe"] is not None:
        update_data["vibe"] = ",".join(update_data["vibe"])
    update_data["updated_at"] = get_datetime_utc()
    gathering.sqlmodel_update(update_data)
    if update_data.keys() & _EMBED_TRIGGER_FIELDS:
        desc, emb = _refresh_description_and_embedding(gathering)
        gathering.description = desc
        gathering.description_embedding = emb
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


@router.post("/{gathering_id}/participants", response_model=ParticipantPublic, status_code=201)
def join_gathering(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    gathering_id: uuid.UUID,
) -> Any:
    gathering = session.get(Gathering, gathering_id)
    if not gathering:
        raise HTTPException(status_code=404, detail="Gathering not found")

    if gathering.host_id == current_user.id:
        raise HTTPException(status_code=400, detail="Host cannot join their own gathering")

    if gathering.status != 0:
        raise HTTPException(status_code=400, detail="Gathering is not open")

    existing = session.exec(
        select(Participant).where(
            Participant.session_id == gathering_id,
            Participant.user_id == current_user.id,
        )
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already a participant in this gathering")

    active_count = session.exec(
        select(func.count()).select_from(Participant).where(
            Participant.session_id == gathering_id,
            col(Participant.status).in_(["pending", "joined"]),
        )
    ).one()
    if active_count >= gathering.max_participants:
        raise HTTPException(status_code=409, detail="Gathering is full")

    participant = Participant(
        session_id=gathering_id,
        user_id=current_user.id,
        status="pending",
    )
    session.add(participant)
    session.commit()
    session.refresh(participant)
    return ParticipantPublic.model_validate(participant)


@router.delete("/{gathering_id}/participants/me")
def cancel_join_gathering(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    gathering_id: uuid.UUID,
) -> Message:
    gathering = session.get(Gathering, gathering_id)
    if not gathering:
        raise HTTPException(status_code=404, detail="Gathering not found")

    participant = session.exec(
        select(Participant).where(
            Participant.session_id == gathering_id,
            Participant.user_id == current_user.id,
        )
    ).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participation not found")

    if participant.status == "joined" and gathering.status != 0:
        raise HTTPException(status_code=400, detail="Cannot cancel after gathering has started or closed")

    session.delete(participant)
    session.commit()
    return Message(message="Participation cancelled successfully")
