"""Perfmon Service client — open, add, collect, close in one call."""

from __future__ import annotations

import logging
from typing import Any, Optional

from zeep.exceptions import Fault

from ucm_mcp.clients.session import soap_service
from ucm_mcp.serialize import error_result, ok_result, to_jsonable
from ucm_mcp.settings import Settings, get_settings

logger = logging.getLogger(__name__)

PERFMON_BINDING = "{http://schemas.cisco.com/ast/soap}PerfmonBinding"


class PerfmonClient:
    """Sample CUCM performance counters without leaking a long-lived session."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._service = None

    def _endpoint(self) -> str:
        host = self.settings.ucm_host
        port = self.settings.ucm_port
        return f"https://{host}:{port}/perfmonservice2/services/PerfmonService"

    def connect(self):
        if self._service is not None:
            return self._service
        self.settings.require_connection()
        wsdl = f"{self._endpoint()}?wsdl"
        self._service = soap_service(
            self.settings,
            wsdl,
            PERFMON_BINDING,
            self._endpoint(),
        )
        return self._service

    def sample(
        self,
        counters: list[str],
        *,
        host: str = "",
    ) -> dict[str, Any]:
        """Open a session, add counters, collect once, and close."""
        if not counters:
            return error_result("At least one counter path is required")
        service = self.connect()
        target_host = host or self.settings.ucm_host
        session_handle = None
        try:
            session_handle = service.perfmonOpenSession()
            for counter in counters:
                try:
                    service.perfmonAddCounter(
                        SessionHandle=session_handle,
                        ArrayOfCounter=[{"Counter": counter}],
                    )
                except TypeError:
                    # Some WSDL layouts nest differently
                    service.perfmonAddCounter(session_handle, [{"Counter": counter}])
            try:
                collected = service.perfmonCollectSessionData(
                    SessionHandle=session_handle
                )
            except TypeError:
                collected = service.perfmonCollectSessionData(session_handle)
            return ok_result(
                to_jsonable(collected),
                host=target_host,
                counters=counters,
            )
        except Fault as fault:
            return error_result(fault.message or str(fault), fault=str(fault))
        except Exception as exc:  # noqa: BLE001
            logger.exception("perfmon_sample failed")
            return error_result(str(exc))
        finally:
            if session_handle is not None:
                try:
                    try:
                        service.perfmonCloseSession(SessionHandle=session_handle)
                    except TypeError:
                        service.perfmonCloseSession(session_handle)
                except Exception:  # noqa: BLE001
                    logger.warning("Failed to close perfmon session", exc_info=True)


_perfmon_client: Optional[PerfmonClient] = None


def get_perfmon_client() -> PerfmonClient:
    global _perfmon_client
    if _perfmon_client is None:
        _perfmon_client = PerfmonClient()
    return _perfmon_client
