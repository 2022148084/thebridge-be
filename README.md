# The Bridge Backend

FastAPI 기반의 운동 메이트 매칭 백엔드입니다. 사용자 인증, 프로필/위치 관리, 친구 요청, 운동 모임 생성/참여, 모임 채팅, Gemini 기반 선호도 대화와 모임 추천 기능을 제공합니다.

## 기술 스택

- Python 3.10
- FastAPI
- SQLModel
- PostgreSQL 17 + pgvector
- Alembic
- Redis
- Google Gemini API
- uv
- Docker Compose

## 빠른 시작

모든 명령은 `backend` 디렉터리에서 실행합니다.

```bash
cp .env.example .env
docker compose up --build
```

실행 후 아래 주소를 확인합니다.

```text
API 문서: http://localhost:8000/docs
OpenAPI: http://localhost:8000/api/v1/openapi.json
Adminer: http://localhost:8080
```

Compose는 다음 서비스를 실행합니다.

- `backend`: FastAPI 애플리케이션, 기본 포트 `8000`
- `db`: pgvector가 포함된 PostgreSQL
- `redis`: 채팅 pub/sub과 Gemini 요청 제한에 사용
- `adminer`: 로컬 DB 확인용 웹 UI, 기본 포트 `8080`

백엔드 컨테이너는 시작 시 PostgreSQL 준비 상태를 기다린 뒤 Alembic migration을 적용하고, 초기 superuser를 생성한 다음 FastAPI 서버를 시작합니다.

## 환경 변수

처음 실행할 때 `.env.example`을 복사해 `.env`를 만듭니다.

```bash
cp .env.example .env
```

주요 설정은 다음과 같습니다.

| 이름 | 설명 |
| --- | --- |
| `PROJECT_NAME` | FastAPI 앱 이름 |
| `SECRET_KEY` | JWT 서명용 secret. 운영에서는 반드시 강한 랜덤 값 사용 |
| `POSTGRES_SERVER` | PostgreSQL 호스트. Docker Compose에서는 `db` |
| `POSTGRES_PORT` | PostgreSQL 포트 |
| `POSTGRES_USER` | DB 사용자 |
| `POSTGRES_PASSWORD` | DB 비밀번호 |
| `POSTGRES_DB` | DB 이름 |
| `FIRST_SUPERUSER` | 최초 관리자 이메일 |
| `FIRST_SUPERUSER_PASSWORD` | 최초 관리자 비밀번호 |
| `BACKEND_CORS_ORIGINS` | 허용할 CORS origin 목록. 예: `["http://localhost:5173"]` |
| `ADMINER_PORT` | 로컬 Adminer 포트 |
| `REDIS_URL` | Redis 접속 URL |
| `GEMINI_API_KEY` | Gemini 채팅, 요약, 임베딩 기능에 사용 |
| `GEMINI_RPM_LIMIT` | Gemini API 분당 요청 제한 |

`GEMINI_API_KEY`가 없으면 AI 채팅/요약/추천 관련 기능이 정상 동작하지 않을 수 있습니다.

## 로컬 개발

Docker 대신 로컬 Python 환경에서 실행하려면 의존성을 설치합니다.

```bash
uv sync
```

로컬에서 앱을 실행합니다.

```bash
uv run uvicorn app.main:app --reload
```

로컬 실행 시 PostgreSQL과 Redis가 접근 가능해야 합니다. 현재 `compose.yml`은 DB/Redis 포트를 호스트에 공개하지 않으므로, 앱만 로컬에서 실행하려면 별도의 PostgreSQL/Redis를 실행하거나 compose에 개발용 port mapping을 추가한 뒤 `.env`의 접속 주소를 맞춥니다.

```env
POSTGRES_SERVER=localhost
REDIS_URL=redis://localhost:6379/0
```

## 주요 API

모든 API는 `/api/v1` prefix 아래에 있습니다. 아래 목록은 prefix를 생략해 표기합니다.

