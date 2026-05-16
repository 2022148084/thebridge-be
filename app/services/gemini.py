import math

from google import genai
from google.genai import types

from app.core.config import settings
from app.models import ChatLog

_EMBED_MODEL = "gemini-embedding-2"

SYSTEM_PROMPT = """You are an AI assistant for 'WBOND', a workout buddy matching service.
Chat naturally with the user to learn about their exercise preferences.

Topics to discover:
- Preferred workout types (running, cycling, yoga, stretching, dancing, walking, hiking)
- Intensity level (1–5, where 1 = very light and 5 = very intense)
- Preferred atmosphere (quiet pace / social energy / locked in / reset mode)
- Workout frequency and preferred time of day

Always respond in English in a friendly, conversational tone.
Do not ask about all topics at once — discover them naturally through the conversation."""

SUMMARY_PROMPT_TEMPLATE = """Based on the following conversation, write a concise summary of the user's workout preferences.
Include: preferred workout types, intensity level, preferred atmosphere, frequency and time of day.
Omit any topics not yet discussed. Write 2–4 sentences.

Conversation:
{conversation}

Summary:"""

MERGE_PROMPT_TEMPLATE = """Merge the following two workout preference summaries into one.
Prioritize the latest information, but incorporate both. Write 2–4 sentences.

Existing summary:
{core}

Latest summary:
{recent}

Merged summary:"""

_MODEL = "gemini-2.5-flash"


def _client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def chat(history: list[ChatLog], user_message: str) -> str:
    client = _client()
    gemini_history = [
        types.Content(
            role="user" if log.role == "user" else "model",
            parts=[types.Part(text=log.message)],
        )
        for log in history
    ]
    chat_session = client.chats.create(
        model=_MODEL,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        history=gemini_history,
    )
    response = chat_session.send_message(user_message)
    return response.text or ""


def generate_recent_summary(messages: list[ChatLog]) -> str:
    client = _client()
    conversation = "\n".join(
        f"{'User' if m.role == 'user' else 'Assistant'}: {m.message}"
        for m in messages
    )
    prompt = SUMMARY_PROMPT_TEMPLATE.format(conversation=conversation)
    response = client.models.generate_content(model=_MODEL, contents=prompt)
    return (response.text or "").strip()


def merge_summaries(core: str, recent: str) -> str:
    client = _client()
    prompt = MERGE_PROMPT_TEMPLATE.format(core=core, recent=recent)
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
    user_desc_line = f"- Additional context: {user_description}" if user_description else ""
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
    response = client.models.generate_content(model=_MODEL, contents=prompt)
    return (response.text or "").strip()


def generate_embedding(text: str) -> list[float]:
    client = _client()
    result = client.models.embed_content(
        model=_EMBED_MODEL,
        contents=text,
    )
    return list(result.embeddings[0].values)


_SPORT_TYPES = {"running", "cycling", "yoga", "stretching", "dancing", "walking", "hiking"}


def extract_preferred_sports(summary: str) -> list[str]:
    text = summary.lower()
    return [s for s in _SPORT_TYPES if s in text]


def compute_weighted_embedding(
    core_emb: list[float],
    recent_emb: list[float],
    core_weight: float = 0.4,
    recent_weight: float = 0.6,
) -> list[float]:
    weighted = [
        core_weight * c + recent_weight * r
        for c, r in zip(core_emb, recent_emb)
    ]
    norm = math.sqrt(sum(x * x for x in weighted))
    return [x / norm for x in weighted] if norm > 0 else weighted
