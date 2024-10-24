from arcade.sdk.errors import ToolExecutionError
from arcade_github.tools.constants import ENDPOINTS, GITHUB_API_BASE_URL


def handle_github_response(response: dict, url: str) -> None:
    """
    Handle GitHub API response and raise appropriate exceptions for non-200 status codes.

    :param response: The response object from the GitHub API
    :param url: The URL of the API endpoint
    :raises ToolExecutionError: If the response status code is not 200
    """
    if 200 <= response.status_code < 300:
        return

    error_messages = {
        301: "Moved permanently. The repository has moved.",
        304: "Not modified. The requested resource hasn't been modified since the last request.",
        403: "Forbidden. You do not have access to this resource.",
        404: "Resource not found. The requested resource does not exist.",
        410: "Gone. The requested resource is no longer available.",
        422: "Validation failed or the endpoint has been spammed.",
        503: "Service unavailable. The server is temporarily unable to handle the request.",
    }

    error_message = error_messages.get(
        response.status_code, f"Failed to process request. Status code: {response.status_code}"
    )

    raise ToolExecutionError(f"Error accessing '{url}': {error_message}")


def get_github_json_headers(token: str) -> dict:
    """
    Generate common headers for GitHub API requests.

    :param token: The authorization token
    :return: A dictionary of headers
    """
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_github_diff_headers(token: str) -> dict:
    """
    Generate headers for GitHub API requests for diff content.

    :param token: The authorization token
    :return: A dictionary of headers
    """
    return {
        "Accept": "application/vnd.github.diff",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def remove_none_values(params: dict) -> dict:
    """
    Remove None values from a dictionary.

    :param params: The dictionary to clean
    :return: A new dictionary with None values removed
    """
    return {k: v for k, v in params.items() if v is not None}


def get_url(endpoint: str, **kwargs) -> str:
    """
    Get the full URL for a given endpoint.

    :param endpoint: The endpoint key from ENDPOINTS
    :param kwargs: The parameters to format the URL with
    :return: The full URL
    """
    return f"{GITHUB_API_BASE_URL}{ENDPOINTS[endpoint].format(**kwargs)}"
