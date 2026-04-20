"""Tests for the persistent plan store."""

from __future__ import annotations

import sqlite3

import pytest

from adloop import store
from adloop.safety import preview as preview_module
from adloop.safety.preview import ChangePlan


# ---------------------------------------------------------------------------
# store.py — direct API
# ---------------------------------------------------------------------------


def _make_plan_kwargs(**overrides):
    base = dict(
        plan_id="abc12345",
        operation="add_keywords",
        entity_type="keyword",
        entity_id="",
        customer_id="123-456-7890",
        changes={"keywords": [{"text": "test", "match_type": "EXACT"}]},
    )
    base.update(overrides)
    return base


def test_save_and_get_plan_roundtrip():
    store.save_plan(**_make_plan_kwargs())

    plan = store.get_plan("abc12345")
    assert plan is not None
    assert plan["plan_id"] == "abc12345"
    assert plan["operation"] == "add_keywords"
    assert plan["status"] == store.STATUS_PENDING
    assert plan["changes"] == {
        "keywords": [{"text": "test", "match_type": "EXACT"}]
    }
    assert plan["customer_id"] == "123-456-7890"
    assert plan["result"] is None
    assert plan["error"] == ""


def test_get_plan_returns_none_for_missing_id():
    assert store.get_plan("does-not-exist") is None


def test_list_plans_filters_by_status():
    store.save_plan(**_make_plan_kwargs(plan_id="p1"))
    store.save_plan(**_make_plan_kwargs(plan_id="p2"))
    store.save_plan(**_make_plan_kwargs(plan_id="p3"))
    store.update_status("p2", store.STATUS_APPLIED, result={"ok": True})

    pending = store.list_plans(status=store.STATUS_PENDING)
    applied = store.list_plans(status=store.STATUS_APPLIED)

    assert {p["plan_id"] for p in pending} == {"p1", "p3"}
    assert {p["plan_id"] for p in applied} == {"p2"}
    assert applied[0]["result"] == {"ok": True}


def test_list_plans_filters_by_customer():
    store.save_plan(**_make_plan_kwargs(plan_id="x", customer_id="111-111-1111"))
    store.save_plan(**_make_plan_kwargs(plan_id="y", customer_id="222-222-2222"))

    result = store.list_plans(customer_id="111-111-1111")
    assert [p["plan_id"] for p in result] == ["x"]


def test_list_plans_orders_newest_first():
    store.save_plan(**_make_plan_kwargs(plan_id="old", created_at="2026-01-01T00:00:00+00:00"))
    store.save_plan(**_make_plan_kwargs(plan_id="mid", created_at="2026-02-01T00:00:00+00:00"))
    store.save_plan(**_make_plan_kwargs(plan_id="new", created_at="2026-03-01T00:00:00+00:00"))

    result = store.list_plans()
    assert [p["plan_id"] for p in result] == ["new", "mid", "old"]


def test_update_status_records_result_and_error():
    store.save_plan(**_make_plan_kwargs(plan_id="p"))

    assert store.update_status("p", store.STATUS_APPLIED, result={"resource": "x/1"})
    plan = store.get_plan("p")
    assert plan is not None
    assert plan["status"] == store.STATUS_APPLIED
    assert plan["result"] == {"resource": "x/1"}

    # FAILED records an error string
    store.save_plan(**_make_plan_kwargs(plan_id="q"))
    assert store.update_status("q", store.STATUS_FAILED, error="boom")
    plan = store.get_plan("q")
    assert plan is not None
    assert plan["status"] == store.STATUS_FAILED
    assert plan["error"] == "boom"


def test_update_status_rejects_invalid_value():
    store.save_plan(**_make_plan_kwargs(plan_id="p"))
    with pytest.raises(ValueError):
        store.update_status("p", "NOT_A_REAL_STATUS")


def test_update_status_on_missing_plan_returns_false():
    assert store.update_status("missing", store.STATUS_APPLIED) is False


def test_delete_plan():
    store.save_plan(**_make_plan_kwargs(plan_id="p"))
    assert store.delete_plan("p")
    assert store.get_plan("p") is None
    assert store.delete_plan("p") is False


def test_clear_plans():
    store.save_plan(**_make_plan_kwargs(plan_id="p1"))
    store.save_plan(**_make_plan_kwargs(plan_id="p2"))
    store.clear_plans()
    assert store.list_plans() == []


# ---------------------------------------------------------------------------
# safety.preview — backwards-compatible wrapper
# ---------------------------------------------------------------------------


def test_preview_store_plan_persists_via_store():
    plan = ChangePlan(
        plan_id="preview1",
        operation="add_keywords",
        entity_type="keyword",
        customer_id="123-456-7890",
        changes={"foo": "bar"},
    )
    preview_module.store_plan(plan)

    retrieved = preview_module.get_plan("preview1")
    assert retrieved is not None
    assert retrieved.plan_id == "preview1"
    assert retrieved.operation == "add_keywords"
    assert retrieved.changes == {"foo": "bar"}


def test_preview_get_plan_hides_non_pending_plans():
    plan = ChangePlan(
        plan_id="preview2",
        operation="add_keywords",
        entity_type="keyword",
        customer_id="123",
        changes={},
    )
    preview_module.store_plan(plan)
    store.update_status("preview2", store.STATUS_APPLIED)

    # Caller of confirm_and_apply should not be able to re-apply.
    assert preview_module.get_plan("preview2") is None

    # But the raw store still has the record for history views.
    row = store.get_plan("preview2")
    assert row is not None
    assert row["status"] == store.STATUS_APPLIED


def test_preview_remove_plan_marks_applied():
    plan = ChangePlan(
        plan_id="preview3",
        operation="add_keywords",
        entity_type="keyword",
        customer_id="123",
        changes={},
    )
    preview_module.store_plan(plan)
    preview_module.remove_plan("preview3")

    row = store.get_plan("preview3")
    assert row is not None
    assert row["status"] == store.STATUS_APPLIED


# ---------------------------------------------------------------------------
# Cross-process / cross-connection persistence
# ---------------------------------------------------------------------------


def test_plan_survives_connection_reopen(tmp_path):
    """The whole point: a plan drafted in one process is visible after
    a fresh connection (simulating MCP restart)."""
    db_path = tmp_path / "survive.db"
    store.set_db_path(db_path)
    store.save_plan(**_make_plan_kwargs(plan_id="survivor"))

    # Drop the open connection — next call re-opens against the same file.
    store.set_db_path(db_path)

    plan = store.get_plan("survivor")
    assert plan is not None
    assert plan["plan_id"] == "survivor"

    # And a raw sqlite3 peek sees the same row, confirming it's on disk.
    raw = sqlite3.connect(str(db_path))
    raw.row_factory = sqlite3.Row
    row = raw.execute("SELECT plan_id, status FROM plans WHERE plan_id = ?", ("survivor",)).fetchone()
    raw.close()
    assert row is not None
    assert row["plan_id"] == "survivor"
    assert row["status"] == store.STATUS_PENDING


def test_dry_run_result_roundtrip():
    store.save_plan(
        **_make_plan_kwargs(
            plan_id="dr",
            dry_run_result={"would_create": 5, "detail": {"nested": True}},
        )
    )
    plan = store.get_plan("dr")
    assert plan is not None
    assert plan["dry_run_result"] == {
        "would_create": 5,
        "detail": {"nested": True},
    }
