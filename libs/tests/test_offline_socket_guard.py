"""Exercise offline guards against Windows socketpair behavior on every OS."""

import asyncio
import socket

import pytest


def _tcp_socketpair():
    """Emulate the Windows stdlib socketpair used by asyncio's self-pipe."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client.connect(listener.getsockname())
            server, _ = listener.accept()
        except BaseException:
            client.close()
            raise
    return server, client


def test_asyncio_works_with_windows_style_socketpair(monkeypatch, request):
    monkeypatch.setattr(socket, "socketpair", _tcp_socketpair)
    blocked = request.getfixturevalue("offline_socket_guard")
    assert asyncio.run(asyncio.sleep(0, result="finished")) == "finished"
    blocked.assert_not_called()


@pytest.mark.parametrize("address", [("127.0.0.1", 443), ("provider.invalid", 443)])
def test_direct_connections_remain_blocked(offline_socket_guard, address):
    with socket.socket() as client, pytest.raises(AssertionError, match="Unexpected network"):
        client.connect(address)
    offline_socket_guard.assert_called_once_with(address)
    offline_socket_guard.reset_mock()


def test_socketpair_failure_restores_connection_guard(monkeypatch, request):
    def failed_socketpair():
        raise OSError("synthetic socketpair failure")

    monkeypatch.setattr(socket, "socketpair", failed_socketpair)
    blocked = request.getfixturevalue("offline_socket_guard")
    with pytest.raises(OSError, match="synthetic socketpair failure"):
        socket.socketpair()
    with socket.socket() as client, pytest.raises(AssertionError, match="Unexpected network"):
        client.connect(("127.0.0.1", 443))
    blocked.assert_called_once_with(("127.0.0.1", 443))
    blocked.reset_mock()
