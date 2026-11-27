"""Wrapper around ciscoaxl for discovery and gated dispatch."""

from __future__ import annotations

import inspect
import logging
from functools import lru_cache
from typing import Any, Optional

from zeep.exceptions import Fault

from ucm_mcp.safety import (
    assert_operation_allowed,
    assert_read_only_sql,
    classify_operation,
    method_signature,
)
from ucm_mcp.serialize import error_result, ok_result, to_jsonable
from ucm_mcp.settings import Settings, get_settings

logger = logging.getLogger(__name__)


@lru_cache
def _axl_class():
    from ciscoaxl import axl

    return axl


class AxlClient:
    """Lazy ciscoaxl.axl connection with discovery helpers."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._client = None

    def connect(self):
        """Return (and cache) a connected axl instance."""
        if self._client is not None:
            return self._client
        self.settings.require_connection()
        cls = _axl_class()
        logger.info(
            "Connecting AXL to %s:%s schema=%s",
            self.settings.ucm_host,
            self.settings.ucm_port,
            self.settings.ucm_version,
        )
        self._client = cls(
            username=self.settings.ucm_username,
            password=self.settings.ucm_password,
            cucm=self.settings.ucm_host,
            cucm_version=self.settings.ucm_version,
            cucm_port=self.settings.ucm_port,
            strict_ssl=self.settings.ucm_verify_ssl,
        )
        return self._client

    def list_operations(
        self,
        *,
        prefix: str = "",
        contains: str = "",
        classification: str = "",
    ) -> list[dict[str, Any]]:
        """List public axl methods, optionally filtered."""
        cls = _axl_class()
        results: list[dict[str, Any]] = []
        for name, member in inspect.getmembers(cls, predicate=inspect.isfunction):
            if name.startswith("_"):
                continue
            kind = classify_operation(name)
            if classification and kind != classification:
                continue
            if prefix and not name.startswith(prefix):
                continue
            if contains and contains.lower() not in name.lower():
                continue
            module = getattr(member, "__module__", "") or ""
            results.append(
                {
                    "name": name,
                    "classification": kind,
                    "module": module.rsplit(".", 1)[-1] if module else "",
                }
            )
        results.sort(key=lambda item: item["name"])
        return results

    def describe_operation(self, name: str) -> dict[str, Any]:
        """Return signature/doc for a public axl method."""
        cls = _axl_class()
        if not hasattr(cls, name) or name.startswith("_"):
            raise AttributeError(f"Unknown AXL operation: {name}")
        func = getattr(cls, name)
        if not callable(func):
            raise AttributeError(f"AXL attribute is not callable: {name}")
        info = method_signature(func)
        info["module"] = (getattr(func, "__module__", "") or "").rsplit(".", 1)[-1]
        return info

    def call(self, name: str, arguments: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Invoke an axl method with JSON arguments under the write gate."""
        try:
            assert_operation_allowed(name, self.settings.ucm_allow_writes)
        except PermissionError as exc:
            return error_result(str(exc), operation=name)

        client = self.connect()
        if not hasattr(client, name) or name.startswith("_"):
            return error_result(f"Unknown AXL operation: {name}")
        method = getattr(client, name)
        if not callable(method):
            return error_result(f"AXL attribute is not callable: {name}")

        args = arguments or {}
        logger.info("AXL call %s keys=%s", name, sorted(args.keys()))
        try:
            result = method(**args)
        except Fault as fault:
            logger.warning("AXL fault on %s: %s", name, fault.message)
            return error_result(
                fault.message or str(fault),
                fault=str(fault),
                operation=name,
            )
        except TypeError as exc:
            return error_result(str(exc), operation=name)
        except Exception as exc:  # noqa: BLE001 - surface to agent
            logger.exception("AXL call failed: %s", name)
            return error_result(str(exc), operation=name)

        return ok_result(result, operation=name)

    def sql_query(self, query: str) -> dict[str, Any]:
        """Run a read-only SQL query via AXL."""
        cleaned = assert_read_only_sql(query)
        client = self.connect()
        logger.info("AXL SQL query length=%d", len(cleaned))
        try:
            if hasattr(client, "run_sql_query"):
                result = client.run_sql_query(cleaned)
            else:
                result = client.sql_query(cleaned)
        except Fault as fault:
            return error_result(fault.message or str(fault), fault=str(fault))
        except Exception as exc:  # noqa: BLE001
            logger.exception("AXL SQL query failed")
            return error_result(str(exc))
        return ok_result(result)

    def sql_update(self, query: str) -> dict[str, Any]:
        """Run a mutating SQL statement when writes are enabled."""
        if not self.settings.ucm_allow_writes:
            return error_result("axl_sql_update requires UCM_ALLOW_WRITES=true")
        cleaned = query.strip().rstrip(";")
        if not cleaned:
            return error_result("SQL statement is empty")
        if ";" in cleaned:
            return error_result("Only a single SQL statement is allowed")
        client = self.connect()
        logger.info("AXL SQL update length=%d", len(cleaned))
        try:
            result = client.sql_update(cleaned)
        except Fault as fault:
            return error_result(fault.message or str(fault), fault=str(fault))
        except Exception as exc:  # noqa: BLE001
            logger.exception("AXL SQL update failed")
            return error_result(str(exc))
        return ok_result(to_jsonable(result))


_axl_client: Optional[AxlClient] = None


def get_axl_client() -> AxlClient:
    """Return the process-wide AxlClient."""
    global _axl_client
    if _axl_client is None:
        _axl_client = AxlClient()
    return _axl_client
