from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    ChatHistoryPublic,
    ChatLog,
    ChatMessageInput,
    ChatMessagePublic,
    ChatResponse,
    Gathering,
    GatheringPublic,
    GatheringRecommendPublic,
    UserPreferences,
    UserPreferencesPublic,
    get_datetime_utc,
)
from app.services import gemini
from app.services.gemini import compute_weighted_embedding

router = APIRouter(prefix="/chat", tags=["chat"])

_HISTORY_LIMIT = 20


@router.post("/", response_model=ChatResponse)
def send_message(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    message_in: ChatMessageInput,
) -> Any:
    recent_logs = session.exec(
        select(ChatLog)
        .where(ChatLog.user_id == current_user.id)
        .order_by(col(ChatLog.created_at).desc())
        .limit(_HISTORY_LIMIT)
    ).all()
    history = list(reversed(recent_logs))

    assistant_text = gemini.chat(history, message_in.message)

    user_log = ChatLog(user_id=current_user.id, role="user", message=message_in.message)
    assistant_log = ChatLog(user_id=current_user.id, role="assistant", message=assistant_text)
    session.add(user_log)
    session.add(assistant_log)
    session.flush()

    all_logs = history + [user_log, assistant_log]
    recent_summary = gemini.generate_recent_summary(all_logs)

    prefs = session.exec(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    ).first()

    recent_emb = gemini.generate_embedding(recent_summary)

    if prefs is None:
        core_summary = recent_summary
        core_emb = recent_emb
        prefs = UserPreferences(
            user_id=current_user.id,
            recent_summary=recent_summary,
            recent_embedding=recent_emb,
            core_summary=core_summary,
            core_embedding=core_emb,
        )
        session.add(prefs)
    else:
        prefs.recent_summary = recent_summary
        prefs.recent_embedding = recent_emb
        if prefs.core_summary is None:
            prefs.core_summary = recent_summary
            prefs.core_embedding = recent_emb
        else:
            prefs.core_summary = gemini.merge_summaries(prefs.core_summary, recent_summary)
            prefs.core_embedding = gemini.generate_embedding(prefs.core_summary)
        prefs.updated_at = get_datetime_utc()
        session.add(prefs)

    # Flush to persist embeddings before querying recommendations
    session.flush()

    recommendations: list[GatheringRecommendPublic] | None = None
    if prefs.core_embedding is not None and prefs.recent_embedding is not None:
        user_vec = compute_weighted_embedding(prefs.core_embedding, prefs.recent_embedding)
        summary = prefs.core_summary or prefs.recent_summary or ""
        preferred_sports = gemini.extract_preferred_sports(summary)
        distance_col = Gathering.description_embedding.cosine_distance(user_vec).label("distance")
        rows = session.exec(
            select(Gathering, distance_col)
            .where(Gathering.description_embedding.isnot(None))
            .where(Gathering.status == 0)
            .where(Gathering.host_id != current_user.id)
            .order_by(distance_col.asc())
            .limit(3)
        ).all()
        if rows:
            recs = []
            for g, dist in rows:
                base = round((1 - dist) * 100, 1)
                if preferred_sports and g.sport_type not in preferred_sports:
                    base = round(base * 0.5, 1)
                recs.append(
                    GatheringRecommendPublic(
                        **GatheringPublic.model_validate(g).model_dump(),
                        match_percentage=base,
                    )
                )
            recommendations = recs

    session.commit()
    session.refresh(assistant_log)
    return ChatResponse(
        message=ChatMessagePublic.model_validate(assistant_log),
        recommendations=recommendations,
    )


@router.get("/history", response_model=ChatHistoryPublic)
def get_chat_history(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    logs = session.exec(
        select(ChatLog)
        .where(ChatLog.user_id == current_user.id)
        .order_by(col(ChatLog.created_at).asc())
    ).all()
    return ChatHistoryPublic(data=[ChatMessagePublic.model_validate(log) for log in logs])


@router.get("/preferences", response_model=UserPreferencesPublic)
def get_preferences(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    prefs = session.exec(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    ).first()
    if not prefs:
        raise HTTPException(status_code=404, detail="No preferences found. Start a chat first.")
    return UserPreferencesPublic.model_validate(prefs)
