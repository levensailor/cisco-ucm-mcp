"""AXL client discovery and write gating without a live CUCM."""

from types import SimpleNamespace

import pytest
from zeep.exceptions import Fault

from ucm_mcp.clients import axl as axl_mod
from ucm_mcp.clients.axl import AxlClient
from ucm_mcp.settings import Settings


def test_list_operations_filters(monkeypatch):
    class FakeAxl:
        def get_phone(self):
            """Get a phone."""

        def add_phone(self):
            """Add a phone."""

        def _private(self):
            pass

    monkeypatch.setattr(axl_mod, "_axl_class", lambda: FakeAxl)
    client = AxlClient(Settings(ucm_host="x", ucm_username="u", ucm_password="p"))
    ops = client.list_operations(contains="phone")
    names = {o["name"] for o in ops}
    assert "get_phone" in names
    assert "add_phone" in names
    assert "_private" not in names
    reads = client.list_operations(classification="read")
    assert all(o["classification"] == "read" for o in reads)


def test_call_blocks_writes_and_maps_faults(monkeypatch):
    class FakeAxl:
        def __init__(self, *args, **kwargs):
            pass

        def get_phone(self, name=""):
            return SimpleNamespace(name=name, description="desk")

        def add_phone(self, **kwargs):
            raise Fault("duplicate")

    monkeypatch.setattr(axl_mod, "_axl_class", lambda: FakeAxl)
    settings = Settings(
        ucm_host="x",
        ucm_username="u",
        ucm_password="p",
        ucm_allow_writes=False,
    )
    client = AxlClient(settings)
    client._client = FakeAxl()

    ok = client.call("get_phone", {"name": "SEPA"})
    assert ok["ok"] is True
    assert ok["data"]["name"] == "SEPA"

    blocked = client.call("add_phone", {"name": "SEPA"})
    assert blocked["ok"] is False
    assert "UCM_ALLOW_WRITES" in blocked["error"]

    settings.ucm_allow_writes = True
    client.settings = settings
    faulted = client.call("add_phone", {"name": "SEPA"})
    assert faulted["ok"] is False
    assert "duplicate" in faulted["error"]


def test_sql_query_guard():
    class FakeAxl:
        def run_sql_query(self, query):
            return {"num_rows": 1, "rows": [{"name": "SEP"}], "query": query}

    settings = Settings(ucm_host="x", ucm_username="u", ucm_password="p")
    client = AxlClient(settings)
    client._client = FakeAxl()
    result = client.sql_query("SELECT name FROM device")
    assert result["ok"] is True
    assert result["data"]["num_rows"] == 1

    with pytest.raises(ValueError):
        client.sql_query("DELETE FROM device")
