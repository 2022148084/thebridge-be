# Development Guide

이 문서는 이 백엔드 코드를 처음 보는 개발자가 빠르게 구조를 파악하고 개발을 시작하기 위한 최소 가이드입니다.

## 코드베이스 구조

```text
backend/
├── app/
│   ├── api/              # FastAPI 라우터, 의존성
│   ├── core/             # 설정, DB 연결, 보안 유틸
│   ├── alembic/          # DB migration 파일
│   ├── crud.py           # DB 작업 함수
│   ├── models.py         # SQLModel 모델과 API schema
│   ├── main.py           # FastAPI 앱 진입점
│   ├── backend_pre_start.py
│   └── initial_data.py
├── alembic.ini
├── compose.yml
├── Dockerfile
├── pyproject.toml
├── uv.lock
└── .env.example
```

주요 흐름:

- `app/main.py`가 FastAPI 앱을 만든다.
- `app/api/main.py`가 API 라우터를 모은다.
- 실제 endpoint는 `app/api/routes/` 아래에 있다.
- DB 모델과 요청/응답 schema는 `app/models.py`에 있다.
- DB 접속 설정은 `app/core/config.py`, 엔진 생성은 `app/core/db.py`에 있다.
- Alembic migration은 `app/alembic/versions/`에 쌓인다.

## 개발 환경 세팅



```bash
cd backend
cp .env.example .env
```

Docker로 실행:

```bash
docker compose up --build
```

API 문서:

```text
http://localhost:8000/docs
```



## 개발 프로세스


# 1. 모델 수정
app/models.py 수정

# 2. 로컬 uv 환경에서 migration 생성
uv run alembic revision --autogenerate -m "add something"

# 3. 생성된 migration 파일 확인
app/alembic/versions/... 또는 alembic/versions/... 확인

# 4. backend 재빌드/재시작
docker compose up -d --build backend

# 5. 로그 확인
docker compose logs -f backend


4. API 변경

라우터는 `app/api/routes/`에 추가하거나 수정한다. 새 라우터 파일을 만들면 `app/api/main.py`에 include 해야 한다.

5. 기본 검증

```bash
docker compose config
docker compose up --build
```

앱이 뜨면 `/docs`에서 endpoint가 보이는지 확인한다.


## 원칙

- 이 프로젝트는 FastAPI + PostgreSQL 백엔드 템플릿이다.
- frontend, email sending, deployment, Traefik 설정은 포함하지 않는다.
- DB schema 변경은 Alembic migration으로 남긴다.
