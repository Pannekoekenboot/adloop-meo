"""AdLoop — MCP server connecting Google Ads + GA4 + codebase."""

import sys

__version__ = "0.6.0"


def main() -> None:
    """Entry point for `adloop` console script.

    Routes to the setup wizard when called as ``adloop init``,
    otherwise starts the MCP server.
    """
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        print(f"adloop {__version__}")
        return

    if len(sys.argv) > 1 and sys.argv[1] == "init":
        from adloop.cli import run_init_wizard

        try:
            run_init_wizard()
        except KeyboardInterrupt:
            print("\n\n  Setup cancelled.\n")
            sys.exit(130)
    elif len(sys.argv) > 1 and sys.argv[1] == "web":
        from adloop.web.serve import run as run_web

        try:
            run_web()
        except KeyboardInterrupt:
            print("\n  Approval UI stopped.\n")
            sys.exit(130)
    else:
        from adloop.server import mcp

        mcp.run()
