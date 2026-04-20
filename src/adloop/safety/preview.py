"""Change preview formatting — structured output for proposed mutations.

Plans are persisted via :mod:`adloop.store` (SQLite) so they survive
MCP server restarts and can be consumed by external tools such as the
approval web UI.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from adloop import store


@dataclass
class ChangePlan:
    """A proposed change that must be confirmed before execution."""

    plan_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    operation: str = ""
    entity_type: str = ""
    entity_id: str = ""
    customer_id: str = ""
    changes: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    requires_double_confirm: bool = False
    dry_run_result: dict[str, Any] | None = None

    def to_preview(self) -> dict[str, Any]:
        """Format as a human-readable preview dict for the AI to present."""
        return {
            "plan_id": self.plan_id,
            "operation": self.operation,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "customer_id": self.customer_id,
            "changes": self.changes,
            "requires_double_confirm": self.requires_double_confirm,
            "status": "PENDING_CONFIRMATION",
            "instructions": (
                "Review the changes above. To apply, call confirm_and_apply "
                f"with plan_id='{self.plan_id}' and dry_run=false."
            ),
        }


def _plan_from_row(row: dict[str, Any]) -> ChangePlan:
    """Reconstruct a ChangePlan from a store row dict."""
    return ChangePlan(
        plan_id=row["plan_id"],
        operation=row["operation"],
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        customer_id=row["customer_id"],
        changes=row["changes"],
        created_at=row["created_at"],
        requires_double_confirm=row["requires_double_confirm"],
        dry_run_result=row["dry_run_result"],
    )


def store_plan(plan: ChangePlan) -> None:
    """Persist a plan for later retrieval by confirm_and_apply."""
    store.save_plan(
        plan_id=plan.plan_id,
        operation=plan.operation,
        entity_type=plan.entity_type,
        entity_id=plan.entity_id,
        customer_id=plan.customer_id,
        changes=plan.changes,
        requires_double_confirm=plan.requires_double_confirm,
        dry_run_result=plan.dry_run_result,
        created_at=plan.created_at,
    )


def get_plan(plan_id: str) -> ChangePlan | None:
    """Retrieve a stored plan by ID.

    Only returns plans still in ``PENDING`` status — a plan that has
    already been applied or rejected cannot be re-confirmed.
    """
    row = store.get_plan(plan_id)
    if row is None:
        return None
    if row["status"] != store.STATUS_PENDING:
        return None
    return _plan_from_row(row)


def remove_plan(plan_id: str) -> None:
    """Mark a plan as consumed.

    Historically this deleted the in-memory entry. With persistence we
    instead mark it APPLIED so the history view can show it. Callers
    that want to record a different terminal state (FAILED / REJECTED /
    DRY_RUN_SUCCESS) should call :func:`adloop.store.update_status`
    directly with the appropriate status and result/error.
    """
    store.update_status(plan_id, store.STATUS_APPLIED)


def clear_plans() -> None:
    """Wipe all persisted plans. Tests only."""
    store.clear_plans()
