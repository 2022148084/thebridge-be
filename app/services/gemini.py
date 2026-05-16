from google import genai
from google.genai import types

from app.core.config import settings
from app.models import ChatLog

SYSTEM_PROMPT = """당신은 운동 친구 매칭 서비스 'The Bridge'의 AI 상담사입니다.
사용자와 친근하게 대화하며 운동 취향을 파악하세요.

파악해야 할 항목:
- 좋아하는 운동 종류 (러닝, 사이클링, 요가, 스트레칭, 댄스, 걷기, 하이킹 중 선택)
- 운동 강도 (1~5단계, 1=매우 가볍게 ~ 5=매우 강하게)
- 선호하는 분위기 (조용한 페이스 / 소셜 에너지 / 집중 모드 / 회복 모드)
- 운동 빈도 및 선호 시간대

모든 대화는 한국어로 자연스럽고 친근하게 진행하세요.
정보를 한 번에 묻지 말고 대화 흐름에 맞게 자연스럽게 파악하세요."""

SUMMARY_PROMPT_TEMPLATE = """다음 대화에서 사용자의 운동 취향을 파악하여 간결하게 요약해줘.
포함할 내용: 좋아하는 운동 종류, 운동 강도, 선호 분위기, 운동 빈도/시간대.
아직 파악되지 않은 항목은 생략해도 됨. 2~4문장으로 요약.

대화:
{conversation}

요약:"""

MERGE_PROMPT_TEMPLATE = """사용자의 운동 취향 요약 두 가지를 하나로 통합해줘.
최신 정보가 있으면 최신 것을 우선으로 하되, 두 요약을 모두 반영해 종합적인 요약을 만들어줘.
2~4문장으로 작성.

기존 요약:
{core}

최신 요약:
{recent}

통합 요약:"""

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
        f"{'사용자' if m.role == 'user' else 'AI'}: {m.message}"
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
