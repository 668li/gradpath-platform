from unittest.mock import patch

import pytest

from app.core.outbound_security import (
    OutboundURLValidationError,
    validate_public_http_endpoint,
)


def test_rejects_loopback():
    with pytest.raises(OutboundURLValidationError):
        validate_public_http_endpoint("http://127.0.0.1:8000/v1")


def test_rejects_private_network():
    with pytest.raises(OutboundURLValidationError):
        validate_public_http_endpoint("http://10.0.0.8:8000/v1")


def test_rejects_credentials():
    with pytest.raises(OutboundURLValidationError):
        validate_public_http_endpoint("https://user:pass@example.com/v1")


def test_accepts_public_https_host():
    with patch(
        "app.core.outbound_security.socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("203.0.113.10", 443))],
    ):
        assert validate_public_http_endpoint("https://api.example.com/v1") == "https://api.example.com/v1"
