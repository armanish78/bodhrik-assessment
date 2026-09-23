**THE WRITTEN NOTES (300-500 WORDS) IS NAMED AS ASSESSMENT_NOTE.MD IN THE FILE STRUCTURE**

# Bodhrik API

A small FastAPI backend service built for the Bodhrik technical assessment. It manages users, sessions, and asynchronous evaluation jobs using PostgreSQL and Redis.

## Tech Stack
- **Backend**: FastAPI (Python 3.11)
- **Database**: PostgreSQL 15 (SQLAlchemy ORM)
- **Queue**: Redis 7
- **Linting & Testing**: Ruff, Pytest

## Basic Architecture
- **API**: A stateless FastAPI service exposing CRUD and job-trigger endpoints.
- **Database**: Stores `Users`, `Sessions`, and `Evaluations`.
- **Queue**: When an evaluation is triggered, a stub job payload is pushed to a Redis list (`evaluation_queue`) to simulate background processing.

## Project Structure
```text
.
├── app/                  # Application code
│   ├── database.py       # SQLAlchemy engine and DB session setup
│   ├── main.py           # FastAPI application and route endpoints
│   ├── models.py         # SQLAlchemy database models
│   └── schemas.py        # Pydantic schemas for validation
├── tests/                # Pytest integration tests
├── Dockerfile            # API container image definition
├── docker-compose.yml    # Multi-container orchestration
├── requirements.txt      # Python dependencies
└── seed.py               # Database seeder for testing and development
```

## How to Run Locally (Docker Compose)

1. **Start the stack** (API, PostgreSQL, and Redis):
   ```bash
   docker compose up --build -d
   ```
2. The API will be available at `http://localhost:8000`.

## Seeding the Database
To run integration tests or use the API locally, you need users in the database.
```bash
# Wait a few seconds for PostgreSQL to initialize, then run:
docker compose exec api python seed.py
```

## Running Tests
Tests are configured to hit the running PostgreSQL database.
```bash
# Ensure the database is seeded first, then run:
docker compose exec api pytest
```

## Linting
We use Ruff for linting.
```bash
docker compose exec api ruff check --ignore B008,BLE001 .
```

## API Endpoints

- `GET /` - Health check
- `POST /sessions` - Create a new session
- `GET /sessions` - List sessions (filtered by role)
- `GET /sessions/{id}` - Get a specific session
- `PUT /sessions/{id}` - Update a session
- `DELETE /sessions/{id}` - Delete a session
- `POST /sessions/{id}/evaluate` - Trigger an async evaluation job

## Role-Based Access Control (RBAC)
Authentication is simulated by passing an `X-User-ID` header with the request.
- **Admin**: Full CRUD access to all sessions, and can trigger evaluations.
- **Teacher**: Can only manage and evaluate sessions where they are the assigned teacher. Cannot access other teachers' sessions.
- **Parent**: Can only view and evaluate sessions assigned to them (their child's sessions). Cannot create, update, or delete sessions.

## Evaluation Queue (Redis)
When `POST /sessions/{id}/evaluate` is called, an `Evaluation` record is created in PostgreSQL with `status="pending"`. The endpoint then immediately pushes a JSON payload to a Redis list called `evaluation_queue`. A separate worker process (not implemented in this scope) would pop from this queue to perform the actual AI evaluation.
