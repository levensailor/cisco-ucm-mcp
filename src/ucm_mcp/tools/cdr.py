"""CDR on Demand MCP tools."""

from __future__ import annotations

from typing import Any

from ucm_mcp.clients.cdr import get_cdr_client


def register(mcp) -> None:
    @mcp.tool()
    def cdr_list_files(from_date: str, to_date: str) -> dict[str, Any]:
        """List CDR/CMR filenames between from_date and to_date (YYYY-MM-DD HH:MM:SS)."""
        return get_cdr_client().get_file_list(from_date=from_date, to_date=to_date)

    @mcp.tool()
    def cdr_get_file(file_name: str) -> dict[str, Any]:
        """Download a CDR file (truncated at UCM_DOWNLOAD_MAX_BYTES)."""
        return get_cdr_client().get_file(file_name)