- `POST /login/access-token`: 이메일/비밀번호 로그인
- `POST /users/signup`: 일반 사용자 가입
- `GET /users/me`: 내 프로필 조회
- `PATCH /users/me`: 내 프로필 수정
- `PATCH /users/me/location`: 내 위치 수정
- `GET /users/search`: 사용자 검색
- `GET /friends`: 친구 목록 조회
- `GET /friends/requests`: 친구 요청 목록 조회
- `POST /friends/{friend_id}`: 친구 요청 생성
- `POST /friends/requests/{request_id}/accept`: 친구 요청 수락
- `GET /gatherings`: 운동 모임 목록 조회
- `GET /gatherings/recommended`: 추천 모임 조회
- `POST /gatherings`: 운동 모임 생성
- `POST /gatherings/{gathering_id}/participants`: 모임 참여
- `DELETE /gatherings/{gathering_id}/participants/me`: 모임 참여 취소
- `POST /chat`: Gemini 기반 선호도 대화와 추천
- `WS /chat/ws/gatherings/{gathering_id}?token=<access_token>`: 모임 실시간 채팅
- `GET /utils/health-check/`: 헬스 체크

자세한 요청/응답 schema는 `/docs`에서 확인합니다.

## 데이터베이스 Migration

모델 변경 후 migration을 생성합니다.

```bash
uv run alembic revision --autogenerate -m "describe change"
```

생성된 migration 파일을 검토한 뒤 적용합니다.

```bash
uv run alembic upgrade head
```

Docker Compose 환경에서는 컨테이너 안에서 실행할 수 있습니다.

```bash
docker compose exec backend alembic upgrade head
```

## 검증 명령

```bash
uv run ruff check .
uv run ty check .
docker compose config
```

컨테이너 로그 확인:

```bash
docker compose logs -f backend
```

백엔드 컨테이너 shell 접속:

```bash
docker compose exec backend bash
```

## Adminer 접속

로컬 Compose 실행 후 `http://localhost:8080`에서 접속합니다.

- System: `PostgreSQL`
- Server: `db`
- Username: `.env`의 `POSTGRES_USER`
- Password: `.env`의 `POSTGRES_PASSWORD`
- Database: `.env`의 `POSTGRES_DB`

## 운영 배포

`compose.prod.yml`은 호스트 레벨 reverse proxy 뒤에서 실행하는 구성을 전제로 합니다. 예를 들어 Caddy를 사용할 수 있습니다.

```caddy
thebridge.hsh-server.com {
    reverse_proxy 127.0.0.1:8000
}
```

운영 서버에서는 `.env`를 직접 만들고 commit하지 않습니다.

```env
PROJECT_NAME="The Bridge Backend"
SECRET_KEY=<strong-random-secret>

POSTGRES_USER=<db-user>
POSTGRES_PASSWORD=<strong-db-password>
POSTGRES_DB=<db-name>

FIRST_SUPERUSER=<admin-email>
FIRST_SUPERUSER_PASSWORD=<strong-admin-password>

BACKEND_CORS_ORIGINS=["https://thebridge.hsh-server.com"]
WEB_CONCURRENCY=4
GEMINI_API_KEY=<gemini-api-key>
GEMINI_RPM_LIMIT=500
REDIS_URL=redis://redis:6379/0
```

최초 배포:

```bash
docker compose -f compose.prod.yml up -d --build
```

업데이트 배포:

```bash
git pull --ff-only
docker compose -f compose.prod.yml up -d --build
docker compose -f compose.prod.yml logs -f backend
```

운영 Compose는 Adminer를 포함하지 않고, 백엔드를 `127.0.0.1:8000`에만 바인딩합니다. 서버 방화벽이나 OCI security rule에서는 SSH, HTTP, HTTPS만 외부에 노출하는 구성을 권장합니다.

## 프로젝트 구조

```text
backend/
├── app/
│   ├── api/              # FastAPI 라우터와 의존성
│   ├── core/             # 설정, DB 연결, 보안 유틸
│   ├── services/         # Gemini, Redis rate limit, 거리 계산
│   ├── alembic/          # Alembic migration
│   ├── crud.py           # DB 작업 함수
│   ├── models.py         # SQLModel 모델과 API schema
│   ├── main.py           # FastAPI 앱 진입점
│   ├── backend_pre_start.py
│   └── initial_data.py
├── alembic.ini
├── compose.yml
├── compose.prod.yml
├── Dockerfile
├── pyproject.toml
├── uv.lock
└── .env.example
```

라우터를 추가하면 `app/api/main.py`에 include 해야 합니다. DB schema 변경은 `app/models.py` 수정 후 Alembic migration으로 남깁니다.
