"""Approval-UI backend for AdLoop.

This package exposes a small FastAPI application that reads and
mutates the SQLite plan store populated by the MCP server, so a team
can review and approve proposed Google Ads changes from a browser
instead of from the Claude Code terminal.

The module only imports FastAPI / uvicorn lazily so the base ``adloop``
install (which does not need the web UI) stays light. Install the
optional extras to enable it::

    uv sync --extra web
    # or
    pip install 'adloop-meo[web]'
"""
