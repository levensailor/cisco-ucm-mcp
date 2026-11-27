"""MCP tool registration helpers."""

from ucm_mcp.tools import axl as axl_tools
from ucm_mcp.tools import cdr as cdr_tools
from ucm_mcp.tools import composites as composite_tools
from ucm_mcp.tools import logs as logs_tools
from ucm_mcp.tools import perfmon as perfmon_tools
from ucm_mcp.tools import phones as phone_tools
from ucm_mcp.tools import ris as ris_tools
from ucm_mcp.tools import services as service_tools


def register_all(mcp) -> None:
    """Register every tool group on the MCPServer instance."""
    axl_tools.register(mcp)
    ris_tools.register(mcp)
    service_tools.register(mcp)
    perfmon_tools.register(mcp)
    logs_tools.register(mcp)
    cdr_tools.register(mcp)
    phone_tools.register(mcp)
    composite_tools.register(mcp)
