import os

from arcade_slack.custom_types import PositiveInt

MAX_PAGINATION_SIZE_LIMIT = 200

MAX_PAGINATION_TIMEOUT_SECONDS = PositiveInt(
    os.environ.get(
        "MAX_PAGINATION_TIMEOUT_SECONDS",
        os.environ.get("MAX_SLACK_PAGINATION_TIMEOUT_SECONDS", 30),
    ),
    name="MAX_PAGINATION_TIMEOUT_SECONDS or MAX_SLACK_PAGINATION_TIMEOUT_SECONDS",
)
