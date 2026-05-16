import asyncio
import json
import uuid
from contextlib import suppress
from typing import Any

import jwt
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.concurrency import run_in_threadpool
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlmodel import Session, col, select

from app.api.deps import CurrentUser, SessionDep
from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import (
    ChatHistoryPublic,
    ChatLog,
    ChatMessageInput,
    ChatMessagePublic,
    ChatResponse,
    Gathering,
    GatheringPublic,
    GatheringRecommendPublic,
    TokenPayload,
    User,
    UserPreferences,
    UserPreferencesPublic,
    get_datetime_utc,
)
from app.services import gemini
from app.services.gemini import compute_weighted_embedding

router = APIRouter(prefix="/chat", tags=["chat"])

_HISTORY_LIMIT = 20
_WS_CLOSE_POLICY_VIOLATION = status.WS_1008_POLICY_VIOLATION
_WS_CLOSE_SERVER_ERROR = status.WS_1011_INTERNAL_ERROR


def _get_websocket_user(token: str | None) -> User | None:
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[security.ALGORITHM],
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        return None

    if token_data.sub is None:
        return None

    with Session(engine) as session:
        user = session.get(User, token_data.sub)
        if not user or not user.is_active:
            return None
        return user


def _gathering_exists(gathering_id: uuid.UUID) -> bool:
    with Session(engine) as session:
        return session.get(Gathering, gathering_id) is not None


def _chat_channel(gathering_id: uuid.UUID) -> str:
    return f"chat:gathering:{gathering_id}"


def _serialize_group_message(
    *,
    gathering_id: uuid.UUID,
    user: User,
    message: str,
) -> str:
    return json.dumps(
        {
            "type": "message",
            "room_id": str(gathering_id),
            "user_id": str(user.id),
            "user_name": user.full_name or user.email,
            "message": message,
            "sent_at": get_datetime_utc().isoformat(),
        }
    )


async def _receive_and_publish(
    *, websocket: WebSocket, redis: Redis, channel: str, gathering_id: uuid.UUID, user: User
) -> None:
    while True:
        data = await websocket.receive_json()
        if not isinstance(data, dict):
            continue
        message = data.get("message")
        if not isinstance(message, str):
            continue
        message = message.strip()
        if not message:
            continue
        payload = _serialize_group_message(
            gathering_id=gathering_id,
            user=user,
            message=message,
        )
        await redis.publish(channel, payload)


async def _listen_and_send(*, websocket: WebSocket, pubsub: Any) -> None:
    async for event in pubsub.listen():
        if event.get("type") != "message":
            continue
        await websocket.send_text(event["data"])


@router.websocket("/ws/gatherings/{gathering_id}")
async def gathering_chat_websocket(
    websocket: WebSocket,
    gathering_id: uuid.UUID,
    token: str | None = None,
) -> None:


    if token:
        print(f"2. 요청된 토큰: {token[:15]}... (생략)")
    else:
        print("2. 토큰이 아예 전달되지 않음!!")

    try:
        user = await run_in_threadpool(_get_websocket_user, token)
        print(f"3. 인증된 유저: {user}")
    except Exception as e:
        print(f"3. 유저 인증 중 에러 발생: {e}")
        user = None

    try:
        gathering_exists = await run_in_threadpool(_gathering_exists, gathering_id)
        print(f"4. 모임 DB 확인 결과: {gathering_exists}")
    except Exception as e:
        print(f"4. 모임 확인 중 에러 발생: {e}")
        gathering_exists = False

    # ===== 디버깅 로그 끝 =====
    if user is None or not gathering_exists:
        print("❌ 유저가 없거나 모임이 없어서 강제 종료합니다 (403 반환)")
        await websocket.close(code=_WS_CLOSE_POLICY_VIOLATION)
        return

    await websocket.accept()

    
    user = await run_in_threadpool(_get_websocket_user, token)
    gathering_exists = await run_in_threadpool(_gathering_exists, gathering_id)
    if user is None or not gathering_exists:
        await websocket.close(code=_WS_CLOSE_POLICY_VIOLATION)
        return


    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()
    channel = _chat_channel(gathering_id)

    try:
        await pubsub.subscribe(channel)
        receive_task = asyncio.create_task(
            _receive_and_publish(
                websocket=websocket,
                redis=redis,
                channel=channel,
                gathering_id=gathering_id,
                user=user,
            )
        )
        listen_task = asyncio.create_task(
            _listen_and_send(websocket=websocket, pubsub=pubsub)
        )
        done, pending = await asyncio.wait(
            {receive_task, listen_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in done:
            task.result()
        for task in pending:
            with suppress(asyncio.CancelledError):
                await task
    except WebSocketDisconnect:
        pass
    except Exception:
        with suppress(RuntimeError):
            await websocket.close(code=_WS_CLOSE_SERVER_ERROR)
    finally:
        with suppress(Exception):
            await pubsub.unsubscribe(channel)
        with suppress(Exception):
            await pubsub.aclose()
        with suppress(Exception):
            await redis.aclose()


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
