"""Cisco IP Phone CGI Execute (XSI) client."""

from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from typing import Any, Optional
from urllib.parse import quote

import requests
from requests.auth import HTTPBasicAuth

from ucm_mcp.serialize import error_result, ok_result
from ucm_mcp.settings import Settings, get_settings

logger = logging.getLogger(__name__)

KEY_MAP = {
    "0": "KeyPad0",
    "1": "KeyPad1",
    "2": "KeyPad2",
    "3": "KeyPad3",
    "4": "KeyPad4",
    "5": "KeyPad5",
    "6": "KeyPad6",
    "7": "KeyPad7",
    "8": "KeyPad8",
    "9": "KeyPad9",
    "*": "KeyPadStar",
    "#": "KeyPadPound",
    "star": "KeyPadStar",
    "pound": "KeyPadPound",
    "soft1": "Soft1",
    "soft2": "Soft2",
    "soft3": "Soft3",
    "soft4": "Soft4",
    "soft5": "Soft5",
    "up": "NavUp",
    "down": "NavDwn",
    "left": "NavLeft",
    "right": "NavRight",
    "select": "NavSelect",
    "enter": "NavSelect",
    "settings": "Settings",
    "applications": "Applications",
    "services": "Services",
    "directories": "Directories",
    "messages": "Messages",
    "info": "Info",
    "hold": "Hold",
    "speaker": "Speaker",
    "headset": "Headset",
    "mute": "Mute",
    "release": "Release",
}


def build_execute_payload(uris: list[str]) -> str:
    """Build application/x-www-form-urlencoded CiscoIPPhoneExecute body."""
    root = ET.Element("CiscoIPPhoneExecute")
    for uri in uris:
        item = ET.SubElement(root, "ExecuteItem")
        item.set("URL", uri)
    xml = ET.tostring(root, encoding="unicode")
    return f"XML={quote(xml, safe='')}"


class PhoneXsiClient:
    """POST CiscoIPPhoneExecute commands to a phone's CGI/Execute endpoint."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def _assert_allowed(self) -> Optional[dict[str, Any]]:
        if not self.settings.ucm_allow_phone_execute:
            return error_result(
                "Phone Execute requires UCM_ALLOW_PHONE_EXECUTE=true"
            )
        if not self.settings.phone_username or not self.settings.phone_password:
            return error_result(
                "PHONE_USERNAME and PHONE_PASSWORD are required for Phone Execute"
            )
        return None

    def execute(self, phone_ip: str, uris: list[str]) -> dict[str, Any]:
        denied = self._assert_allowed()
        if denied:
            return denied
        if not phone_ip:
            return error_result("phone_ip is required")
        if not uris:
            return error_result("At least one XSI URI is required")
        for uri in uris:
            if not (
                uri.startswith("Key:")
                or uri.startswith("Dial:")
                or uri.startswith("Init:")
                or uri.startswith("Display:")
            ):
                return error_result(
                    f"Unsupported XSI URI '{uri}'. Allowed prefixes: Key:, Dial:, Init:, Display:"
                )

        payload = build_execute_payload(uris)
        url = f"http://{phone_ip}/CGI/Execute"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        logger.info("Phone Execute ip=%s uris=%s", phone_ip, uris)
        try:
            response = requests.post(
                url,
                data=payload,
                headers=headers,
                auth=HTTPBasicAuth(
                    self.settings.phone_username, self.settings.phone_password
                ),
                timeout=self.settings.ucm_request_timeout,
            )
        except requests.RequestException as exc:
            return error_result(str(exc), phone_ip=phone_ip)

        text = response.text or ""
        if response.status_code >= 400:
            return error_result(
                f"HTTP {response.status_code}",
                phone_ip=phone_ip,
                body=text[:500],
            )
        success = "Success" in text or response.status_code == 200
        return ok_result(
            {"response": text, "success": success},
            phone_ip=phone_ip,
            uris=uris,
        )

    def press(self, phone_ip: str, key: str) -> dict[str, Any]:
        """Press a named key or digit on the phone."""
        normalized = key.strip().lower()
        if normalized.startswith("s") and len(normalized) == 2 and normalized[1].isdigit():
            soft = f"soft{normalized[1]}"
            mapped = KEY_MAP.get(soft)
        else:
            mapped = KEY_MAP.get(normalized) or KEY_MAP.get(key.strip())
        if not mapped:
            return error_result(
                f"Unknown key '{key}'. Examples: 0-9, *, #, soft1, up, down, settings, applications"
            )
        return self.execute(phone_ip, [f"Key:{mapped}"])

    def reset_itl(self, phone_ip: str, model: str) -> dict[str, Any]:
        """Run model-specific ITL wipe key sequences."""
        denied = self._assert_allowed()
        if denied:
            return denied
        model_l = (model or "").lower()
        sequence: list[str] = []

        if "88" in model_l:
            # Applications -> 5 -> 4 -> 2 -> Soft3
            sequence = [
                "Key:Applications",
                "Key:KeyPad5",
                "Key:KeyPad4",
                "Key:KeyPad2",
                "Key:Soft3",
            ]
        elif "797" in model_l:
            sequence = [
                "Key:Settings",
                "Key:KeyPad4",
                "Key:KeyPad5",
                "Key:KeyPad2",
                "Key:Soft5",
            ]
        elif "796" in model_l or "794" in model_l:
            sequence = [
                "Key:Settings",
                "Key:KeyPad4",
                "Key:KeyPad5",
                "Key:KeyPad2",
                "Key:KeyPadStar",
                "Key:KeyPadStar",
                "Key:KeyPadPound",
                "Key:Soft2",
                "Key:Soft4",
                "Key:Soft2",
            ]
        else:
            return error_result(
                f"No ITL reset macro for model '{model}'. Supported: 794x/796x, 797x, 88xx."
            )

        results = []
        for uri in sequence:
            result = self.execute(phone_ip, [uri])
            results.append(result)
            if not result.get("ok"):
                return error_result(
                    "ITL reset sequence failed mid-run",
                    phone_ip=phone_ip,
                    model=model,
                    steps=results,
                )
            time.sleep(0.4)
        return ok_result(
            {"steps": results, "model": model, "phone_ip": phone_ip},
        )


_xsi_client: Optional[PhoneXsiClient] = None


def get_phone_xsi_client() -> PhoneXsiClient:
    global _xsi_client
    if _xsi_client is None:
        _xsi_client = PhoneXsiClient()
    return _xsi_client
