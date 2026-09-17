"""Persistent long-running job state and safe recovery primitives."""

from __future__ import annotations

import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Job:
    id: str
    kind: str
    payload: str
    status: str
    attempts: int
    lease_until: float | None
    error: str | None = None


class JobStore:
    """SQLite-backed durable job store suitable for a single worker database."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        with self._connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS jobs ("
                "id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL, "
                "status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, "
                "lease_until REAL, error TEXT)"
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10.0)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def enqueue(self, kind: str, payload: str) -> Job:
        job = Job(uuid.uuid4().hex, kind, payload, "queued", 0, None)
        with self._connect() as db:
            db.execute(
                "INSERT INTO jobs(id,kind,payload,status,attempts,lease_until,error) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    job.id,
                    job.kind,
                    job.payload,
                    job.status,
                    job.attempts,
                    job.lease_until,
                    job.error,
                ),
            )
        return job

    def recover_expired(self, now: float | None = None) -> int:
        current = time.time() if now is None else now
        with self._connect() as db:
            result = db.execute(
                "UPDATE jobs SET status='queued', lease_until=NULL "
                "WHERE status='running' AND lease_until IS NOT NULL AND lease_until < ?",
                (current,),
            )
            return result.rowcount

    def claim(self, lease_seconds: int = 300) -> Job | None:
        now = time.time()
        lease = now + lease_seconds
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM jobs WHERE status='queued' ORDER BY rowid LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            updated = db.execute(
                "UPDATE jobs SET status='running', attempts=attempts+1, lease_until=? "
                "WHERE id=? AND status='queued'",
                (lease, row["id"]),
            )
            if updated.rowcount != 1:
                return None
            return Job(
                row["id"],
                row["kind"],
                row["payload"],
                "running",
                row["attempts"] + 1,
                lease,
                row["error"],
            )

    def complete(self, job_id: str) -> None:
        with self._connect() as db:
            db.execute("UPDATE jobs SET status='completed', lease_until=NULL WHERE id=?", (job_id,))

    def fail(self, job_id: str, error: str, *, retry: bool) -> None:
        with self._connect() as db:
            db.execute(
                "UPDATE jobs SET status=?, lease_until=NULL, error=? WHERE id=?",
                ("queued" if retry else "failed", error[:4000], job_id),
            )

    def get(self, job_id: str) -> Job | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            return None
        return Job(
            row["id"],
            row["kind"],
            row["payload"],
            row["status"],
            row["attempts"],
            row["lease_until"],
            row["error"],
        )


class GracefulShutdown:
    """Coordinates readiness removal and bounded worker shutdown."""

    def __init__(self) -> None:
        self.stopping = False

    def begin(self) -> None:
        self.stopping = True

    def should_accept(self) -> bool:
        return not self.stopping


__all__ = ["GracefulShutdown", "Job", "JobStore"]
