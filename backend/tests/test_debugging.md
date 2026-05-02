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

## 5. Lifespan & Dependency Overrides
**Problem**: `AttributeError: 'State' object has no attribute 'groq_client'`.
**Cause**: Using the modern `lifespan` handler in FastAPI requires explicit initialization of state variables.
**Solution**:
- Initialized `app.state.groq_client` inside the `lifespan` context manager in `app/main.py`.
- Ensured all tests use `_override_groq` to mock LLM calls, providing environment consistency and speed.
- Registered all routers (supervisors, runs, and events) explicitly in `main.py`.
