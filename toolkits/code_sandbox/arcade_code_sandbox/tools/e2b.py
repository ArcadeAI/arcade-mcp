from typing import Annotated

from e2b_code_interpreter import Sandbox

from arcade.sdk import tool
from arcade_code_sandbox.tools.models import E2BSupportedLanguage
from arcade_code_sandbox.tools.utils import get_secret

# See https://e2b.dev/docs to learn more about E2B


@tool
def run_code(
    code: Annotated[str, "The code to run"],
    language: Annotated[
        E2BSupportedLanguage, "The language of the code"
    ] = E2BSupportedLanguage.PYTHON,
) -> Annotated[str, "The sandbox execution as a JSON string"]:
    """
    Run code in a sandbox and return the output.
    """
    api_key = get_secret("E2B_API_KEY")

    with Sandbox(api_key=api_key) as sbx:
        execution = sbx.run_code(code=code, language=language)

    return execution.to_json()


# Note: Not recommended to use tool_choice='generate' with this tool since it contains base64 encoded image.
@tool
def create_static_matplotlib_chart(
    code: Annotated[str, "The Python code to run"],
) -> Annotated[dict, "A dictionary with the following keys: base64_image, logs, error"]:
    """
    Run the provided Python code to generate a static matplotlib chart. The resulting chart is returned as a base64 encoded image.
    """
    api_key = get_secret("E2B_API_KEY")

    with Sandbox(api_key=api_key) as sbx:
        execution = sbx.run_code(code=code)

    result = {
        "base64_image": execution.results[0].png if execution.results else None,
        "logs": execution.logs.to_json(),
        "error": execution.error.to_json() if execution.error else None,
    }

    return result
