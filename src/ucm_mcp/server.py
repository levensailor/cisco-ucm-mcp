"""Cisco UCM MCP server entrypoint."""

from __future__ import annotations

import logging

from mcp.server.mcpserver import MCPServer

from ucm_mcp import __version__
from ucm_mcp.logging_config import setup_logging
from ucm_mcp.settings import get_settings
from ucm_mcp.tools import register_all

logger = logging.getLogger(__name__)

mcp = MCPServer(
    "ucm-mcp",
    version=__version__,
    instructions=(
        "Cisco Unified Communications Manager MCP server. "
        "Use axl_list_operations / axl_describe_operation / axl_call for the full AXL surface. "
        "Use ris_select_devices, service_*, perfmon_sample, logs_*, cdr_*, and phone_* for "
        "serviceability and phone APIs. Write and phone-execute tools are gated by env flags."
    ),
)

register_all(mcp)


def main() -> None:
    """Start the MCP server over stdio or Streamable HTTP."""
    settings = get_settings()
    setup_logging(settings.ucm_log_dir, settings.ucm_log_level)
    logger.info("Starting ucm-mcp %s transport=%s", __version__, settings.ucm_transport)

    transport = (settings.ucm_transport or "stdio").lower()
    if transport == "http":
        mcp.run(
            transport="streamable-http",
            host=settings.ucm_http_host,
            port=settings.ucm_http_port,
        )
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
