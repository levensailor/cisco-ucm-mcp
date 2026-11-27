"""RIS MCP tools."""

from __future__ import annotations

from typing import Any, Optional

from ucm_mcp.clients.ris import get_ris_client


def register(mcp) -> None:
    @mcp.tool()
    def ris_select_devices(
        items: Optional[list[str]] = None,
        select_by: str = "Name",
        device_class: str = "Phone",
        model: int = 255,
        status: str = "Any",
        protocol: str = "Any",
        download_status: str = "Any",
        node_name: str = "",
        max_returned_devices: int = 1000,
        state_info: str = "",
    ) -> dict[str, Any]:
        """Query RisPort70 for device registration. select_by: Name, DirNumber, IPV4Address, Description."""
        return get_ris_client().select_devices(
            items=items,
            select_by=select_by,
            device_class=device_class,
            model=model,
            status=status,
            protocol=protocol,
            download_status=download_status,
            node_name=node_name,
            max_returned_devices=max_returned_devices,
            state_info=state_info,
        )
