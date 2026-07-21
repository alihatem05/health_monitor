# Testing Strategy

This project has three layers of automated tests plus a Postman collection for manual API testing.

## Unit tests

Test individual functions in isolation. No database, no network, no running app. External calls are mocked.

test_checker.py covers check_service() against mocked HTTP responses: healthy (200), unhealthy (non 200), timeout, and connection error.

test_scheduler.py covers handle_alert()'s status change logic: first check, no change, and a real transition.

These two files hold the only pieces of pure, isolated decision logic in the codebase. The rest of scheduler.py is orchestration (task creation, dict bookkeeping) and is proven by actually running it, which is what the E2E tests do.

## Integration tests

Test real components against a real, isolated test database.

test_crud.py covers every function in crud.py against a real Postgres test database: create, read, delete, duplicate handling, and history ordering.

test_routes.py covers the FastAPI routes through an async TestClient, exercising the full path from request to route to crud to database.

## End to end tests

Test the full running system. A real scheduler runs against a real, locally started dummy service, and results are verified as they actually appear over time.

test_e2e_flow.py registers a service pointing at a live dummy server, waits for the background check loop to produce results, and asserts on them. It covers all four dummy service behaviors: healthy, unhealthy, slow, and flaky.

This is the only layer that proves check_loop and flusher_loop work correctly, since neither is unit tested directly.

## Postman tests

A separate artifact demonstrating manual and API level QA practice, not a duplicate of the pytest suite. It covers the main endpoints with response assertions and uses environment variables to chain requests, for example reusing a created service's ID in later requests.

See tests/postman/README.md for how to run it manually or through Newman.

## Test database

Integration and E2E tests run against a separate, real Postgres instance (db-test in docker-compose.yml), not SQLite and not the dev database, for two reasons.

The Service and CheckResult models use Postgres specific UUID columns, so SQLite would need workarounds that don't reflect what actually ships.

Testing against the same database engine used in production is more representative than testing against a different one for convenience.

The test database has no persistent volume. It is wiped and rebuilt on every container recreation. Tables are also cleared between individual test runs, handled in conftest.py.

## Running the tests

Start the app and both databases.

docker compose up -d db db-test

Run unit tests only, fast, no database needed.

python -m pytest tests/unit -v

Run integration tests, requires db-test running.

python -m pytest tests/integration -v

Run end to end tests, requires the dummy app to be importable. It spins up its own test server on a background thread.

python -m pytest tests/e2e -v

Run everything.

python -m pytest tests/ -v

## Design notes

pytest.ini sets both asyncio_default_fixture_loop_scope and asyncio_default_test_loop_scope to session, so the shared async engine and connections stay bound to a single event loop for the whole run. Without this, async Postgres connections created in one test's loop cannot be reused in the next.

The client fixture overrides get_db to use the same db_session a test has direct access to, so a test can set up data through crud and verify it through HTTP in the same test, against the same underlying transaction.

start_service_loop, stop_service_loop, start_all_loops, and stop_all_loops are not covered in isolation. This is a deliberate scope decision. They are thin wrappers around asyncio.create_task and dict bookkeeping, and the E2E test already exercises the real startup path they are part of.
