"""Issue #58 deterministic API-liveness checks, using synthetic TEMP SQLite only."""
from __future__ import annotations

import asyncio
import sqlite3
import threading
import time

import httpx
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from handoff_hub.auto_dispatch import run_dispatch_cycle
from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import make_session_factory
from handoff_hub.provenance_writer import ProvenanceRecorder
from handoff_hub.queue_lifecycle_schema import LIFECYCLE_REVISION
from handoff_hub.schema_admin import upgrade_lifecycle_existing, verify_database
from scripts import lab_environment

HEALTH_LIMIT_SECONDS = 0.25
AUTH_SQL_DELAY_SECONDS = 0.75


def prepare_lifecycle_lab(tmp_path, monkeypatch):
    monkeypatch.setattr(
        lab_environment.tempfile, "gettempdir", lambda: str(tmp_path),
    )
    lab = lab_environment.prepare_lab()
    upgraded = upgrade_lifecycle_existing(
        lab.database, tmp_path / "backups", confirmed=True,
    )
    assert upgraded["revision"] == LIFECYCLE_REVISION
    assert verify_database(lab.database)["integrity"] == "ok"
    return lab


def password_for(lab, username: str) -> str:
    matches = [
        line.split("]: ", 1)[1]
        for line in lab.credentials.read_text(encoding="utf-8").splitlines()
        if line.startswith(username + " [") and "]: " in line
    ]
    assert len(matches) == 1
    return matches[0]


def test_health_live_does_not_wait_for_slow_auth_sql(tmp_path, monkeypatch):
    lab = prepare_lifecycle_lab(tmp_path, monkeypatch)
    app = create_app(database_url=lab.database_url)
    block_next_auth_query = threading.Event()
    auth_query_started = threading.Event()
    release_auth_query = threading.Event()

    def delay_auth_query(connection, cursor, statement, parameters, context, executemany):
        sql = statement.lower()
        if (
            block_next_auth_query.is_set()
            and "auth_sessions" in sql
            and "token_hash" in sql
        ):
            block_next_auth_query.clear()
            auth_query_started.set()
            release_auth_query.wait(timeout=AUTH_SQL_DELAY_SECONDS)

    event.listen(Engine, "before_cursor_execute", delay_auth_query)

    async def exercise():
        async with app.router.lifespan_context(app), httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://issue58-test",
            timeout=3,
        ) as client:
            login = await client.post("/v1/auth/login", json={
                "username": "admin.demo",
                "password": password_for(lab, "admin.demo"),
            })
            assert login.status_code == 200
            token = login.json()["access_token"]
            headers = {"Authorization": "Bearer " + token}
            block_next_auth_query.set()
            started = time.perf_counter()
            auth_request = asyncio.create_task(
                client.get("/v1/admin/overview", headers=headers),
            )
            health_request = asyncio.create_task(
                client.get("/health/live"),
            )
            try:
                health = await asyncio.wait_for(health_request, timeout=2)
                health_latency = time.perf_counter() - started
            finally:
                release_auth_query.set()
            auth = await asyncio.wait_for(auth_request, timeout=2)
            return health.status_code, health_latency, auth.status_code

    try:
        health_status, health_latency, auth_status = asyncio.run(exercise())
    finally:
        release_auth_query.set()
        event.remove(Engine, "before_cursor_execute", delay_auth_query)

    assert auth_query_started.is_set(), "the real AuthSession lookup was not delayed"
    assert auth_status == 200
    assert health_status == 200
    assert health_latency < HEALTH_LIMIT_SECONDS, (
        f"/health/live waited {health_latency * 1000:.1f} ms for an auth SQL pause"
    )


