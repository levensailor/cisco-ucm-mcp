"""Phone XSI payload encoding and gates."""

from unittest.mock import MagicMock, patch
from urllib.parse import unquote

from ucm_mcp.clients.phone_xsi import PhoneXsiClient, build_execute_payload
from ucm_mcp.settings import Settings


def test_build_execute_payload_encodes_xml():
    payload = build_execute_payload(["Key:KeyPad1", "Key:Soft1"])
    assert payload.startswith("XML=")
    decoded = unquote(payload[4:])
    assert "CiscoIPPhoneExecute" in decoded
    assert 'URL="Key:KeyPad1"' in decoded
    assert 'URL="Key:Soft1"' in decoded


def test_phone_execute_requires_gate():
    client = PhoneXsiClient(
        Settings(
            ucm_host="x",
            ucm_username="u",
            ucm_password="p",
            ucm_allow_phone_execute=False,
            phone_username="cti",
            phone_password="cti",
        )
    )
    result = client.press("10.0.0.1", "1")
    assert result["ok"] is False
    assert "UCM_ALLOW_PHONE_EXECUTE" in result["error"]


def test_phone_press_posts_payload():
    settings = Settings(
        ucm_host="x",
        ucm_username="u",
        ucm_password="p",
        ucm_allow_phone_execute=True,
        phone_username="cti",
        phone_password="cti",
    )
    client = PhoneXsiClient(settings)
    response = MagicMock(status_code=200, text="<CiscoIPPhoneResponse><ResponseItem Status=\"0\" Data=\"Success\"/></CiscoIPPhoneResponse>")
    with patch("ucm_mcp.clients.phone_xsi.requests.post", return_value=response) as post:
        result = client.press("10.0.0.5", "5")
    assert result["ok"] is True
    args, kwargs = post.call_args
    url = kwargs.get("url") or (args[0] if args else None)
    assert url == "http://10.0.0.5/CGI/Execute"
    body = kwargs["data"]
    assert "KeyPad5" in unquote(body[4:] if body.startswith("XML=") else body)
