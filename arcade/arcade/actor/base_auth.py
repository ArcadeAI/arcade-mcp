from dataclasses import dataclass

TOKEN_VER = "1"  # noqa: S105 Possible hardcoded password assigned (false positive)


@dataclass
class TokenValidationResult:
    valid: bool
    api_key: str | None = None
    error: str | None = None
