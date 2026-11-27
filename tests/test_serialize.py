"""Serialization helpers."""

from datetime import datetime
from decimal import Decimal

from ucm_mcp.serialize import ok_result, to_jsonable


def test_to_jsonable_primitives_and_secrets():
    payload = {
        "name": "SEPABC",
        "password": "secret",
        "when": datetime(2026, 1, 2, 3, 4, 5),
        "qty": Decimal("1.5"),
        "tags": ("a", "b"),
    }
    out = to_jsonable(payload)
    assert out["name"] == "SEPABC"
    assert out["password"] == "***"
    assert out["when"].startswith("2026-01-02")
    assert out["qty"] == 1.5
    assert out["tags"] == ["a", "b"]


def test_ok_result_envelope():
    result = ok_result({"x": 1}, operation="get_phone")
    assert result["ok"] is True
    assert result["data"] == {"x": 1}
    assert result["operation"] == "get_phone"
