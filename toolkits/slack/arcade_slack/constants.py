import os


class PositiveInt(int):
    def __new__(cls, value, name="value"):
        def validate(val):
            if val <= 0:
                raise ValueError(f"{name} must be positive, got {val}")
            return val

        try:
            instance = super().__new__(cls, value)
        except ValueError as e:
            if str(e).startswith(name):
                raise
            raise ValueError(f"{name} must be a valid integer, got {value!r}")

        return validate(instance)


MAX_PAGINATION_SIZE_LIMIT = 200

MAX_PAGINATION_TIMEOUT_SECONDS = PositiveInt(
    os.environ.get(
        "MAX_PAGINATION_TIMEOUT_SECONDS",
        os.environ.get("MAX_SLACK_PAGINATION_TIMEOUT_SECONDS", 30),
    ),
    name="MAX_PAGINATION_TIMEOUT_SECONDS or MAX_SLACK_PAGINATION_TIMEOUT_SECONDS",
)
