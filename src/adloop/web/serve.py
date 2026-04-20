"""Uvicorn entry point for the approval-UI backend.

Lazy imports so the base ``adloop`` install (which doesn't ship
FastAPI/uvicorn) keeps working. A clear error points users at the
``[web]`` extras if they haven't installed them yet.
"""

from __future__ import annotations

import sys


_EXTRAS_HINT = (
    "The approval UI requires the optional [web] extras. Install with:\n"
    "    uv sync --extra web\n"
    "    # or\n"
    "    pip install 'adloop-meo[web]'"
)


def run(host: str = "127.0.0.1", port: int = 8787) -> None:
    """Start the FastAPI app under uvicorn.

    Defaults to 127.0.0.1 — the UI is local-only by design.
    """
    try:
        import uvicorn
    except ImportError:
        print(_EXTRAS_HINT, file=sys.stderr)
        sys.exit(1)

    try:
        from adloop.web.api import create_app
    except ImportError as exc:  # FastAPI missing
        print(f"{_EXTRAS_HINT}\n\n(underlying error: {exc})", file=sys.stderr)
        sys.exit(1)

    app = create_app()
    print(f"AdLoop approval UI starting on http://{host}:{port}")
    print("Press Ctrl+C to stop.\n")
    uvicorn.run(app, host=host, port=port, log_level="info")
