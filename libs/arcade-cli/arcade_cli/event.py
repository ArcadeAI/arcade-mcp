from dataclasses import dataclass


class LocalDestinationError(ValueError):
    """The forwarding destination is not an explicit loopback URL."""


@dataclass(frozen=True)
class ResolvedLocalTarget:
    connect_url: str
    host_header: str


def resolve_local_target(url: str) -> ResolvedLocalTarget:
    raise LocalDestinationError("local forwarding is not implemented")
