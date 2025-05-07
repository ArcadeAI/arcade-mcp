from functools import wraps
from typing import Any


def clean_asana_response(func):
    def response_cleaner(data: dict[str, Any]) -> dict[str, Any]:
        if "gid" in data:
            data["id"] = data["gid"]
            del data["gid"]

        for k, v in data.items():
            if isinstance(v, dict):
                data[k] = response_cleaner(v)
            elif isinstance(v, list):
                data[k] = [
                    item if not isinstance(item, dict) else response_cleaner(item) for item in v
                ]

        return data

    @wraps(func)
    async def wrapper(*args, **kwargs):
        response = await func(*args, **kwargs)
        return response_cleaner(response)

    return wrapper