def test_lifecycle_stress_keeps_health_live_during_writer_and_dispatch_contention(
    tmp_path, monkeypatch,
):
    lab = prepare_lifecycle_lab(tmp_path, monkeypatch)
    app = create_app(database_url=lab.database_url)
    dispatcher_factory, dispatcher_engine = make_session_factory(lab.database_url)
    provenance = ProvenanceRecorder(dispatcher_engine)
    dispatch_begin = threading.Event()
    dispatch_done = threading.Event()
    dispatch_result = {}
    dispatch_errors = []

    def observe_dispatch_begin(connection, cursor, statement, parameters, context, executemany):
        if (
            threading.current_thread().name == "issue58-dispatch-probe"
            and statement.strip().upper() == "BEGIN IMMEDIATE"
        ):
            dispatch_begin.set()

    event.listen(dispatcher_engine, "before_cursor_execute", observe_dispatch_begin)

    def dispatch_once():
        try:
            dispatch_result.update(run_dispatch_cycle(dispatcher_factory, provenance))
        except (sqlite3.Error, SQLAlchemyError) as exc:
            dispatch_errors.append(type(exc).__name__)
        finally:
            dispatch_done.set()

    async def exercise():
        health_latencies = []
        responses = []
        async with app.router.lifespan_context(app), httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://issue58-test",
            timeout=4,
        ) as client:
            login = await client.post("/v1/auth/login", json={
                "username": "admin.demo",
                "password": password_for(lab, "admin.demo"),
            })
            assert login.status_code == 200
            headers = {
                "Authorization": "Bearer " + login.json()["access_token"],
                "Content-Type": "application/json",
            }
            created = await client.post(
                "/v1/admin/queues",
                headers=headers,
                json={"id": "qa-issue58", "name": "Issue 58 liveness"},
            )
            assert created.status_code == 201
            activated = await client.patch(
                "/v1/admin/queues/qa-issue58/state",
                headers=headers,
                json={"state": "ACTIVE", "expected_version": 1},
            )
            assert activated.status_code == 200

            async def change_state(state: str, version: int, contend: bool = False):
                release_lock = threading.Event()
                lock_ready = threading.Event()
                lock_thread = None
                dispatch_thread = None
                timer = None
                if contend:
                    def hold_writer():
                        connection = sqlite3.connect(
                            lab.database, timeout=3, isolation_level=None,
                        )
                        try:
                            connection.execute("BEGIN IMMEDIATE")
                            lock_ready.set()
                            release_lock.wait(timeout=2)
                            connection.rollback()
                        finally:
                            connection.close()

                    lock_thread = threading.Thread(
                        target=hold_writer, name="issue58-writer-lock", daemon=True,
                    )
                    lock_thread.start()
                    assert await asyncio.to_thread(lock_ready.wait, 2)
                    dispatch_begin.clear()
                    dispatch_done.clear()
                    dispatch_thread = threading.Thread(
                        target=dispatch_once,
                        name="issue58-dispatch-probe",
                        daemon=True,
                    )
                    dispatch_thread.start()
                    assert await asyncio.to_thread(dispatch_begin.wait, 2)
                    timer = threading.Timer(0.75, release_lock.set)
                    timer.daemon = True
                    timer.start()

                started = time.perf_counter()
                patch_request = asyncio.create_task(client.patch(
                    "/v1/admin/queues/qa-issue58/state",
                    headers=headers,
                    json={"state": state, "expected_version": version},
                ))
                health_request = asyncio.create_task(client.get("/health/live"))
                try:
                    health = await asyncio.wait_for(health_request, timeout=2)
                    health_latencies.append(time.perf_counter() - started)
                finally:
                    release_lock.set()
                    if timer is not None:
                        timer.cancel()
                response = await asyncio.wait_for(patch_request, timeout=3)
                responses.append((response.status_code, response.json()))
                if lock_thread is not None:
                    await asyncio.to_thread(lock_thread.join, 2)
                if dispatch_thread is not None:
                    await asyncio.to_thread(dispatch_thread.join, 2)
                    assert dispatch_done.is_set()
                    assert not dispatch_errors
                    assert dispatch_result["offered"] == 0
                assert health.status_code == 200
                assert response.status_code == 200

            await change_state("PAUSED", 2)
            await change_state("ACTIVE", 3)
            await change_state("PAUSED", 4, contend=True)
            await change_state("ARCHIVED", 5)

        with sqlite3.connect(
            lab.database.as_uri() + "?mode=ro", uri=True, timeout=3,
        ) as db:
            current = db.execute(
                "SELECT state,version FROM queue_lifecycle WHERE queue_id=?",
                ("qa-issue58",),
            ).fetchone()
            events = db.execute(
                "SELECT from_state,to_state,version FROM queue_lifecycle_events "
                "WHERE queue_id=? ORDER BY version",
                ("qa-issue58",),
            ).fetchall()
        return health_latencies, responses, current, events

    try:
        health_latencies, responses, current, events = asyncio.run(exercise())
    finally:
        event.remove(
            dispatcher_engine, "before_cursor_execute", observe_dispatch_begin,
        )
        dispatcher_engine.dispose()

    assert max(health_latencies) < HEALTH_LIMIT_SECONDS, (
        f"/health/live latency exceeded the limit: {health_latencies}"
    )
    assert [status for status, _ in responses] == [200, 200, 200, 200]
    assert [body["version"] for _, body in responses] == [3, 4, 5, 6]
    assert current == ("ARCHIVED", 6)
    assert events == [
        (None, "DRAFT", 1),
        ("DRAFT", "ACTIVE", 2),
        ("ACTIVE", "PAUSED", 3),
        ("PAUSED", "ACTIVE", 4),
        ("ACTIVE", "PAUSED", 5),
        ("PAUSED", "ARCHIVED", 6),
    ]
