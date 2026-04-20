"""Persistent plan store backed by SQLite.

Plans previously lived only in an in-memory dict and were lost on MCP
server restart. They now persist to ``~/.adloop/plans.db`` so:

* a plan can survive an MCP restart between draft and apply
* a separate process (the approval web UI) can read pending plans and
  mark them approved / rejected

The public API mirrors the previous in-memory module (``save_plan``,
``get_plan``, ``update_status`` …) and is wrapped by ``safety.preview``
for backwards compatibility.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS plans (
    plan_id                 TEXT PRIMARY KEY,
    operation               TEXT NOT NULL,
    entity_type             TEXT NOT NULL,
    entity_id               TEXT NOT NULL DEFAULT '',
    customer_id             TEXT NOT NULL DEFAULT '',
    changes_json            TEXT NOT NULL,
    requires_double_confirm INTEGER NOT NULL DEFAULT 0,
    dry_run_result_json     TEXT,
    created_at              TEXT NOT NULL,
    updated_at              TEXT NOT NULL,
    status                  TEXT NOT NULL DEFAULT 'PENDING',
    result_json             TEXT,
    error_text              TEXT
);

CREATE INDEX IF NOT EXISTS idx_plans_status   ON plans(status);
CREATE INDEX IF NOT EXISTS idx_plans_customer ON plans(customer_id);
CREATE INDEX IF NOT EXISTS idx_plans_created  ON plans(created_at DESC);
"""

# Plan lifecycle states. Any transition writes ``updated_at``.
STATUS_PENDING = "PENDING"
STATUS_APPLIED = "APPLIED"
STATUS_REJECTED = "REJECTED"
STATUS_FAILED = "FAILED"
STATUS_DRY_RUN = "DRY_RUN_SUCCESS"  # terminal, distinct from APPLIED

VALID_STATUSES = {
    STATUS_PENDING,
    STATUS_APPLIED,
    STATUS_REJECTED,
    STATUS_FAILED,
    STATUS_DRY_RUN,
}

# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

_DEFAULT_DB_PATH = Path.home() / ".adloop" / "plans.db"
_db_path: Path | None = None
_connection: sqlite3.Connection | None = None


def set_db_path(path: str | Path | None) -> None:
    """Override the DB path (used by tests, or to keep state in tmpdirs).

    Passing ``None`` reverts to the default ``~/.adloop/plans.db``. Any
    existing connection is closed so the next call re-opens against the
    new path.
    """
    global _db_path, _connection
    if _connection is not None:
        try:
            _connection.close()
        finally:
            _connection = None
    _db_path = Path(path) if path is not None else None


def _resolve_db_path() -> Path:
    path = _db_path if _db_path is not None else _DEFAULT_DB_PATH
    if path != Path(":memory:"):
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        path = _resolve_db_path()
        # isolation_level=None => autocommit; we manage transactions
        # explicitly with BEGIN / COMMIT via the `transaction` ctx mgr.
        _connection = sqlite3.connect(
            str(path),
            isolation_level=None,
            check_same_thread=False,
            timeout=5.0,
        )
        _connection.row_factory = sqlite3.Row
        # WAL allows concurrent readers (the web UI) while the MCP
        # server is writing.  Safe for single-machine multi-process.
        if str(path) != ":memory:":
            _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA foreign_keys=ON")
        _connection.executescript(SCHEMA)
    return _connection


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    conn = _get_connection()
    conn.execute("BEGIN")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Row <-> dict conversion
# ---------------------------------------------------------------------------


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "plan_id": row["plan_id"],
        "operation": row["operation"],
        "entity_type": row["entity_type"],
        "entity_id": row["entity_id"],
        "customer_id": row["customer_id"],
        "changes": json.loads(row["changes_json"]),
        "requires_double_confirm": bool(row["requires_double_confirm"]),
        "dry_run_result": (
            json.loads(row["dry_run_result_json"])
            if row["dry_run_result_json"] is not None
            else None
        ),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "status": row["status"],
        "result": (
            json.loads(row["result_json"])
            if row["result_json"] is not None
            else None
        ),
        "error": row["error_text"] or "",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def save_plan(
    *,
    plan_id: str,
    operation: str,
    entity_type: str,
    entity_id: str,
    customer_id: str,
    changes: dict[str, Any],
    requires_double_confirm: bool = False,
    dry_run_result: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> None:
    """Insert a new plan with status=PENDING.

    If the plan_id already exists it is replaced — draft tools generate
    fresh UUIDs so this only happens in tests.
    """
    now = created_at or _now()
    conn = _get_connection()
    conn.execute(
        """
        INSERT OR REPLACE INTO plans (
            plan_id, operation, entity_type, entity_id, customer_id,
            changes_json, requires_double_confirm, dry_run_result_json,
            created_at, updated_at, status, result_json, error_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
        """,
        (
            plan_id,
            operation,
            entity_type,
            entity_id,
            customer_id,
            json.dumps(changes, default=str),
            1 if requires_double_confirm else 0,
            json.dumps(dry_run_result, default=str) if dry_run_result is not None else None,
            now,
            now,
            STATUS_PENDING,
        ),
    )


def get_plan(plan_id: str) -> dict[str, Any] | None:
    """Return the plan dict, or ``None`` if not found."""
    conn = _get_connection()
    row = conn.execute(
        "SELECT * FROM plans WHERE plan_id = ?", (plan_id,)
    ).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def list_plans(
    *,
    status: str | None = None,
    customer_id: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return plans filtered by status / customer, newest first."""
    conn = _get_connection()
    clauses: list[str] = []
    params: list[Any] = []
    if status is not None:
        clauses.append("status = ?")
        params.append(status)
    if customer_id is not None:
        clauses.append("customer_id = ?")
        params.append(customer_id)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(int(limit))
    rows = conn.execute(
        f"SELECT * FROM plans{where} ORDER BY created_at DESC LIMIT ?",
        params,
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def update_status(
    plan_id: str,
    status: str,
    *,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> bool:
    """Update plan status. Returns True if a row was updated."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status!r}")
    conn = _get_connection()
    cur = conn.execute(
        """
        UPDATE plans
        SET status = ?,
            updated_at = ?,
            result_json = COALESCE(?, result_json),
            error_text = COALESCE(?, error_text)
        WHERE plan_id = ?
        """,
        (
            status,
            _now(),
            json.dumps(result, default=str) if result is not None else None,
            error,
            plan_id,
        ),
    )
    return cur.rowcount > 0


def delete_plan(plan_id: str) -> bool:
    """Hard-delete a plan. Rarely used — prefer ``update_status``."""
    conn = _get_connection()
    cur = conn.execute("DELETE FROM plans WHERE plan_id = ?", (plan_id,))
    return cur.rowcount > 0


def clear_plans() -> None:
    """Remove every plan. Intended for tests only."""
    conn = _get_connection()
    conn.execute("DELETE FROM plans")
