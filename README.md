# Health Monitor

A health-check aggregator service. Registers backend services, periodically pings each one's `/health` endpoint, records status and response time, exposes an API and dashboard, and logs alerts when a service's status changes.

Built as a DevOps/Cloud-focused portfolio project: the application itself is intentionally scoped small so most of the effort goes into containerization, automated testing, CI/CD, and real cloud infrastructure.

## Features

- Register, list, and remove services to monitor via a REST API
- Independent async check loop per service, each on its own interval, no shared blocking between services
- Buffered writes: check results batch in memory and flush to Postgres on an interval instead of writing on every single check
- In-memory status cache for instant reads on the status endpoint, no database hit required
- Alert logging on status transitions (healthy to unhealthy, first check, etc.), not on every check
- Static dashboard showing live, color-coded status per service, polling the API
- Full CI/CD pipeline: automated tests, image build, push to registry, deploy to a live server
- Real infrastructure provisioned with Terraform, not manually clicked together

## API routes

| Method | Path | Description |
|---|---|---|
| POST | `/services` | Register a new service to monitor. Returns the existing service instead of creating a duplicate if the URL is already registered. |
| GET | `/services` | List all registered services. |
| DELETE | `/services/{service_id}` | Stop monitoring and remove a service. |
| GET | `/services/{service_id}/status` | Current status, read from the in-memory cache, no database hit. |
| GET | `/services/{service_id}/history` | Recorded check results for a service, most recent first. |
| POST | `/services/stop-all` | Stop all currently running check loops. |
| GET | `/` | Basic liveness response. |
| GET | `/dashboard/` | The static dashboard UI. |

## Tech stack

- FastAPI, async SQLAlchemy, asyncpg
- PostgreSQL
- Docker, Docker Compose
- GitHub Actions
- Terraform, AWS EC2
- pytest, pytest-asyncio, pytest-mock, httpx, asgi-lifespan
- Postman / Newman

## Architecture

- `app/main.py` - FastAPI app, lifespan (creates tables, starts all check loops on startup, cancels them on shutdown), routes
- `app/models.py` - SQLAlchemy models: `Service`, `CheckResult`
- `app/schemas.py` - Pydantic request/response schemas
- `app/crud.py` - all database access; every function takes an `AsyncSession` as an argument rather than opening its own session, so routes can inject a session via FastAPI's dependency system and tests can override it with a test session
- `app/checker.py` - `check_service(url, timeout)`, a pure function that pings a service's `/health` endpoint and returns status, response time, and error message
- `app/scheduler.py` - the per-service check loops, the buffered flush loop, alert handling, and the functions that start/stop loops
- `app/state.py` - shared in-memory state: pending check results, last known status per service, currently running loop tasks
- `app/database.py` - engine, session factory, the `get_db` dependency
- `app/config.py` - reads database URLs and flush interval from environment
- `static/` - the dashboard, plain HTML and JS, no framework, polls the API every few seconds
- `dummy/` - a separate, minimal FastAPI service, configurable via environment variables to behave as healthy, unhealthy, slow, or flaky; used for local development and for the end-to-end tests; has its own Dockerfile and its own smaller dependency list
- `tests/` - unit, integration, and end-to-end tests, plus a Postman collection, documented in `tests/README.md`

## Design decisions

**Per-service async loops instead of one batch scheduler.** An earlier version checked every service in one shared cycle using `asyncio.gather`. That meant one slow or timed-out service delayed the whole batch. Each service now runs its own independent `asyncio` loop with its own sleep interval, so a stuck service only ever affects itself.

**Buffered writes instead of write-per-check.** Every check result is appended to an in-memory list, and a separate loop drains and bulk-inserts that list into Postgres on a fixed interval. This cuts write volume significantly compared to committing after every single check. No lock is needed around the shared list: asyncio coroutines are cooperatively scheduled, and a plain list append has no `await` inside it, so nothing can interleave mid-append.

**An in-memory status cache.** The current status of every service is also kept in a plain dictionary, used two ways: to answer the status endpoint instantly without touching the database, and to detect whether a check actually changed a service's status before firing an alert, rather than alerting on every check regardless of whether anything changed.

