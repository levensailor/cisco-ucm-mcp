"""CDR on Demand SOAP client."""

from __future__ import annotations

import logging
from typing import Any, Optional

from zeep.exceptions import Fault

from ucm_mcp.clients.session import soap_service
from ucm_mcp.serialize import error_result, ok_result, to_jsonable
from ucm_mcp.settings import Settings, get_settings

logger = logging.getLogger(__name__)

CDR_BINDING = "{http://schemas.cisco.com/ast/soap}CDRonDemandBinding"


class CdrClient:
    """List and retrieve CDR file metadata / content with size caps."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._service = None

    def _endpoint(self) -> str:
        host = self.settings.ucm_host
        port = self.settings.ucm_port
        return f"https://{host}:{port}/CDRonDemandService2/services/CDRonDemand"

    def connect(self):
        if self._service is not None:
            return self._service
        self.settings.require_connection()
        # CUCM exposes both path casings across versions
        endpoint = self._endpoint()
        wsdl = f"{endpoint}?wsdl"
        try:
            self._service = soap_service(
                self.settings,
                wsdl,
                CDR_BINDING,
                endpoint,
            )
        except Exception:
            alt = f"https://{self.settings.ucm_host}:{self.settings.ucm_port}/cdrservice/services/CDRonDemand"
            self._service = soap_service(
                self.settings,
                f"{alt}?wsdl",
                CDR_BINDING,
                alt,
            )
        return self._service

    def get_file_list(
        self,
        *,
        from_date: str,
        to_date: str,
    ) -> dict[str, Any]:
        """Return CDR/CMR filenames between inclusive datetime strings."""
        if not from_date or not to_date:
            return error_result("from_date and to_date are required (YYYY-MM-DD HH:MM:SS)")
        service = self.connect()
        try:
            if hasattr(service, "get_file_list"):
                resp = service.get_file_list(from_date, to_date, True)
            elif hasattr(service, "getFileList"):
                resp = service.getFileList(from_date, to_date, True)
            else:
                return error_result("CDR get_file_list is not available on this cluster")
            return ok_result(to_jsonable(resp), from_date=from_date, to_date=to_date)
        except Fault as fault:
            return error_result(fault.message or str(fault), fault=str(fault))
        except Exception as exc:  # noqa: BLE001
            logger.exception("cdr get_file_list failed")
            return error_result(str(exc))

    def get_file(self, file_name: str) -> dict[str, Any]:
        if not file_name:
            return error_result("file_name is required")
        service = self.connect()
        max_bytes = self.settings.ucm_download_max_bytes
        try:
            if hasattr(service, "get_file"):
                resp = service.get_file(file_name)
            elif hasattr(service, "getFile"):
                resp = service.getFile(file_name)
            else:
                return error_result("CDR get_file is not available on this cluster")
            content = to_jsonable(resp)
            text = content if isinstance(content, str) else str(content)
            truncated = False
            encoded = text.encode("utf-8", errors="replace")
            if len(encoded) > max_bytes:
                text = encoded[:max_bytes].decode("utf-8", errors="replace")
                truncated = True
            return ok_result(
                {"content": text, "truncated": truncated, "file_name": file_name}
            )
        except Fault as fault:
            return error_result(fault.message or str(fault), fault=str(fault))
        except Exception as exc:  # noqa: BLE001
            logger.exception("cdr get_file failed")
            return error_result(str(exc))


_cdr_client: Optional[CdrClient] = None


def get_cdr_client() -> CdrClient:
    global _cdr_client
    if _cdr_client is None:
        _cdr_client = CdrClient()
    return _cdr_client
