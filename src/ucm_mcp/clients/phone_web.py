"""Scrape Cisco IP Phone web device/network/status pages."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth

from ucm_mcp.serialize import error_result, ok_result
from ucm_mcp.settings import Settings, get_settings

logger = logging.getLogger(__name__)

FIELD_PATTERNS: list[tuple[str, str]] = [
    ("sn", r"(Serial number_|Serial Number_)([^_]*)"),
    ("firmware", r"(Version_)([^_]*)"),
    ("dn", r"(Phone DN_)([^_]*)"),
    ("model", r"(Model number_|Model Number_)([^_]*)"),
    ("kem1", r"(Key expansion module 1_|Key Expansion Module 1_)([^_]*)"),
    ("kem2", r"(Key expansion module 2_|Key Expansion Module 2_)([^_]*)"),
    ("mac_address", r"(MAC address_|MAC Address_)([^_]*)"),
    ("hostname", r"(Host name_|Host Name_)([^_]*)"),
    ("domain_name", r"(Domain name_|Domain Name_)([^_]*)"),
    ("dhcp_server", r"(DHCP server_|DHCP Server_)([^_]*)"),
    ("dhcp", r"(DHCP_)([^_]*)"),
    ("ip_address", r"(IP address_|IP Address_)([^_]*)"),
    ("subnetmask", r"(Subnet mask_|Subnet Mask_)([^_]*)"),
    ("gateway", r"(Default router_|Default Router 1_)([^_]*)"),
    ("dns1", r"(DNS server 1_|DNS Server 1_)([^_]*)"),
    ("dns2", r"(DNS server 2_|DNS Server 2_)([^_]*)"),
    ("alt_tftp", r"(Alternate TFTP_)([^_]*)"),
    ("tftp1", r"(TFTP server 1_|TFTP Server 1_)([^_]*)"),
    ("tftp2", r"(TFTP server 2_)([^_]*)"),
    ("op_vlan", r"(Operational VLAN ID_|Operational VLAN Id_)([^_]*)"),
    ("admin_vlan", r"(Admin VLAN ID_|Admin VLAN Id_)([^_]*)"),
    ("cucm1", r"(CUCM server1_|Unified CM 1_)([^_]*)"),
    ("cucm2", r"(CUCM server2_|Unified CM 2_)([^_]*)"),
    ("cucm3", r"(CUCM server3_|Unified CM 3_)([^_]*)"),
    ("info_url", r"(Information URL_)([^_]*)"),
    ("dir_url", r"(Directories URL_)([^_]*)"),
    ("msg_url", r"(Messages URL_)([^_]*)"),
    ("svc_url", r"(Services URL_)([^_]*)"),
    ("idle_url", r"(Idle URL_)([^_]*)"),
    ("info_url_time", r"(Idle URL time_)([^_]*)"),
    ("proxy_url", r"(Proxy Server URL_|Proxy server URL)([^_]*)"),
    ("auth_url", r"(Authentication URL_)([^_]*)"),
    ("tvs", r"(TVS_)([^_]*)"),
]


def _urls_for_model(phone_ip: str, model: str) -> dict[str, str]:
    if model.endswith("0"):
        return {
            "config": f"http://{phone_ip}/NetworkConfiguration",
            "device": f"http://{phone_ip}/DeviceInformation",
            "status": f"http://{phone_ip}/DeviceLog?2",
        }
    return {
        "config": f"http://{phone_ip}/CGI/Java/Serviceability?adapter=device.statistics.configuration",
        "device": f"http://{phone_ip}/CGI/Java/Serviceability?adapter=device.statistics.device",
        "status": f"http://{phone_ip}/CGI/Java/Serviceability?adapter=device.settings.status.messages",
    }


class PhoneWebClient:
    """Fetch and parse phone serviceability HTML pages."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def _auth(self) -> Optional[HTTPBasicAuth]:
        if self.settings.phone_username and self.settings.phone_password:
            return HTTPBasicAuth(
                self.settings.phone_username, self.settings.phone_password
            )
        return None

    def _get_text(self, url: str) -> tuple[Optional[str], Optional[str]]:
        try:
            response = requests.get(
                url,
                auth=self._auth(),
                timeout=self.settings.ucm_request_timeout,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, features="lxml")
            return soup.get_text("_"), None
        except requests.RequestException as exc:
            return None, str(exc)

    def all_details(self, phone_ip: str, model: str = "") -> dict[str, Any]:
        if not phone_ip:
            return error_result("phone_ip is required")

        urls = _urls_for_model(phone_ip, model)
        page_errors: dict[str, str] = {}
        texts: dict[str, str] = {}
        for name, url in urls.items():
            text, err = self._get_text(url)
            if err:
                page_errors[name] = err
            else:
                texts[name] = text or ""

        if not texts:
            return error_result(
                "Failed to fetch any phone web pages",
                phone_ip=phone_ip,
                page_errors=page_errors,
            )

        combined = "_".join(texts.values())
        details: dict[str, Any] = {}
        for field, pattern in FIELD_PATTERNS:
            match = re.search(pattern, combined)
            if match:
                details[field] = match.group(2).strip()

        status_text = texts.get("status", "")
        statuses = re.findall(
            r"(..:..:...m ../.*/..)(\n)([^_]*)",
            status_text,
        )
        if not statuses:
            statuses = re.findall(
                r"(\d{1,2}:\d{2}:\d{2}\s*[ap]m\s+\d{1,2}/\d{1,2}/\d{2,4})[_ ]+([^_]*)",
                status_text,
                flags=re.IGNORECASE,
            )
            details["status"] = [
                f"{stamp} {message}".strip() for stamp, message in statuses[-3:]
            ]
        else:
            details["status"] = [
                f"{stamp} {message}".strip() for stamp, _, message in statuses[-3:]
            ]

        return ok_result(
            details,
            phone_ip=phone_ip,
            page_errors=page_errors or None,
        )


_web_client: Optional[PhoneWebClient] = None


def get_phone_web_client() -> PhoneWebClient:
    global _web_client
    if _web_client is None:
        _web_client = PhoneWebClient()
    return _web_client
