"""Phone web scrape parsing with HTML fixtures."""

from unittest.mock import MagicMock, patch

from ucm_mcp.clients.phone_web import PhoneWebClient
from ucm_mcp.settings import Settings

DEVICE_HTML = """
<html><body>
Serial Number_FCH2053D2BS_
Version_sip88xx.12-0-1-8_
Phone DN_52807_
Model Number_CP-8851_
</body></html>
"""

CONFIG_HTML = """
<html><body>
MAC Address_F8A5C59E0F1C_
Host Name_SEPF8A5C59E0F1C_
IP Address_10.131.202.127_
TFTP Server 1_10.144.200.10_
Unified CM 1_10.144.200.10  Active_
</body></html>
"""

STATUS_HTML = """
<html><body>
11:39:03am 10/09/18
ITL installed_
11:39:04am 10/09/18
SEPF8A5C59E0F1C.cnf.xml.sgn(HTTP)_
11:39:05am 10/09/18
VPN not configured_
</body></html>
"""


def test_phone_details_parses_fields():
    settings = Settings(ucm_host="x", ucm_username="u", ucm_password="p")
    client = PhoneWebClient(settings)

    def fake_get(url, auth=None, timeout=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "device.statistics.device" in url:
            resp.text = DEVICE_HTML
        elif "configuration" in url:
            resp.text = CONFIG_HTML
        else:
            resp.text = STATUS_HTML
        return resp

    with patch("ucm_mcp.clients.phone_web.requests.get", side_effect=fake_get):
        result = client.all_details("10.131.202.127")

    assert result["ok"] is True
    data = result["data"]
    assert data["sn"] == "FCH2053D2BS"
    assert data["firmware"] == "sip88xx.12-0-1-8"
    assert data["dn"] == "52807"
    assert data["model"] == "CP-8851"
    assert data["mac_address"] == "F8A5C59E0F1C"
    assert data["hostname"] == "SEPF8A5C59E0F1C"
    assert data["ip_address"] == "10.131.202.127"
    assert data["tftp1"] == "10.144.200.10"
    assert data["cucm1"] == "10.144.200.10  Active"


def test_phone_details_reports_page_errors():
    import requests

    settings = Settings(ucm_host="x", ucm_username="u", ucm_password="p")
    client = PhoneWebClient(settings)

    with patch(
        "ucm_mcp.clients.phone_web.requests.get",
        side_effect=requests.ConnectionError("down"),
    ):
        result = client.all_details("10.0.0.1")
    assert result["ok"] is False
    assert "page_errors" in result
