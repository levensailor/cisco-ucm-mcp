"""RIS client chunking and merge behavior."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from ucm_mcp.clients.ris import RisClient
from ucm_mcp.settings import Settings


def _device(name: str, status: str = "Registered") -> SimpleNamespace:
    return SimpleNamespace(
        Name=name,
        Status=status,
        LoginUserId="user1",
        TimeStamp=1,
        IPAddress=SimpleNamespace(item=[SimpleNamespace(IP="10.0.0.1")]),
        LinesStatus=None,
    )


def test_ris_chunks_and_merges_nodes():
    settings = Settings(
        ucm_host="cucm.example",
        ucm_username="u",
        ucm_password="p",
        ucm_version="15.0",
    )
    client = RisClient(settings)
    service = MagicMock()

    # First chunk returns device A on node1; second returns device B on same node
    def select(_state, criteria):
        items = criteria["SelectItems"]["item"]
        names = [i["Item"] for i in items]
        devices = [_device(n) for n in names]
        node = SimpleNamespace(
            Name="sub1",
            CmDevices=SimpleNamespace(item=devices),
        )
        result = SimpleNamespace(
            SelectCmDeviceResult=SimpleNamespace(
                TotalDevicesFound=len(devices),
                CmNodes=SimpleNamespace(item=[node]),
            ),
            StateInfo="state-1",
        )
        return result

    service.selectCmDeviceExt.side_effect = select
    client._service = service

    phones = [f"SEP{i:012d}" for i in range(1005)]
    result = client.select_devices(items=phones, select_by="Name")
    assert result["ok"] is True
    assert service.selectCmDeviceExt.call_count == 2
    nodes = result["data"]["nodes"]
    assert len(nodes) == 1
    merged = nodes[0]["CmDevices"]["item"]
    assert len(merged) == 1005


def test_ris_sends_separate_item_elements():
    settings = Settings(
        ucm_host="cucm.example",
        ucm_username="u",
        ucm_password="p",
    )
    client = RisClient(settings)
    service = MagicMock()
    service.selectCmDeviceExt.return_value = SimpleNamespace(
        SelectCmDeviceResult=SimpleNamespace(TotalDevicesFound=0, CmNodes=None),
        StateInfo="",
    )
    client._service = service

    client.select_devices(items=["SEPA", "SEPB"], select_by="Name")
    criteria = service.selectCmDeviceExt.call_args.args[1]
    items = criteria["SelectItems"]["item"]
    assert items == [{"Item": "SEPA"}, {"Item": "SEPB"}]