**Pull-based health checks, not push-based heartbeats.** Sentinel actively pings each service rather than waiting for services to report in. This matches how Kubernetes liveness probes and Prometheus scraping work, and avoids the added complexity a heartbeat model would need to distinguish "quiet" from "dead," since a fully crashed service can't send a heartbeat either.

**No message queue.** The in-memory buffer plus periodic flush is sufficient for a single process with no other process contending for the same state. A queue like Redis would be justified if this ran as multiple processes or workers, which it currently doesn't, so one wasn't added just to look more sophisticated.

**Repository pattern for data access.** Every database query lives in `crud.py`. Nothing else in the app opens a SQLAlchemy session directly. This is what makes FastAPI's dependency injection usable for the database session in routes, and what let tests override that same dependency with a test database session without touching route or query code.

**A deliberately scoped-down test pyramid.** Unit tests cover the two places with real, isolated decision logic: interpreting an HTTP response in the checker, and detecting a status transition in the alert handler. Everything else in the scheduler, starting and stopping loops, is thin orchestration around `asyncio.create_task` and dictionary bookkeeping, and is proven correct by the end-to-end tests actually running the whole system, rather than mocked in isolation for its own sake.

## Running locally

Requires Docker and Docker Compose.

1. Create a `.env` file in the project root:

```
DATABASE_URL=postgresql+asyncpg://postgres:<password>@localhost:5432/health-monitor-db
TEST_DATABASE_URL=postgresql+asyncpg://postgres:<password>@localhost:5433/health-monitor-test-db
FLUSH_INTERVAL=5
```

2. Run:

```
docker compose up --build
```

`docker-compose.override.yml` is picked up automatically alongside `docker-compose.yml` when present, giving a full local development setup in one command: the app built from source rather than pulled, a separate test database, and two dummy services already registered so the dashboard has something real to show immediately.

3. App: `http://localhost:8000`
4. Dashboard: `http://localhost:8000/dashboard/`

## Testing

Four layers: unit, integration, end-to-end, and a Postman collection for manual/API-level testing. Full breakdown, reasoning, and instructions for each in `tests/README.md`.

```
python -m pytest tests/unit -v
python -m pytest tests/integration -v
python -m pytest tests/e2e -v
```

Integration and end-to-end tests run against a separate, real Postgres test database, not SQLite, since the models use Postgres-specific UUID columns and testing against the same engine used in production is more representative than testing against a different one for convenience.

## CI/CD

Defined in `.github/workflows/ci.yml`, triggered on push to `main`. Four stages:

- **Test** - installs dependencies directly (no Docker involved in this stage) and runs the full pytest suite against a Postgres service container that GitHub Actions provisions specifically for this job
- **Build** - builds the application image with Docker Buildx, tagged both with the commit SHA and `latest`
- **Push** - logs into Docker Hub and pushes both tags
- **Deploy** - copies the production compose file onto the live server over SSH, pulls the newly pushed image, restarts the stack with Docker Compose, and prunes old images

Each stage only runs if the one before it succeeds, so a failing test blocks a broken image from ever being built, and a failed build blocks a deploy from ever running against an untested or unbuilt image.

## Infrastructure

Provisioned with Terraform, not created by hand in a console. Resources: one AWS EC2 instance running Ubuntu, a security group allowing inbound SSH and the application's port, with Docker installed automatically on first boot.

The server only runs `health-monitor` and `db`. The pieces that exist purely for development and testing, the second Postgres instance used by tests and the dummy services, live in the local override file only and are never copied to the server or referenced by the production compose file.

Getting the database connection string right across every environment this project touches was one of the more instructive parts of building this: the exact same setting needs a different literal value depending on where the code connecting to it is actually running, since `localhost` and a Docker Compose service name resolve completely differently depending on whether you're inside a container, inside CI, or on your own machine. Locally, outside Docker, it's `localhost`. Inside Docker Compose, the app reaches Postgres through Compose's internal DNS using the service name `db`. In CI, it's `localhost` again, since GitHub's test database is a plain service container, not part of any Compose network. On the deployed server, it's `db` again, for the same reason as local Compose. None of these values is more correct than another; each is only correct for the network it actually runs in.

Secrets never live in the repository. Local and server `.env` files are gitignored, GitHub Actions secrets hold CI's database credentials and the server's SSH key and IP, and the server's own `.env` is created once, by hand, directly on the machine.
