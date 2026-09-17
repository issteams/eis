"""SQLite persistence for resumable engineering workflows."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Iterator
from uuid import UUID

from eis.workflows.models import (
    WorkflowApproval,
    WorkflowEvent,
    WorkflowPhase,
    WorkflowRequest,
    WorkflowState,
    WorkflowStatus,
)


class WorkflowStore:
    """Durable workflow state store with atomic state replacement."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    objective TEXT NOT NULL,
                    repository TEXT NOT NULL,
                    input_json TEXT,
                    status TEXT NOT NULL,
                    phase_index INTEGER NOT NULL,
                    events_json TEXT NOT NULL,
                    approval_json TEXT,
                    data_json TEXT NOT NULL,
                    escalation_reason TEXT
                )"""
            )

    def save(self, state: WorkflowState) -> None:
        approval = asdict(state.approval) if state.approval else None
        events = [asdict(event) for event in state.events]
        payload = (
            str(state.request.id),
            state.request.objective,
            state.request.repository,
            json.dumps(state.request.input),
            state.status.value,
            state.phase_index,
            json.dumps(events, default=str),
            json.dumps(approval, default=str),
            json.dumps(state.data, default=str),
            state.escalation_reason,
        )
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO workflows
                (id, objective, repository, input_json, status, phase_index,
                 events_json, approval_json, data_json, escalation_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    objective=excluded.objective,
                    repository=excluded.repository,
                    input_json=excluded.input_json,
                    status=excluded.status,
                    phase_index=excluded.phase_index,
                    events_json=excluded.events_json,
                    approval_json=excluded.approval_json,
                    data_json=excluded.data_json,
                    escalation_reason=excluded.escalation_reason""",
                payload,
            )

    def load(self, workflow_id: UUID | str) -> WorkflowState | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM workflows WHERE id = ?", (str(workflow_id),)
            ).fetchone()
        if row is None:
            return None
        request = WorkflowRequest(
            objective=row["objective"],
            repository=row["repository"],
            input=json.loads(row["input_json"]) if row["input_json"] else None,
            id=UUID(row["id"]),
        )
        events = tuple(
            WorkflowEvent(
                phase=WorkflowPhase(item["phase"]),
                status=item["status"],
                detail=item.get("detail", ""),
                evidence=tuple(item.get("evidence", ())),
                failures=tuple(item.get("failures", ())),
                corrections=tuple(item.get("corrections", ())),
                risks=tuple(item.get("risks", ())),
                uncertainty=tuple(item.get("uncertainty", ())),
                id=UUID(item["id"]),
            )
            for item in json.loads(row["events_json"])
        )
        approval_data = json.loads(row["approval_json"]) if row["approval_json"] else None
        approval = (
            WorkflowApproval(
                phase=WorkflowPhase(approval_data["phase"]),
                resource=approval_data["resource"],
                reason=approval_data["reason"],
                approval_request_id=UUID(approval_data["approval_request_id"]),
            )
            if approval_data
            else None
        )
        return WorkflowState(
            request=request,
            status=WorkflowStatus(row["status"]),
            phase_index=row["phase_index"],
            events=events,
            approval=approval,
            data=json.loads(row["data_json"]),
            escalation_reason=row["escalation_reason"],
        )