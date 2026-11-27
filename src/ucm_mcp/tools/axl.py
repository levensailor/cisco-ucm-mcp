"""AXL discovery and dispatch MCP tools."""

from __future__ import annotations

from typing import Any, Optional

from ucm_mcp.clients.axl import get_axl_client
from ucm_mcp.serialize import error_result, ok_result


def register(mcp) -> None:
    @mcp.tool()
    def axl_list_operations(
        prefix: str = "",
        contains: str = "",
        classification: str = "",
    ) -> dict[str, Any]:
        """List ciscoaxl public methods. Filter by prefix, substring, or classification (read/write/unknown)."""
        client = get_axl_client()
        ops = client.list_operations(
            prefix=prefix,
            contains=contains,
            classification=classification,
        )
        return ok_result(ops, count=len(ops))

    @mcp.tool()
    def axl_describe_operation(name: str) -> dict[str, Any]:
        """Return signature, parameters, docstring, and read/write classification for an AXL method."""
        client = get_axl_client()
        try:
            return ok_result(client.describe_operation(name))
        except AttributeError as exc:
            return error_result(str(exc))

    @mcp.tool()
    def axl_call(
        operation: str,
        arguments: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Call any ciscoaxl method by name with a JSON argument object. Mutating ops need UCM_ALLOW_WRITES=true."""
        return get_axl_client().call(operation, arguments or {})

    @mcp.tool()
    def axl_sql_query(query: str) -> dict[str, Any]:
        """Run a single read-only SELECT/WITH SQL query against the CUCM database via AXL."""
        try:
            return get_axl_client().sql_query(query)
        except ValueError as exc:
            return error_result(str(exc))

    @mcp.tool()
    def axl_sql_update(query: str) -> dict[str, Any]:
        """Run a single mutating SQL statement via AXL. Requires UCM_ALLOW_WRITES=true."""
        return get_axl_client().sql_update(query)
