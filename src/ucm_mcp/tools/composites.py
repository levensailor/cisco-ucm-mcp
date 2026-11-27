"""Cross-API composite MCP tools."""

from __future__ import annotations

import logging
from typing import Any, Optional

from ucm_mcp.clients.axl import get_axl_client
from ucm_mcp.clients.control_center import client_for_node
from ucm_mcp.clients.phone_web import get_phone_web_client
from ucm_mcp.clients.ris import get_ris_client
from ucm_mcp.serialize import error_result, ok_result, to_jsonable
from ucm_mcp.settings import get_settings

logger = logging.getLogger(__name__)


def _device_ip_from_ris(device: dict[str, Any]) -> Optional[str]:
    ip_block = device.get("IPAddress") or {}
    items = ip_block.get("item") if isinstance(ip_block, dict) else ip_block
    if not items:
        return None
    if not isinstance(items, list):
        items = [items]
    for entry in items:
        if isinstance(entry, dict):
            ip = entry.get("IP") or entry.get("IPAddr")
            if ip:
                return ip
    return None


def _flatten_ris_devices(ris_payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = ris_payload.get("data") or {}
    devices: list[dict[str, Any]] = []
    for node in data.get("nodes") or []:
        cm_devices = node.get("CmDevices") or {}
        items = cm_devices.get("item") if isinstance(cm_devices, dict) else cm_devices
        if not items:
            continue
        if not isinstance(items, list):
            items = [items]
        for device in items:
            if isinstance(device, dict):
                enriched = dict(device)
                enriched["_node"] = node.get("Name") or node.get("nodeName")
                devices.append(enriched)
    return devices


def register(mcp) -> None:
    @mcp.tool()
    def phone_status(name: str) -> dict[str, Any]:
        """Join AXL get_phone with RIS registration, IP, login user, and line status for a device name."""
        if not name:
            return error_result("name is required (e.g. SEPF8A5C59E0F1C)")

        axl = get_axl_client()
        phone_result = axl.call("get_phone", {"name": name})
        ris_result = get_ris_client().select_devices(
            items=[name],
            select_by="Name",
            device_class="Phone",
            status="Any",
        )

        registration = None
        if ris_result.get("ok"):
            devices = _flatten_ris_devices(ris_result)
            match = next((d for d in devices if d.get("Name") == name), None)
            if match is None and devices:
                match = devices[0]
            if match:
                registration = {
                    "status": match.get("Status"),
                    "login_user_id": match.get("LoginUserId"),
                    "timestamp": match.get("TimeStamp"),
                    "ip_address": _device_ip_from_ris(match),
                    "lines_status": match.get("LinesStatus"),
                    "node": match.get("_node"),
                    "raw": match,
                }

        return ok_result(
            {
                "name": name,
                "phone": phone_result.get("data") if phone_result.get("ok") else None,
                "phone_error": None if phone_result.get("ok") else phone_result,
                "registration": registration,
                "ris_error": None if ris_result.get("ok") else ris_result,
            }
        )

    @mcp.tool()
    def cluster_service_status(service: str = "") -> dict[str, Any]:
        """List process nodes via AXL, skip EnterpriseWideData, and query Control Center status on each."""
        axl = get_axl_client()
        nodes_result = axl.call("list_process_nodes", {})
        if not nodes_result.get("ok"):
            return nodes_result

        nodes = nodes_result.get("data") or []
        if not isinstance(nodes, list):
            nodes = [nodes]

        settings = get_settings()
        rows: list[dict[str, Any]] = []
        for node in nodes:
            node_data = to_jsonable(node)
            node_name = (
                node_data.get("name")
                or node_data.get("Name")
                or (node_data if isinstance(node_data, str) else None)
            )
            if not node_name or node_name == "EnterpriseWideData":
                continue
            status = client_for_node(node_name, settings).status(service)
            rows.append(
                {
                    "node": node_name,
                    "ok": status.get("ok", False),
                    "services": status.get("data") if status.get("ok") else None,
                    "error": status.get("error") if not status.get("ok") else None,
                }
            )
        return ok_result(rows, service=service or "all", node_count=len(rows))

    @mcp.tool()
    def phone_inventory(name: str) -> dict[str, Any]:
        """Resolve a device name via RIS to its registered IP, then scrape the phone web inventory pages."""
        if not name:
            return error_result("name is required")

        ris_result = get_ris_client().select_devices(
            items=[name],
            select_by="Name",
            device_class="Phone",
            status="Any",
        )
        if not ris_result.get("ok"):
            return ris_result

        devices = _flatten_ris_devices(ris_result)
        match = next((d for d in devices if d.get("Name") == name), None)
        if match is None and devices:
            match = devices[0]
        if not match:
            return error_result(f"No RIS data found for {name}")

        ip_address = _device_ip_from_ris(match)
        if not ip_address:
            return error_result(
                f"Device {name} has no IP address in RIS",
                registration=match,
            )

        model = match.get("Model") or match.get("Product") or ""
        # Prefer human product string when model is numeric
        details = get_phone_web_client().all_details(ip_address, model=str(model))
        return ok_result(
            {
                "name": name,
                "ip_address": ip_address,
                "registration": match,
                "details": details.get("data") if details.get("ok") else None,
                "details_error": None if details.get("ok") else details,
            }
        )
