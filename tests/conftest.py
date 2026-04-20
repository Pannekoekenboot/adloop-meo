"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from adloop import store


@pytest.fixture(autouse=True)
def _isolate_plan_store(tmp_path, monkeypatch):
    """Route every test's plan persistence to a fresh SQLite file.

    Without this, tests would share ``~/.adloop/plans.db`` with the
    developer's real AdLoop install and leak state between cases.
    """
    store.set_db_path(tmp_path / "plans.db")
    try:
        yield
    finally:
        store.clear_plans()
        store.set_db_path(None)
