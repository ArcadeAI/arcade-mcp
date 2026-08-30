import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit, urlunsplit


class LocalDestinationError(ValueError):
    """The forwarding destination is not an explicit loopback URL."""


@dataclass(frozen=True)
class ResolvedLocalTarget:
    connect_url: str
    host_header: str


def resolve_local_target(url: str) -> ResolvedLocalTarget:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise LocalDestinationError("forwarding URL is invalid") from exc

    host = parsed.hostname
    if (
        parsed.scheme != "http"
        or host is None
        or port is None
        or not 1 <= port <= 65535
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise LocalDestinationError(
            "forwarding URL must be HTTP, include an explicit port, and have no credentials"
        )

    normalized_host = host.lower()
    if normalized_host == "localhost":
        address = _resolve_localhost(port)
    elif normalized_host in {"127.0.0.1", "::1"}:
        address = normalized_host
    else:
        raise LocalDestinationError("forwarding URL must use localhost, 127.0.0.1, or [::1]")

    connect_host = f"[{address}]" if ":" in address else address
    original_host = f"[{normalized_host}]" if ":" in normalized_host else normalized_host
    connect_url = urlunsplit(
        SplitResult("http", f"{connect_host}:{port}", parsed.path, parsed.query, "")
    )
    return ResolvedLocalTarget(connect_url=connect_url, host_header=f"{original_host}:{port}")


def _resolve_localhost(port: int) -> str:
    try:
        addresses = {
            str(info[4][0])
            for info in socket.getaddrinfo("localhost", port, type=socket.SOCK_STREAM)
        }
    except OSError as exc:
        raise LocalDestinationError("localhost could not be resolved") from exc
    if not addresses or any(not ipaddress.ip_address(address).is_loopback for address in addresses):
        raise LocalDestinationError("localhost resolved to a non-loopback address")
    return sorted(addresses, key=lambda address: (":" in address, address))[0]
