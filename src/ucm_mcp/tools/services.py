"""Control Center MCP tools."""

from __future__ import annotations

from typing import Any

from ucm_mcp.clients.control_center import client_for_node
from ucm_mcp.settings import get_settings


def register(mcp) -> None:
    @mcp.tool()
    def service_products(node: str = "") -> dict[str, Any]:
        """List CUCM product information from Control Center on a node (defaults to UCM_HOST)."""
        settings = get_settings()
        target = node or settings.ucm_host
        return client_for_node(target, settings).list_products()

    @mcp.tool()
    def service_list(node: str = "") -> dict[str, Any]:
        """List services known to Control Center on a node."""
        settings = get_settings()
        target = node or settings.ucm_host
        return client_for_node(target, settings).list_services()

    @mcp.tool()
    def service_status(service: str = "", node: str = "") -> dict[str, Any]:
        """Get service status (and uptime) from Control Center. Empty service returns all."""
        settings = get_settings()
        target = node or settings.ucm_host
        return client_for_node(target, settings).status(service)

    @mcp.tool()
    def service_control(action: str, service: str, node: str = "") -> dict[str, Any]:
        """start, stop, restart, activate, or deactivate a service. Requires UCM_ALLOW_SERVICE_CONTROL=true. Tomcat is refused."""
        settings = get_settings()
        target = node or settings.ucm_host
        return client_for_node(target, settings).control(action, service)
