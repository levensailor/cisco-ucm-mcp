"""RisPort70 client for real-time device registration queries."""

from __future__ import annotations

import logging
from typing import Any, Optional

from zeep.exceptions import Fault

from ucm_mcp.clients.session import soap_service
from ucm_mcp.serialize import error_result, ok_result, to_jsonable
from ucm_mcp.settings import Settings, get_settings

logger = logging.getLogger(__name__)

RIS_BINDING = "{http://schemas.cisco.com/ast/soap}RisBinding"
CHUNK_SIZE = 1000


class RisClient:
    """Query CUCM RisPort70 selectCmDevice / selectCmDeviceExt."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._service = None

    def _endpoint(self) -> str:
        host = self.settings.ucm_host
        port = self.settings.ucm_port
        return f"https://{host}:{port}/realtimeservice2/services/RISService70"

    def connect(self):
        if self._service is not None:
            return self._service
        self.settings.require_connection()
        wsdl = f"{self._endpoint()}?wsdl"
        self._service = soap_service(
            self.settings,
            wsdl,
            RIS_BINDING,
            self._endpoint(),
        )
        return self._service

    def select_devices(
        self,
        *,
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
        """Query device registration status, chunking items and merging nodes."""
        service = self.connect()
        select_items = items or ["*"]
        max_returned = min(max(1, max_returned_devices), 2000)

        chunks = [
            select_items[i : i + CHUNK_SIZE]
            for i in range(0, len(select_items), CHUNK_SIZE)
        ] or [["*"]]

        merged_nodes: dict[str, Any] = {}
        last_state = state_info
        total = 0

        for chunk in chunks:
            criteria = {
                "MaxReturnedDevices": str(min(len(chunk), max_returned) if chunk != ["*"] else max_returned),
                "DeviceClass": device_class,
                "Model": model,
                "Status": status,
                "NodeName": node_name or "",
                "SelectBy": select_by,
                "SelectItems": {"item": [{"Item": item} for item in chunk]},
                "Protocol": protocol,
                "DownloadStatus": download_status,
            }
            # Cap MaxReturnedDevices to API max
            criteria["MaxReturnedDevices"] = str(
                min(int(criteria["MaxReturnedDevices"]), 2000)
            )
            logger.info(
                "RIS selectCmDevice select_by=%s items=%d node=%s",
                select_by,
                len(chunk),
                node_name or "*",
            )
            try:
                if hasattr(service, "selectCmDeviceExt"):
                    response = service.selectCmDeviceExt(last_state, criteria)
                else:
                    response = service.selectCmDevice(last_state, criteria)
            except Fault as fault:
                return error_result(fault.message or str(fault), fault=str(fault))
            except Exception as exc:  # noqa: BLE001
                logger.exception("RIS query failed")
                return error_result(str(exc))

            result = getattr(response, "SelectCmDeviceResult", response)
            last_state = getattr(response, "StateInfo", last_state) or last_state
            total += int(getattr(result, "TotalDevicesFound", 0) or 0)

            cm_nodes = getattr(result, "CmNodes", None)
            if cm_nodes is None:
                continue
            node_list = getattr(cm_nodes, "item", cm_nodes) or []
            if not isinstance(node_list, list):
                node_list = [node_list]
            for node in node_list:
                node_data = to_jsonable(node)
                name = (
                    node_data.get("Name")
                    or node_data.get("nodeName")
                    or node_data.get("NodeName")
                    or f"node-{len(merged_nodes)}"
                )
                existing = merged_nodes.get(name)
                if not existing:
                    merged_nodes[name] = node_data
                    continue
                # Merge devices from chunks
                existing_devices = _extract_devices(existing)
                new_devices = _extract_devices(node_data)
                combined = {d.get("Name") or id(d): d for d in existing_devices}
                for device in new_devices:
                    combined[device.get("Name") or id(device)] = device
                _set_devices(existing, list(combined.values()))

        return ok_result(
            {
                "total_devices_found": total,
                "state_info": last_state,
                "nodes": list(merged_nodes.values()),
            }
        )


def _extract_devices(node: dict[str, Any]) -> list[dict[str, Any]]:
    devices = node.get("CmDevices") or {}
    if isinstance(devices, dict):
        items = devices.get("item") or devices.get("CmDevice") or []
    else:
        items = devices
    if items is None:
        return []
    if not isinstance(items, list):
        return [items]
    return [d for d in items if isinstance(d, dict)]


def _set_devices(node: dict[str, Any], devices: list[dict[str, Any]]) -> None:
    if "CmDevices" not in node or not isinstance(node["CmDevices"], dict):
        node["CmDevices"] = {}
    node["CmDevices"]["item"] = devices


_ris_client: Optional[RisClient] = None


def get_ris_client() -> RisClient:
    global _ris_client
    if _ris_client is None:
        _ris_client = RisClient()
    return _ris_client
