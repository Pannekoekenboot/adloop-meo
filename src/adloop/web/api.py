"""FastAPI application for the approval UI.

Endpoints (all JSON, all under ``/api``):

* ``GET  /api/health``                — liveness probe
* ``GET  /api/plans``                 — list plans, filterable by status
                                        and customer_id
* ``GET  /api/plans/{plan_id}``       — full plan detail
* ``POST /api/plans/{plan_id}/approve`` — apply the plan to Google Ads
* ``POST /api/plans/{plan_id}/reject``  — mark the plan as REJECTED
* ``GET  /api/accounts``              — list accessible Ads accounts
                                        (proxies ``list_accounts``)

The write endpoints reuse ``adloop.ads.write.confirm_and_apply`` so
that approving via the web UI runs through exactly the same safety
checks and audit logging as approving via Claude.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from adloop import store
from adloop.config import AdLoopConfig, load_config

# Location of the compiled Next.js bundle. Populated by
# ``scripts/build-web-ui.sh`` (or a manual ``npm run build`` inside
# ``web-ui/``) and copied into the package so ``pip install`` picks it up.
_STATIC_DIR = Path(__file__).parent / "static"


def create_app(config: AdLoopConfig | None = None) -> FastAPI:
    """Build the FastAPI app.

    ``config`` is injected in tests; in production we load from the
    normal config path on first call.
    """
    cfg = config if config is not None else load_config()

    app = FastAPI(
        title="AdLoop Approval UI",
        version="0.1.0",
        description=(
            "Local-only approval queue for AdLoop plans. "
            "Not intended to be exposed beyond 127.0.0.1."
        ),
    )

    # The Next.js dev server runs on :3000; the built static bundle
    # will be served from the same origin so CORS is only needed in
    # development. Keep the list explicit — no wildcard for a tool
    # that calls the Google Ads API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    _register_routes(app, cfg)
    _mount_static_ui(app)
    return app


def _mount_static_ui(app: FastAPI) -> None:
    """Serve the compiled Next.js bundle from the same origin as the API.

    Routes are registered before this mount, so /api/* always takes
    precedence. If the bundle hasn't been built (dev setups running
    ``next dev`` on :3000 separately), we just skip the mount and log
    a hint.
    """
    if not _STATIC_DIR.is_dir() or not (_STATIC_DIR / "index.html").is_file():
        # Runs during dev when the bundle hasn't been built yet. Not
        # an error — the Next dev server on :3000 will proxy to this
        # FastAPI via the rewrites() in next.config.ts.
        @app.get("/", include_in_schema=False)
        def _no_bundle() -> dict[str, str]:
            return {
                "status": "api-only",
                "hint": (
                    "The UI bundle is not built. Either run `npm run dev` "
                    "in web-ui/ (which proxies /api here), or build the "
                    "bundle with `scripts/build-web-ui.sh`."
                ),
            }

        return

    # ``html=True`` makes StaticFiles serve index.html for directory
    # requests and fall back to 404.html for unknown paths.
    app.mount(
        "/",
        StaticFiles(directory=str(_STATIC_DIR), html=True),
        name="ui",
    )


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


def _register_routes(app: FastAPI, cfg: AdLoopConfig) -> None:
    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "require_dry_run": cfg.safety.require_dry_run,
        }

    @app.get("/api/plans")
    def list_plans(
        status: str | None = Query(
            default=None,
            description="Filter by status (PENDING, APPLIED, REJECTED, FAILED, DRY_RUN_SUCCESS).",
        ),
        customer_id: str | None = Query(
            default=None, description="Filter by Google Ads customer_id."
        ),
        limit: int = Query(default=200, ge=1, le=1000),
    ) -> dict[str, Any]:
        if status is not None and status not in store.VALID_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid status '{status}'. "
                    f"Allowed: {sorted(store.VALID_STATUSES)}."
                ),
            )
        plans = store.list_plans(
            status=status,
            customer_id=customer_id,
            limit=limit,
        )
        return {"plans": plans, "count": len(plans)}

    @app.get("/api/plans/{plan_id}")
    def get_plan(plan_id: str) -> dict[str, Any]:
        plan = store.get_plan(plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail=f"Plan '{plan_id}' not found.")
        return plan

    @app.post("/api/plans/{plan_id}/approve")
    def approve_plan(plan_id: str) -> dict[str, Any]:
        existing = store.get_plan(plan_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Plan '{plan_id}' not found.")
        if existing["status"] != store.STATUS_PENDING:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Plan '{plan_id}' cannot be approved — current status is "
                    f"{existing['status']}. Only PENDING plans are actionable."
                ),
            )

        # Refuse up front when the config forces dry-run mode; silently
        # succeeding as DRY_RUN_SUCCESS when the user clicked "Approve"
        # would be misleading.
        if cfg.safety.require_dry_run:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Cannot approve: safety.require_dry_run is true in "
                    "~/.adloop/config.yaml. Set it to false to enable "
                    "real mutations from the web UI."
                ),
            )

        # Reuse the same function Claude calls. It loads the plan from
        # the store, executes the mutation, writes audit log, and
        # updates the plan's status to APPLIED or FAILED.
        from adloop.ads.write import confirm_and_apply as _apply

        result = _apply(cfg, plan_id=plan_id, dry_run=False)
        if "error" in result:
            # _apply has already recorded FAILED status; surface to client.
            raise HTTPException(status_code=502, detail=result)
        return result

    @app.post("/api/plans/{plan_id}/reject")
    def reject_plan(plan_id: str) -> dict[str, Any]:
        existing = store.get_plan(plan_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Plan '{plan_id}' not found.")
        if existing["status"] != store.STATUS_PENDING:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Plan '{plan_id}' cannot be rejected — current status is "
                    f"{existing['status']}. Only PENDING plans are actionable."
                ),
            )

        store.update_status(plan_id, store.STATUS_REJECTED)
        updated = store.get_plan(plan_id)
        return {"status": "REJECTED", "plan": updated}

    @app.get("/api/accounts")
    def list_accounts() -> dict[str, Any]:
        """Proxy ``adloop.ads.read.list_accounts`` so the UI can fill
        the account switcher dropdown."""
        from adloop.ads.read import list_accounts as _list_accounts

        try:
            result = _list_accounts(cfg)
        except Exception as exc:  # pragma: no cover — depends on auth
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return result
