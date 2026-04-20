"""Tests for the FastAPI approval-UI backend.

These exercise the HTTP layer directly via ``TestClient`` — no real
Google Ads traffic. ``confirm_and_apply`` is monkey-patched so the
approve flow can be verified without credentials.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from adloop import store  # noqa: E402
from adloop.config import AdLoopConfig, SafetyConfig  # noqa: E402
from adloop.web.api import create_app  # noqa: E402


def _cfg(require_dry_run: bool = False) -> AdLoopConfig:
    return AdLoopConfig(safety=SafetyConfig(require_dry_run=require_dry_run))


def _client(cfg: AdLoopConfig | None = None) -> TestClient:
    return TestClient(create_app(cfg or _cfg()))


def _seed_plan(plan_id: str = "p1", customer_id: str = "123-456-7890") -> None:
    store.save_plan(
        plan_id=plan_id,
        operation="add_keywords",
        entity_type="keyword",
        entity_id="",
        customer_id=customer_id,
        changes={"keywords": [{"text": "test", "match_type": "EXACT"}]},
    )


# ---------------------------------------------------------------------------
# /api/health
# ---------------------------------------------------------------------------


def test_health_reports_require_dry_run_flag():
    client = _client(_cfg(require_dry_run=True))
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["require_dry_run"] is True


# ---------------------------------------------------------------------------
# /api/plans
# ---------------------------------------------------------------------------


def test_list_plans_returns_all_by_default():
    _seed_plan("p1")
    _seed_plan("p2")
    r = _client().get("/api/plans")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert {p["plan_id"] for p in body["plans"]} == {"p1", "p2"}


def test_list_plans_filters_by_status():
    _seed_plan("p1")
    _seed_plan("p2")
    store.update_status("p2", store.STATUS_APPLIED, result={"ok": True})

    r = _client().get("/api/plans", params={"status": store.STATUS_APPLIED})
    assert r.status_code == 200
    body = r.json()
    assert [p["plan_id"] for p in body["plans"]] == ["p2"]


def test_list_plans_rejects_unknown_status():
    r = _client().get("/api/plans", params={"status": "WAT"})
    assert r.status_code == 400
    assert "Invalid status" in r.json()["detail"]


def test_list_plans_filters_by_customer():
    _seed_plan("p1", customer_id="111-111-1111")
    _seed_plan("p2", customer_id="222-222-2222")
    r = _client().get("/api/plans", params={"customer_id": "111-111-1111"})
    assert r.status_code == 200
    assert [p["plan_id"] for p in r.json()["plans"]] == ["p1"]


# ---------------------------------------------------------------------------
# /api/plans/{id}
# ---------------------------------------------------------------------------


def test_get_plan_returns_detail():
    _seed_plan("p1")
    r = _client().get("/api/plans/p1")
    assert r.status_code == 200
    assert r.json()["plan_id"] == "p1"


def test_get_plan_returns_404_when_missing():
    r = _client().get("/api/plans/nope")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# /api/plans/{id}/approve
# ---------------------------------------------------------------------------


def test_approve_missing_plan_returns_404():
    r = _client().post("/api/plans/nope/approve")
    assert r.status_code == 404


def test_approve_non_pending_plan_returns_409():
    _seed_plan("p1")
    store.update_status("p1", store.STATUS_APPLIED, result={"ok": True})

    r = _client().post("/api/plans/p1/approve")
    assert r.status_code == 409
    assert "APPLIED" in r.json()["detail"]


def test_approve_refuses_when_dry_run_required():
    _seed_plan("p1")
    r = _client(_cfg(require_dry_run=True)).post("/api/plans/p1/approve")
    assert r.status_code == 409
    assert "require_dry_run" in r.json()["detail"]


def test_approve_calls_confirm_and_apply(monkeypatch):
    _seed_plan("p1")

    captured: dict = {}

    def fake_apply(cfg, plan_id, dry_run):
        captured["plan_id"] = plan_id
        captured["dry_run"] = dry_run
        return {"status": "applied", "plan_id": plan_id, "resource": "x/1"}

    # The api module imports confirm_and_apply lazily inside the handler,
    # so patch the source module.
    from adloop.ads import write as write_mod

    monkeypatch.setattr(write_mod, "confirm_and_apply", fake_apply)

    r = _client().post("/api/plans/p1/approve")
    assert r.status_code == 200, r.text
    assert captured == {"plan_id": "p1", "dry_run": False}
    assert r.json()["status"] == "applied"


def test_approve_surfaces_apply_errors_as_502(monkeypatch):
    _seed_plan("p1")

    def fake_apply(cfg, plan_id, dry_run):
        return {"error": "boom", "plan_id": plan_id}

    from adloop.ads import write as write_mod

    monkeypatch.setattr(write_mod, "confirm_and_apply", fake_apply)

    r = _client().post("/api/plans/p1/approve")
    assert r.status_code == 502
    assert r.json()["detail"]["error"] == "boom"


# ---------------------------------------------------------------------------
# /api/plans/{id}/reject
# ---------------------------------------------------------------------------


def test_reject_marks_plan_rejected():
    _seed_plan("p1")
    r = _client().post("/api/plans/p1/reject")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "REJECTED"
    assert body["plan"]["status"] == store.STATUS_REJECTED

    # And the change is persisted.
    assert store.get_plan("p1")["status"] == store.STATUS_REJECTED


def test_reject_non_pending_returns_409():
    _seed_plan("p1")
    store.update_status("p1", store.STATUS_APPLIED)

    r = _client().post("/api/plans/p1/reject")
    assert r.status_code == 409


def test_reject_missing_returns_404():
    r = _client().post("/api/plans/nope/reject")
    assert r.status_code == 404
