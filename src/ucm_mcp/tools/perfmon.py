"""Perfmon MCP tools."""

from __future__ import annotations

from typing import Any, Optional

from ucm_mcp.clients.perfmon import get_perfmon_client


def register(mcp) -> None:
    @mcp.tool()
    def perfmon_sample(
        counters: list[str],
        host: str = "",
    ) -> dict[str, Any]:
        """Open a Perfmon session, sample the given counter paths once, and close the session."""
        return get_perfmon_client().sample(counters, host=host)
