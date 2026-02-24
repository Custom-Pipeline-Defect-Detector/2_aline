# Aline AI Doc Hub (MVP)

AI-first internal web app for Nanjing Aline Automation Company. Users upload documents, the system extracts text, routes and extracts entities via Ollama, generates proposals, and only approved proposals are written into core tables with full audit logs.

## Quick start

```bash
docker compose up --build
```

If your environment blocks Docker Hub authentication, ensure the base images are already cached locally and run:

```bash
docker compose up --build --pull=never
```

Open:
- Backend API: http://localhost:8000/api
- Frontend UI: http://localhost:9876

## Seeded admin user
- Email: `mir@aline.com`
- Password: `89ui89ui` (change after first login)

## Services
- **backend**: FastAPI + SQLAlchemy + Alembic
- **worker**: Celery worker for extraction + AI processing
- **watcher**: Watchdog service for file system ingestion
- **postgres**: DB
- **redis**: broker/result backend
- **frontend**: React + Vite + Tailwind

## Environment variables
| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg2://aline:aline@postgres:5432/aline` | DB connection |
| `FILE_STORAGE_ROOT` | `/data/aline_docs` | Document storage |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct` | Model name |
| `WATCH_PATHS` | `/data/aline_docs` | Watcher paths |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Celery broker |


## Local backend startup (without Docker)
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

If `/api/dashboard/summary` or `/api/customers` returns a 503, verify database connectivity and re-run `alembic upgrade head`.

## Tests
```bash
cd backend
pytest
```

## AI chat memory behavior
- AI chat sessions, messages, and memory items are stored per authenticated user and never shared across users.
- The assistant uses only recent session messages plus a small set of durable memory items (not the full transcript forever).
- Users can inspect and delete their saved memory entries from the AI Inbox memory dialog.

## Messages feature (separate from AI Inbox)
- `/messages` provides human-to-human chat for authenticated users.
- It has two modes: direct messages (1:1 private rooms) and a single global shared room.
- This is implemented under `/api/messages/*` and is intentionally separate from `/api/ai/*` (AI sessions/memory).
