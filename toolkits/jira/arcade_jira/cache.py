CLOUD_ID_BY_AUTH_TOKEN: dict[str, str] = {}


def get_cloud_id(auth_token: str) -> str | None:
    return CLOUD_ID_BY_AUTH_TOKEN.get(auth_token)


def set_cloud_id(auth_token: str, cloud_id: str) -> None:
    CLOUD_ID_BY_AUTH_TOKEN[auth_token] = cloud_id
