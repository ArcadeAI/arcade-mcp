"""SSL/TLS certificate verification helpers for httpx clients."""

from __future__ import annotations

import os


def get_ssl_verify() -> str | bool:
    """Return the SSL verification setting for httpx calls.

    Checks standard CA bundle environment variables in priority order:
      1. SSL_CERT_FILE
      2. REQUESTS_CA_BUNDLE
      3. CURL_CA_BUNDLE

    Returns the first non-empty path found, or ``True`` (httpx default)
    if none are set.
    """
    for var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        value = os.environ.get(var, "")
        if value:
            return value
    return True
