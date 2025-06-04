import json

from arcadepy import Arcade
from arcadepy.tool_errors import ThirdPartyApiRateLimitError

USER_ID = "user@example.com"
TOOL_NAME = "Slack.SendDmToUser"

client = Arcade(base_url="http://localhost:9099")

auth_response = client.tools.authorize(
    tool_name=TOOL_NAME,
    user_id=USER_ID,
)

if auth_response.status != "completed":
    print(f"Click this link to authorize: {auth_response.url}")

client.auth.wait_for_completion(auth_response)

response = client.tools.execute(
    tool_name=TOOL_NAME,
    user_id=USER_ID,
    input={
        "user_name": "renato",
        "message": "Hello, world!",
    },
)

print(response.tool_error)
# dict[str, Any]: {"error_message": "Too Many Requests", "can_retry": True, "retry_after_ms": 30000, ...}

try:
    response.raise_for_tool_status()
except ThirdPartyApiRateLimitError as exc:
    print(exc.error_message)
    # str: Too Many Requests

    print(exc.can_retry)
    # bool: True

    print(exc.retry_after_ms)
    # int: 30000

    print(exc.http_response.status)
    # HttpStatus: HttpStatus(code=429, name="TOO_MANY_REQUESTS", title="Too Many Requests")

    print(exc.http_response.headers)
    # dict[str, str]: {"Retry-After": "30"}
else:
    print(json.dumps(response.output.value, indent=2))
