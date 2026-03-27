"""Unit tests for arcade_core.network.ssl.get_ssl_verify()."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from arcade_core.network.ssl import get_ssl_verify


class TestGetSslVerify:
    """Tests for get_ssl_verify() env-var resolution."""

    def test_no_env_vars_returns_true(self) -> None:
        """When no CA bundle env vars are set, return True (httpx default)."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_ssl_verify() is True

    def test_ssl_cert_file_returns_path(self) -> None:
        """SSL_CERT_FILE takes highest priority."""
        with patch.dict(
            os.environ, {"SSL_CERT_FILE": "/path/to/cert.pem"}, clear=True
        ):
            assert get_ssl_verify() == "/path/to/cert.pem"

    def test_requests_ca_bundle_returns_path(self) -> None:
        """REQUESTS_CA_BUNDLE is used when SSL_CERT_FILE is unset."""
        with patch.dict(
            os.environ, {"REQUESTS_CA_BUNDLE": "/path/to/bundle.pem"}, clear=True
        ):
            assert get_ssl_verify() == "/path/to/bundle.pem"

    def test_curl_ca_bundle_returns_path(self) -> None:
        """CURL_CA_BUNDLE is used when higher-priority vars are unset."""
        with patch.dict(
            os.environ, {"CURL_CA_BUNDLE": "/path/to/curl-ca.pem"}, clear=True
        ):
            assert get_ssl_verify() == "/path/to/curl-ca.pem"

    def test_priority_ssl_cert_file_over_requests(self) -> None:
        """SSL_CERT_FILE wins over REQUESTS_CA_BUNDLE."""
        with patch.dict(
            os.environ,
            {
                "SSL_CERT_FILE": "/ssl.pem",
                "REQUESTS_CA_BUNDLE": "/requests.pem",
            },
            clear=True,
        ):
            assert get_ssl_verify() == "/ssl.pem"

    def test_priority_ssl_cert_file_over_curl(self) -> None:
        """SSL_CERT_FILE wins over CURL_CA_BUNDLE."""
        with patch.dict(
            os.environ,
            {
                "SSL_CERT_FILE": "/ssl.pem",
                "CURL_CA_BUNDLE": "/curl.pem",
            },
            clear=True,
        ):
            assert get_ssl_verify() == "/ssl.pem"

    def test_priority_requests_over_curl(self) -> None:
        """REQUESTS_CA_BUNDLE wins over CURL_CA_BUNDLE."""
        with patch.dict(
            os.environ,
            {
                "REQUESTS_CA_BUNDLE": "/requests.pem",
                "CURL_CA_BUNDLE": "/curl.pem",
            },
            clear=True,
        ):
            assert get_ssl_verify() == "/requests.pem"

    def test_all_three_set_returns_ssl_cert_file(self) -> None:
        """When all three are set, SSL_CERT_FILE wins."""
        with patch.dict(
            os.environ,
            {
                "SSL_CERT_FILE": "/ssl.pem",
                "REQUESTS_CA_BUNDLE": "/requests.pem",
                "CURL_CA_BUNDLE": "/curl.pem",
            },
            clear=True,
        ):
            assert get_ssl_verify() == "/ssl.pem"

    def test_empty_string_falls_through(self) -> None:
        """Empty strings are treated as unset."""
        with patch.dict(
            os.environ,
            {"SSL_CERT_FILE": "", "REQUESTS_CA_BUNDLE": "/requests.pem"},
            clear=True,
        ):
            assert get_ssl_verify() == "/requests.pem"

    def test_all_empty_strings_returns_true(self) -> None:
        """All empty strings → returns True."""
        with patch.dict(
            os.environ,
            {
                "SSL_CERT_FILE": "",
                "REQUESTS_CA_BUNDLE": "",
                "CURL_CA_BUNDLE": "",
            },
            clear=True,
        ):
            assert get_ssl_verify() is True
