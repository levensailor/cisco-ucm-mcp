"""Log Collection Service client."""

from __future__ import annotations

import logging
from typing import Any, Optional

from zeep.exceptions import Fault

from ucm_mcp.clients.session import soap_service
from ucm_mcp.serialize import error_result, ok_result, to_jsonable
from ucm_mcp.settings import Settings, get_settings

logger = logging.getLogger(__name__)

LOG_BINDING = "{http://schemas.cisco.com/ast/soap}LogCollectionPortBinding"


class LogCollectionClient:
    """List and select CUCM log files with a download size cap."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._service = None

    def _endpoint(self) -> str:
        host = self.settings.ucm_host
        port = self.settings.ucm_port
        return f"https://{host}:{port}/logcollectionservice2/services/LogCollectionPort"

    def connect(self):
        if self._service is not None:
            return self._service
        self.settings.require_connection()
        wsdl = f"{self._endpoint()}?wsdl"
        self._service = soap_service(
            self.settings,
            wsdl,
            LOG_BINDING,
            self._endpoint(),
        )
        return self._service

    def list_nodes(self) -> dict[str, Any]:
        service = self.connect()
        try:
            if hasattr(service, "listNodeService"):
                resp = service.listNodeService()
            elif hasattr(service, "GetServiceList"):
                resp = service.GetServiceList()
            else:
                return error_result("Log Collection WSDL has no list method")
            return ok_result(to_jsonable(resp))
        except Fault as fault:
            return error_result(fault.message or str(fault), fault=str(fault))
        except Exception as exc:  # noqa: BLE001
            logger.exception("log list_nodes failed")
            return error_result(str(exc))

    def select_log_files(
        self,
        *,
        service_name: str = "",
        node: str = "",
    ) -> dict[str, Any]:
        service = self.connect()
        try:
            if hasattr(service, "selectLogFiles"):
                resp = service.selectLogFiles(
                    FileSelectionCriteria={
                        "ServiceName": service_name or "",
                        "HostName": node or self.settings.ucm_host,
                    }
                )
            else:
                return error_result("selectLogFiles is not available on this cluster")
            return ok_result(to_jsonable(resp))
        except TypeError:
            try:
                resp = service.selectLogFiles(service_name or "", node or "")
                return ok_result(to_jsonable(resp))
            except Exception as exc:  # noqa: BLE001
                return error_result(str(exc))
        except Fault as fault:
            return error_result(fault.message or str(fault), fault=str(fault))
        except Exception as exc:  # noqa: BLE001
            logger.exception("select_log_files failed")
            return error_result(str(exc))

    def download_file(self, file_name: str) -> dict[str, Any]:
        """Download a log file, truncating at UCM_DOWNLOAD_MAX_BYTES."""
        if not file_name:
            return error_result("file_name is required")
        service = self.connect()
        max_bytes = self.settings.ucm_download_max_bytes
        try:
            if hasattr(service, "GetOneFile"):
                resp = service.GetOneFile(file_name)
            elif hasattr(service, "getOneFile"):
                resp = service.getOneFile(file_name)
            else:
                return error_result("GetOneFile is not available on this cluster")
            content = to_jsonable(resp)
            text = content if isinstance(content, str) else str(content)
            truncated = False
            if isinstance(text, str) and len(text.encode("utf-8", errors="replace")) > max_bytes:
                encoded = text.encode("utf-8", errors="replace")[:max_bytes]
                text = encoded.decode("utf-8", errors="replace")
                truncated = True
            return ok_result(
                {"content": text, "truncated": truncated, "file_name": file_name}
            )
        except Fault as fault:
            return error_result(fault.message or str(fault), fault=str(fault))
        except Exception as exc:  # noqa: BLE001
            logger.exception("download_file failed")
            return error_result(str(exc))


_logs_client: Optional[LogCollectionClient] = None


def get_logs_client() -> LogCollectionClient:
    global _logs_client
    if _logs_client is None:
        _logs_client = LogCollectionClient()
    return _logs_client
