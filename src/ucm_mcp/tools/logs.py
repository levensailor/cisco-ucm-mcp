"""Log Collection MCP tools."""

from __future__ import annotations

from typing import Any

from ucm_mcp.clients.logs import get_logs_client


def register(mcp) -> None:
    @mcp.tool()
    def logs_list_nodes() -> dict[str, Any]:
        """List nodes/services available to the Log Collection API."""
        return get_logs_client().list_nodes()

    @mcp.tool()
    def logs_select_files(service_name: str = "", node: str = "") -> dict[str, Any]:
        """Select log file metadata for a service on a node."""
        return get_logs_client().select_log_files(service_name=service_name, node=node)

    @mcp.tool()
    def logs_download_file(file_name: str) -> dict[str, Any]:
        """Download a log file (truncated at UCM_DOWNLOAD_MAX_BYTES, default 2 MB)."""
        return get_logs_client().download_file(file_name)
