# Test Debugging & Infrastructure Guide

This document tracks the major testing hurdles and architectural fixes implemented during the development of the Order Supervisor.

## 1. Database Locking & Terminal Hangs
**Problem**: The test suite would frequently hang at the end of a run (`[DB TEARDOWN] Final cleanup...`), requiring a `taskkill` to resume.
**Cause**: Postgres requires an "Access Exclusive Lock" to drop tables. If an async connection was left "idle in transaction" or not fully closed, the teardown would wait forever for a lock.
**Solution**:
- Removed `drop_all` from the session teardown in `conftest.py`. Tables are now only dropped/recreated at the **start** of a run.
- Added `connect_args={"command_timeout": 10}` to the SQLAlchemy engine to ensure that if a lock *does* occur, the test suite errors out instead of hanging the terminal.
- Implemented `NullPool` to ensure connections are never held in a pool between tests.

## 2. Concurrency Errors (InterfaceError)
**Problem**: `asyncpg.exceptions._base.InterfaceError: cannot perform operation: another operation is in progress`.
**Cause**: Shared event loops or pooled connections being accessed simultaneously by different async tasks.
**Solution**:
- Implemented a session-scoped `event_loop` fixture in `conftest.py` to ensure all async operations (FastAPI, SQLAlchemy, and Pytest) share the exact same loop.
- Ensured all database interaction uses `NullPool`.

## 3. Pydantic Name Conflicts
**Problem**: The `model_config` column name in the database conflicted with Pydantic v2's reserved `model_config` attribute.
**Solution**:
- Renamed the column to `llm_settings`.
- Restored the missing Alembic `script.py.mako` template to allow migrations to run.
- Used `op.alter_column(..., new_column_name=...)` in the migration to safely rename the column in PostgreSQL.

## 4. Test Session Synchronization
**Problem**: Tests would fail with `AssertionError: assert 'sleeping' == 'active'` even when the logic appeared correct.
**Cause**: The test was using one session (`db` fixture) to check status, while the API was using a different session to update it. SQLAlchemy was returning a "cached" version of the object from its identity map.
**Solution**:
- Always use `await db.refresh(obj)` before asserting on object states that were modified by an external API call.

## 5. Phase 4: Reasoning & Tool Execution
**Problem**: The Agent Trigger returns `iterations: 0` and `terminated_early: true`.
**Cause**: The agent loop is protected by status guards. It will only run if the status is `active` or `running`.
**Solution**:
- If a run is `sleeping`, it means it successfully finished its last cycle. To force it to run again, use a fresh run or ensure the status is reset.
- Check `GET /api/runs/{id}/activities` to confirm if a previous cycle already completed.

**Problem**: `422 Unprocessable Content` when sending events.
**Cause**: The `EventCreate` schema uses a strict `Literal` enum for `event_type`.
**Solution**: Ensure the event name matches the strict vocabulary defined in `app/schemas/event.py` (e.g., use `shipment_delayed` instead of `delay_notification`).

**Problem**: `pydantic_core._pydantic_core.ValidationError` on startup.
**Cause**: Extra variables in `.env` (like `MISTRAL_API_KEY`) not defined in the `Settings` class when `extra="forbid"` is active (default).
**Solution**: Added `extra="ignore"` to `SettingsConfigDict` in `app/config.py` to allow flexible environment configuration without crashing the app.

## Phase 6: Final Stabilization
**Problem**: `AttributeError: 'State' object has no attribute 'groq_client'` in older tests.
**Cause**: Endpoints now depend on a global Groq client that might not be initialized in simple API tests using `ASGITransport`.
**Solution**: Added a global `ensure_groq_client_in_app` autouse fixture in `conftest.py` to provide a safety mock.

**Problem**: `StatementError` when saving final summaries in tests.
**Cause**: The Groq mock was returning a `MagicMock` object for the message content, which SQLAlchemy cannot serialize into a JSONB column.
**Solution**: Configured the mock in `conftest.py` to return a static string (`"Global Mock Summary"`) for all LLM calls.
