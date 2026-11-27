"""Shared HTTP session helpers for CUCM SOAP/HTTPS clients."""

from __future__ import annotations

import logging
from typing import Optional

import urllib3
from requests import Session
from requests.auth import HTTPBasicAuth
from zeep import Client, Settings
from zeep.cache import SqliteCache
from zeep.transports import Transport

from ucm_mcp.settings import Settings as AppSettings

logger = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def build_session(
    username: str,
    password: str,
    *,
    verify_ssl: bool = False,
) -> Session:
    """Create an authenticated requests Session."""
    session = Session()
    session.auth = HTTPBasicAuth(username, password)
    session.verify = verify_ssl
    return session


def build_zeep_client(
    wsdl: str,
    session: Session,
    *,
    timeout: int = 30,
) -> Client:
    """Create a zeep Client bound to the given WSDL and session."""
    settings = Settings(strict=False, xml_huge_tree=True, xsd_ignore_sequence_order=True)
    transport = Transport(session=session, timeout=timeout, cache=SqliteCache())
    return Client(wsdl, settings=settings, transport=transport)


def soap_service(
    app: AppSettings,
    wsdl_url: str,
    binding_name: str,
    address: str,
    session: Optional[Session] = None,
):
    """Return a zeep service proxy for a CUCM SOAP binding."""
    sess = session or build_session(
        app.ucm_username,
        app.ucm_password,
        verify_ssl=app.ucm_verify_ssl,
    )
    client = build_zeep_client(wsdl_url, sess, timeout=app.ucm_request_timeout)
    logger.debug("Bound SOAP service %s -> %s", binding_name, address)
    return client.create_service(binding_name, address)
