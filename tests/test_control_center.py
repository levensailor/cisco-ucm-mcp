"""Control Center client safety and fan-out helpers."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ucm_mcp.clients.control_center import ControlCenterClient
from ucm_mcp.settings import Settings
from ucm_mcp.tools import composites


def test_tomcat_control_refused():
    settings = Settings(
        ucm_host="cucm.example",
        ucm_username="u",
        ucm_password="p",
        ucm_allow_service_control=True,
    )
    client = ControlCenterClient("cucm.example", settings)
    result = client.control("restart", "Cisco Tomcat")
    assert result["ok"] is False
    assert "Tomcat" in result["error"]


def test_service_control_requires_gate():
    settings = Settings(
        ucm_host="cucm.example",
        ucm_username="u",
        ucm_password="p",
        ucm_allow_service_control=False,
    )
    client = ControlCenterClient("cucm.example", settings)
    result = client.control("restart", "Cisco CallManager")
    assert result["ok"] is False
    assert "UCM_ALLOW_SERVICE_CONTROL" in result["error"]


def test_cluster_service_status_skips_enterprise_wide(monkeypatch):
    class FakeAxl:
        def call(self, name, arguments=None):
            assert name == "list_process_nodes"
            return {
                "ok": True,
                "data": [
                    {"name": "EnterpriseWideData"},
                    {"name": "pub.example"},
                    {"name": "sub.example"},
                ],
            }

    class FakeCC:
        def __init__(self, node, settings=None):
            self.node = node

        def status(self, service=""):
            return {"ok": True, "data": [{"ServiceName": service or "Cisco Tomcat"}]}

    monkeypatch.setattr(composites, "get_axl_client", lambda: FakeAxl())
    monkeypatch.setattr(composites, "client_for_node", FakeCC)
    monkeypatch.setattr(
        composites,
        "get_settings",
        lambda: Settings(ucm_host="pub.example", ucm_username="u", ucm_password="p"),
    )

    captured = {}

    class FakeMcp:
        def tool(self):
            def decorator(fn):
                captured[fn.__name__] = fn
                return fn

            return decorator

    composites.register(FakeMcp())
    result = captured["cluster_service_status"](service="Cisco Tomcat")
    assert result["ok"] is True
    assert result["node_count"] == 2
    nodes = {row["node"] for row in result["data"]}
    assert nodes == {"pub.example", "sub.example"}
