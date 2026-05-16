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

## OCI Deployment

The production compose file is intended to run behind host-level Caddy:

```caddy
thebridge.hsh-server.com {
    reverse_proxy 127.0.0.1:8000
}
```

Create `.env` manually on the OCI instance. Do not commit it:

```env
PROJECT_NAME="The Bridge Backend"
SECRET_KEY=<strong-random-secret>

POSTGRES_USER=<db-user>
POSTGRES_PASSWORD=<strong-db-password>
POSTGRES_DB=<db-name>

FIRST_SUPERUSER=<admin-email>
FIRST_SUPERUSER_PASSWORD=<strong-admin-password>

BACKEND_CORS_ORIGINS=["https://thebridge.hsh-server.com"]
WEB_CONCURRENCY=2
```

First deploy:

```bash
docker compose -f compose.prod.yml up -d --build
```

Deploy after pulling updates:

```bash
git pull --ff-only
docker compose -f compose.prod.yml up -d --build
docker compose -f compose.prod.yml logs -f backend
```

The production stack excludes Adminer and binds the backend only to
`127.0.0.1:8000`, so OCI security rules should expose only SSH, HTTP, and HTTPS.

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
