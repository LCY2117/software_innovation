# Life Reflex Arc — Cloud Server

FastAPI-based distributed emergency response backend (v2 — production-ready).

## Quick Start (dev, no external dependencies)

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run server (SQLite + in-memory Redis fallback)
uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# API docs
open http://localhost:8080/docs
```

## Configuration

Copy `.env.example` to `.env` and adjust values:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./lifereflexarc.db` | Database connection string |
| `REDIS_URL` | *(empty)* | Redis URL; leave empty for in-memory fallback |
| `JWT_SECRET` | `dev-secret-change-in-production` | JWT signing secret |
| `DEBUG` | `false` | Enable debug logging |
| `SOS_DURATION_SEC` | `10` | SOS auto-trigger countdown |

## Production (PostgreSQL + Redis)

```bash
DATABASE_URL=postgresql+asyncpg://lra:pass@postgres/lifereflexarc \
REDIS_URL=redis://redis:6379/0 \
JWT_SECRET=your-strong-secret \
uvicorn main:app --host 0.0.0.0 --port 8080 --workers 4
```

## Docker Compose (full stack)

From the repository root:

```bash
docker-compose up -d
# API:   http://localhost:8080
# Docs:  http://localhost:8080/docs
# Web:   http://localhost:5173
```

## API

All endpoints are under `/api/v1`. Responses follow the unified format:

```json
{"code": 0, "msg": "ok", "data": {...}, "traceId": "abc12345"}
```

| Prefix | Description |
|---|---|
| `/api/v1/incidents` | Incident CRUD, SOS, roles, actions |
| `/api/v1/auth` | Phone + SMS + JWT authentication |
| `/api/v1/geo` | AED nearby search, location reporting |
| `/ws?incidentId=<id>` | WebSocket real-time state updates |
| `/health` | Health check |

## Architecture

```
main.py
└── app/
    ├── config.py          # pydantic-settings
    ├── database.py        # SQLAlchemy async engine
    ├── redis_client.py    # Redis with in-memory fallback
    ├── models/            # SQLAlchemy ORM models
    ├── schemas/           # Pydantic request/response schemas
    ├── api/v1/            # FastAPI routers
    ├── services/          # Business logic
    └── ws/                # WebSocket handler (Redis Pub/Sub fan-out)
```

## Tests

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```
