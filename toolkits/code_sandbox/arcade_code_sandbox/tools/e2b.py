from typing import Annotated

from e2b_code_interpreter import Sandbox

from arcade.sdk import tool
from arcade_code_sandbox.tools.models import E2BSupportedLanguage
from arcade_code_sandbox.tools.utils import get_secret


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


@tool
def create_static_matplotlib_chart(
    code: Annotated[str, "The Python code to run"],
) -> Annotated[list[str], "The base64 encoded image"]:
    """
    Run the provided Python code to generate a static matplotlib chart. The resulting chart is is returned as a base64 encoded image.
    """
    api_key = get_secret("E2B_API_KEY")

    with Sandbox(api_key=api_key) as sbx:
        execution = sbx.run_code(code=code)

    base64_images = []
    for result in execution.results:
        if result.png:
            base64_images.append(result.png)

    return base64_images
