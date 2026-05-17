import math
from typing import cast

from google import genai
from google.genai import types

from app.core.config import settings
from app.models import ChatLog
from app.services.rate_limit import enforce_gemini_rpm_limit

_EMBED_MODEL = "gemini-embedding-2"

SYSTEM_PROMPT = """You are a friendly assistant for WBOND, a workout buddy matching app.
Your job is to learn about the user's workout preferences through natural conversation — not an interview.

Guidelines:
- Ask one question at a time, only when it flows naturally
- Keep each reply to 2–3 sentences max
- Use minimal emojis (one per message at most, only when it fits)
- If the user mentions something relevant, acknowledge it before moving on
- Never list all questions at once

Preferences to uncover (naturally, over time):
- Workout type: running / cycling / yoga / stretching / dancing / walking / hiking
- Intensity: 1 (very light) → 5 (very intense)
- Vibe: quiet pace / social energy / locked in / reset mode
- Frequency and preferred time of day

Tone: warm, concise, human. Like a friend who's into fitness — not a chatbot running through a checklist.

Always respond in the same language the user is writing in."""


SUMMARY_PROMPT_TEMPLATE = """Summarize the user's workout preferences based on the conversation below.
Be concise — 3 to 4 sentences only.
Only include what was actually discussed. Skip anything not mentioned.

Cover if available:
- Workout type(s)
- Intensity level (1–5)
- Preferred vibe (quiet pace / social energy / locked in / reset mode)
- Frequency and time of day

Conversation:
{conversation}

Summary:"""


MERGE_PROMPT_TEMPLATE = """You have two workout preference summaries for the same user.
Merge them into a single, updated summary of 3–4 sentences.

Rules:
- If there's a conflict, prefer the latest summary
- Don't repeat the same point twice
- Keep only what's relevant and specific

Existing summary (all past sessions):
{core}

Latest summary (last 3 messages only):
{recent}

Merged summary:"""

_MODEL = "gemini-2.5-flash"


def _client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def chat(history: list[ChatLog], user_message: str) -> str:
    client = _client()
    gemini_history = cast(
        list[types.ContentOrDict],
        [
            types.Content(
                role="user" if log.role == "user" else "model",
                parts=[types.Part(text=log.message)],
            )
            for log in history
        ],
    )
    chat_session = client.chats.create(
        model=_MODEL,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        history=gemini_history,
    )
    enforce_gemini_rpm_limit()
    response = chat_session.send_message(user_message)
    return response.text or ""


def generate_recent_summary(messages: list[ChatLog]) -> str:
    client = _client()
    conversation = "\n".join(
        f"{'User' if m.role == 'user' else 'Assistant'}: {m.message}" for m in messages
    )
    prompt = SUMMARY_PROMPT_TEMPLATE.format(conversation=conversation)
    enforce_gemini_rpm_limit()
    response = client.models.generate_content(model=_MODEL, contents=prompt)
    return (response.text or "").strip()


def merge_summaries(core: str, recent: str) -> str:
    client = _client()
    prompt = MERGE_PROMPT_TEMPLATE.format(core=core, recent=recent)
    enforce_gemini_rpm_limit()
    response = client.models.generate_content(model=_MODEL, contents=prompt)
    return (response.text or "").strip()


GATHERING_DESC_PROMPT = """Write a concise 2-3 sentence description for a workout gathering with the following attributes:
- Location: {city} ({place_name})
- Sport: {sport_type}
- Intensity level: {level} out of 5
- Vibe: {vibe}
- Duration: {duration_min} minutes
- Max participants: {max_participants}
{user_desc_line}
Write in English. Focus on the experience and atmosphere."""


def generate_gathering_description(
    city: str,
    place_name: str,
    sport_type: str,
    level: int,
    vibe: str,
    duration_min: int,
    max_participants: int,
    user_description: str | None = None,
) -> str:
    client = _client()
    user_desc_line = (
        f"- Additional context: {user_description}" if user_description else ""
    )
    prompt = GATHERING_DESC_PROMPT.format(
        city=city,
        place_name=place_name,
        sport_type=sport_type,
        level=level,
        vibe=vibe,
        duration_min=duration_min,
        max_participants=max_participants,
        user_desc_line=user_desc_line,
    )
    enforce_gemini_rpm_limit()
    response = client.models.generate_content(model=_MODEL, contents=prompt)
    return (response.text or "").strip()


def generate_embedding(text: str) -> list[float]:
    client = _client()
    enforce_gemini_rpm_limit()
    result = client.models.embed_content(
        model=_EMBED_MODEL,
        contents=text,
    )
    values = result.embeddings[0].values if result.embeddings else []
    return list(values or [])


_SPORT_TYPES = {
    "running",
    "cycling",
    "yoga",
    "stretching",
    "dancing",
    "walking",
    "hiking",
}


def extract_preferred_sports(summary: str) -> list[str]:
    text = summary.lower()
    return [s for s in _SPORT_TYPES if s in text]


def compute_weighted_embedding(
    core_emb: list[float],
    recent_emb: list[float],
    core_weight: float = 0.2,
    recent_weight: float = 0.8,
) -> list[float]:
    weighted = [
        core_weight * c + recent_weight * r
        for c, r in zip(core_emb, recent_emb, strict=False)
    ]
    norm = math.sqrt(sum(x * x for x in weighted))
    return [x / norm for x in weighted] if norm > 0 else weighted
