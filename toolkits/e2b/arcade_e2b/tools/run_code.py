from typing import Annotated

from arcade_tdk import ToolContext, tool
from e2b_code_interpreter import Sandbox

from arcade_e2b.enums import E2BSupportedLanguage

# See https://e2b.dev/docs to learn more about E2B


@tool(requires_secrets=["E2B_API_KEY"])
def run_code(
    context: ToolContext,
    code: Annotated[str, "The code to run"],
    language: Annotated[
        E2BSupportedLanguage, "The language of the code"
    ] = E2BSupportedLanguage.PYTHON,
) -> Annotated[str, "The sandbox execution as a JSON string"]:
    """
    Run code in a sandbox and return the output.
    """
    api_key = context.get_secret("E2B_API_KEY")

    with Sandbox(api_key=api_key) as sbx:
        execution = sbx.run_code(code=code, language=language)

    return str(execution.to_json())
