from dataclasses import dataclass
from typing import Any


@dataclass
class RequestData:
    path: str
    method: str
    body: Any
