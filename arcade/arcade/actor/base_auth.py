from dataclasses import dataclass

TOKEN_VER = "1"


@dataclass
class TokenValidationResult:
    valid: bool
    api_key: str | None = None
    error: str | None = None
