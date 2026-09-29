"""Tests for the fetch guard that keeps user-submitted URLs off internal hosts."""

import socket

import pytest

from services.asyncapply.utils.web import BlockedUrlError, assert_fetchable


def _resolve_to(monkeypatch, address: str) -> None:
    """Force every hostname lookup to answer with one address."""
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **kw: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 0))],
    )


@pytest.mark.parametrize(
    "address",
    [
        "169.254.169.254",  # cloud metadata -- the one that leaks IAM credentials
        "127.0.0.1",  # loopback
        "10.0.0.5",  # private
        "192.168.1.10",  # private
        "172.16.4.2",  # private
        "0.0.0.0",  # unspecified
    ],
)
def test_non_public_addresses_are_blocked(monkeypatch, address: str) -> None:
    _resolve_to(monkeypatch, address)
    with pytest.raises(BlockedUrlError):
        assert_fetchable("https://careers.example.com/job/1")


def test_a_public_address_is_allowed(monkeypatch) -> None:
    _resolve_to(monkeypatch, "93.184.216.34")
    assert_fetchable("https://careers.example.com/job/1")


def test_a_hostname_that_does_not_resolve_is_blocked(monkeypatch) -> None:
    def _fail(*args, **kwargs):
        raise socket.gaierror("no such host")

    monkeypatch.setattr(socket, "getaddrinfo", _fail)
    with pytest.raises(BlockedUrlError):
        assert_fetchable("https://nope.example.com/job/1")


@pytest.mark.parametrize("url", ["file:///etc/passwd", "gopher://x/1", "ftp://host/f"])
def test_non_http_schemes_are_blocked(url: str) -> None:
    with pytest.raises(BlockedUrlError):
        assert_fetchable(url)


def test_a_url_with_no_host_is_blocked() -> None:
    with pytest.raises(BlockedUrlError):
        assert_fetchable("http://")
