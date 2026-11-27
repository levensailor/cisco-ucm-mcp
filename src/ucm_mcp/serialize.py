"""Convert zeep / SOAP objects into JSON-safe structures."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from zeep.helpers import serialize_object

SECRET_KEYS = frozenset(
    {
        "password",
        "pin",
        "secret",
        "token",
        "authorization",
        "auth",
        "digest",
        "credentials",
        "passphrase",
    }
)


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SECRET_KEYS)


def to_jsonable(value: Any, *, _depth: int = 0) -> Any:
    """Recursively convert a value into JSON-serializable Python types."""
    if _depth > 40:
        return str(value)

    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.hex()

    if isinstance(value, dict):
        return {
            str(k): ("***" if _is_secret_key(str(k)) else to_jsonable(v, _depth=_depth + 1))
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item, _depth=_depth + 1) for item in value]

    # zeep compound types
    try:
        serialized = serialize_object(value, target_cls=dict)
        if serialized is not value:
            return to_jsonable(serialized, _depth=_depth + 1)
    except Exception:
        pass

    if hasattr(value, "__dict__"):
        public = {
            k: v
            for k, v in vars(value).items()
            if not k.startswith("_")
        }
        if public:
            return to_jsonable(public, _depth=_depth + 1)

    return str(value)


def ok_result(data: Any = None, **extra: Any) -> dict[str, Any]:
    """Standard success envelope."""
    payload: dict[str, Any] = {"ok": True}
    if data is not None:
        payload["data"] = to_jsonable(data)
    payload.update({k: to_jsonable(v) for k, v in extra.items()})
    return payload


def error_result(message: str, **extra: Any) -> dict[str, Any]:
    """Standard error envelope."""
    payload: dict[str, Any] = {"ok": False, "error": message}
    payload.update({k: to_jsonable(v) for k, v in extra.items()})
    return payload
