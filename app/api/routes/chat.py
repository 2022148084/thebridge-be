from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    ChatHistoryPublic,
    ChatLog,
    ChatMessageInput,
    ChatMessagePublic,
    UserPreferences,
    UserPreferencesPublic,
    get_datetime_utc,
)
from app.services import gemini

router = APIRouter(prefix="/chat", tags=["chat"])

_HISTORY_LIMIT = 20


@router.post("/", response_model=ChatMessagePublic)
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

    if prefs is None:
        prefs = UserPreferences(
            user_id=current_user.id,
            recent_summary=recent_summary,
            core_summary=recent_summary,
        )
        session.add(prefs)
    else:
        prefs.recent_summary = recent_summary
        if prefs.core_summary is None:
            prefs.core_summary = recent_summary
        else:
            prefs.core_summary = gemini.merge_summaries(prefs.core_summary, recent_summary)
        prefs.updated_at = get_datetime_utc()
        session.add(prefs)

    session.commit()
    session.refresh(assistant_log)
    return ChatMessagePublic.model_validate(assistant_log)


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
