from typing import Annotated

from arcade_tdk import ToolContext, tool
from e2b_code_interpreter import Sandbox

# See https://e2b.dev/docs to learn more about E2B


# Note: Not recommended to use tool_choice='generate' with this tool
#       since it contains base64 encoded image.
@tool(requires_secrets=["E2B_API_KEY"])
def create_static_matplotlib_chart(
    context: ToolContext,
    code: Annotated[str, "The Python code to run"],
) -> Annotated[dict, "A dictionary with the following keys: base64_image, logs, error"]:
    """
    Run the provided Python code to generate a static matplotlib chart.
    The resulting chart is returned as a base64 encoded image.
    """
    api_key = context.get_secret("E2B_API_KEY")

    with Sandbox(api_key=api_key) as sbx:
        execution = sbx.run_code(code=code)

    result = {
        "base64_image": execution.results[0].png if execution.results else None,
        "logs": execution.logs.to_json(),
        "error": execution.error.to_json() if execution.error else None,
    }

    return result
