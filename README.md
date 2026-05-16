# FastAPI + PostgreSQL Backend

Hackathon backend template built with FastAPI, SQLModel, Alembic, PostgreSQL, and uv.

## Run with Docker Compose

All commands are run from this directory:

```bash
cd backend
cp .env.example .env
docker compose up --build
```

Open the API docs at:

```text
http://localhost:8000/docs
```

The compose stack starts two services:

- `db`: PostgreSQL
- `backend`: FastAPI app on port `8000`
- `adminer`: database web UI on port `8080`

On container startup the backend waits for PostgreSQL, runs Alembic migrations, creates the initial superuser, and starts FastAPI.

Open Adminer at:

```text
http://localhost:8080
```

Use these local credentials:

- System: `PostgreSQL`
- Server: `db`
- Username: value of `POSTGRES_USER`
- Password: value of `POSTGRES_PASSWORD`
- Database: value of `POSTGRES_DB`

## Local Development

Install dependencies:

```bash
uv sync
```

Run the app locally:

```bash
uvicorn app.main:app --reload
```

When running outside Docker, set `POSTGRES_SERVER` in `.env` to the host where PostgreSQL is reachable.

## Configuration

Copy `.env.example` to `.env` and adjust values:

```bash
cp .env.example .env
```

Required settings:

- `PROJECT_NAME`
- `SECRET_KEY`
- `POSTGRES_SERVER`
- `POSTGRES_PORT`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `FIRST_SUPERUSER`
- `FIRST_SUPERUSER_PASSWORD`

Optional:

- `ADMINER_PORT`: local Adminer port. Defaults to `8080`.
- `BACKEND_CORS_ORIGINS`: JSON-style list of allowed origins. The local Vite frontend uses `["http://localhost:5173"]`.

## Database Migrations

Alembic is configured relative to this directory.

Create a migration:

```bash
alembic revision --autogenerate -m "Describe change"
```

Apply migrations:

```bash
alembic upgrade head
```

Inside Docker:

```bash
docker compose exec backend alembic upgrade head
```

## Useful Commands

Validate compose configuration:

```bash
docker compose config
```

Open a shell in the backend container:

```bash
docker compose exec backend bash
```
