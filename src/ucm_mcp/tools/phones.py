"""Phone web and XSI Execute MCP tools."""

from __future__ import annotations

from typing import Any, Optional

from ucm_mcp.clients.phone_web import get_phone_web_client
from ucm_mcp.clients.phone_xsi import get_phone_xsi_client


def register(mcp) -> None:
    @mcp.tool()
    def phone_details(phone_ip: str, model: str = "") -> dict[str, Any]:
        """Scrape a phone's device/network/status web pages into a structured inventory dict."""
        return get_phone_web_client().all_details(phone_ip, model=model)

    @mcp.tool()
    def phone_press(phone_ip: str, key: str) -> dict[str, Any]:
        """Press a phone key via CGI Execute. Requires UCM_ALLOW_PHONE_EXECUTE and PHONE_* credentials."""
        return get_phone_xsi_client().press(phone_ip, key)

    @mcp.tool()
    def phone_execute(phone_ip: str, uris: list[str]) -> dict[str, Any]:
        """POST CiscoIPPhoneExecute URIs (Key:, Dial:, Init:, Display:). Requires phone-execute gate."""
        return get_phone_xsi_client().execute(phone_ip, uris)

    @mcp.tool()
    def phone_reset_itl(phone_ip: str, model: str) -> dict[str, Any]:
        """Run model-specific ITL wipe key macros (794x/796x, 797x, 88xx). Requires phone-execute gate."""
        return get_phone_xsi_client().reset_itl(phone_ip, model)
