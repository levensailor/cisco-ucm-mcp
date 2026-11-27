"""Operation classification and SQL statement guards."""

from __future__ import annotations

import inspect
import re
from typing import Any, Callable

READ_PREFIXES = (
    "get_",
    "list_",
    "run_sql_query",
    "sql_query",
    "sql_query_inactive",
)

WRITE_PREFIXES = (
    "add_",
    "update_",
    "delete_",
    "remove_",
    "apply_",
    "reset_",
    "restart_",
    "do_",
    "assign_",
    "unassign_",
    "lock_",
    "wipe_",
    "sql_update",
)

# Exact names that are read-only even if they look ambiguous
READ_EXACT = frozenset(
    {
        "run_sql_query",
        "sql_query",
        "sql_query_inactive",
        "list_route_plan",
        "list_route_plan_specific",
        "list_process_nodes",
        "list_changes",
    }
)

WRITE_EXACT = frozenset({"sql_update"})

_SQL_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|merge|exec|execute|call|grant|revoke)\b",
    re.IGNORECASE,
)


def classify_operation(name: str) -> str:
    """Return 'read', 'write', or 'unknown' for an AXL method name."""
    if name in READ_EXACT:
        return "read"
    if name in WRITE_EXACT:
        return "write"
    for prefix in READ_PREFIXES:
        if name == prefix or name.startswith(prefix):
            return "read"
    for prefix in WRITE_PREFIXES:
        if name == prefix or name.startswith(prefix):
            return "write"
    return "unknown"


def assert_operation_allowed(name: str, allow_writes: bool) -> None:
    """Raise PermissionError when a write/unknown op runs without the write gate."""
    kind = classify_operation(name)
    if kind == "read":
        return
    if kind == "write" and allow_writes:
        return
    if kind == "unknown" and allow_writes:
        return
    raise PermissionError(
        f"Operation '{name}' is classified as '{kind}' and requires "
        "UCM_ALLOW_WRITES=true"
    )


def assert_read_only_sql(query: str) -> str:
    """Validate a single SELECT/WITH statement; return normalized SQL."""
    cleaned = query.strip().rstrip(";")
    if not cleaned:
        raise ValueError("SQL query is empty")
    if ";" in cleaned:
        raise ValueError("Only a single SQL statement is allowed")
    first = cleaned.split(None, 1)[0].upper()
    if first not in {"SELECT", "WITH"}:
        raise ValueError("Only SELECT or WITH queries are allowed for axl_sql_query")
    if _SQL_FORBIDDEN.search(cleaned):
        # Allow "WITH" / column names that collide; check as whole words after first token
        remainder = cleaned[len(first) :]
        if _SQL_FORBIDDEN.search(remainder):
            raise ValueError(
                "Mutating or DDL keywords are not allowed in axl_sql_query"
            )
    return cleaned


def method_signature(func: Callable[..., Any]) -> dict[str, Any]:
    """Describe a callable for axl_describe_operation."""
    try:
        sig = inspect.signature(func)
        params = []
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            entry: dict[str, Any] = {"name": name, "kind": str(param.kind)}
            if param.default is not inspect.Parameter.empty:
                entry["default"] = repr(param.default)
            if param.annotation is not inspect.Parameter.empty:
                entry["annotation"] = (
                    param.annotation
                    if isinstance(param.annotation, str)
                    else getattr(param.annotation, "__name__", str(param.annotation))
                )
            params.append(entry)
        signature = str(sig)
    except (TypeError, ValueError):
        params = []
        signature = "(...)"

    return {
        "name": getattr(func, "__name__", str(func)),
        "signature": signature,
        "parameters": params,
        "doc": inspect.getdoc(func) or "",
        "classification": classify_operation(getattr(func, "__name__", "")),
    }
