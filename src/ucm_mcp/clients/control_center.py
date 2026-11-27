"""Control Center Services client (start/stop/activate services)."""

from __future__ import annotations

import logging
from typing import Any, Optional

from zeep.exceptions import Fault

from ucm_mcp.clients.session import soap_service
from ucm_mcp.serialize import error_result, ok_result, to_jsonable
from ucm_mcp.settings import Settings, get_settings

logger = logging.getLogger(__name__)

CC_BINDING = "{http://schemas.cisco.com/ast/soap}ControlCenterServicesBinding"
TOMCAT = "Cisco Tomcat"


class ControlCenterClient:
    """One Control Center SOAP binding, typically per CUCM node."""

    def __init__(
        self,
        node: str,
        settings: Optional[Settings] = None,
    ) -> None:
        self.node = node
        self.settings = settings or get_settings()
        self._service = None

    def _endpoint(self) -> str:
        port = self.settings.ucm_port
        return f"https://{self.node}:{port}/controlcenterservice2/services/ControlCenterServices"

    def connect(self):
        if self._service is not None:
            return self._service
        self.settings.require_connection()
        wsdl = f"{self._endpoint()}?wsdl"
        self._service = soap_service(
            self.settings,
            wsdl,
            CC_BINDING,
            self._endpoint(),
        )
        return self._service

    def list_products(self) -> dict[str, Any]:
        service = self.connect()
        try:
            resp = service.getProductInformationList("")
            products = getattr(getattr(resp, "Products", None), "item", None) or []
            return ok_result(to_jsonable(products), node=self.node)
        except Fault as fault:
            return error_result(fault.message or str(fault), node=self.node)
        except Exception as exc:  # noqa: BLE001
            logger.exception("list_products failed on %s", self.node)
            return error_result(str(exc), node=self.node)

    def list_services(self) -> dict[str, Any]:
        service = self.connect()
        try:
            resp = service.soapGetStaticServiceList("")
            items = getattr(resp, "item", resp)
            return ok_result(to_jsonable(items), node=self.node)
        except Fault as fault:
            return error_result(fault.message or str(fault), node=self.node)
        except Exception as exc:  # noqa: BLE001
            logger.exception("list_services failed on %s", self.node)
            return error_result(str(exc), node=self.node)

    def status(self, service: str = "") -> dict[str, Any]:
        svc = self.connect()
        try:
            resp = svc.soapGetServiceStatus(service or "")
            items = getattr(getattr(resp, "ServiceInfoList", None), "item", None) or []
            return ok_result(to_jsonable(items), node=self.node)
        except Fault as fault:
            return error_result(fault.message or str(fault), node=self.node)
        except Exception as exc:  # noqa: BLE001
            logger.exception("service status failed on %s", self.node)
            return error_result(str(exc), node=self.node)

    def control(self, action: str, service: str) -> dict[str, Any]:
        """start | stop | restart | activate | deactivate a service."""
        if not self.settings.ucm_allow_service_control:
            return error_result(
                "service_control requires UCM_ALLOW_SERVICE_CONTROL=true",
                node=self.node,
            )
        action_l = action.lower().strip()
        if service == TOMCAT:
            return error_result(
                "Cisco Tomcat cannot be controlled via Control Center SOAP. "
                "OS-admin SSH restart is intentionally not supported by this MCP server.",
                node=self.node,
                service=service,
            )

        svc = self.connect()
        try:
            if action_l in {"start", "stop", "restart"}:
                control_type = {"start": "Start", "stop": "Stop", "restart": "Restart"}[
                    action_l
                ]
                req = {
                    "NodeName": self.node,
                    "ControlType": control_type,
                    "ServiceList": {"item": [service]},
                }
                resp = svc.soapDoControlServices(req)
                return ok_result(to_jsonable(resp), node=self.node, action=action_l)
            if action_l in {"activate", "deactivate"}:
                deploy = "Deploy" if action_l == "activate" else "UnDeploy"
                req = {
                    "NodeName": self.node,
                    "DeployType": deploy,
                    "ServiceList": {"item": [service]},
                }
                resp = svc.soapDoServiceDeployment(req)
                return ok_result(to_jsonable(resp), node=self.node, action=action_l)
            return error_result(
                f"Unknown action '{action}'. Use start, stop, restart, activate, or deactivate.",
                node=self.node,
            )
        except Fault as fault:
            return error_result(fault.message or str(fault), node=self.node)
        except Exception as exc:  # noqa: BLE001
            logger.exception("service_control failed on %s", self.node)
            return error_result(str(exc), node=self.node)


def client_for_node(node: str, settings: Optional[Settings] = None) -> ControlCenterClient:
    return ControlCenterClient(node=node, settings=settings)
