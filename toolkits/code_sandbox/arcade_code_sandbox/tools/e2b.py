import base64
import os
from typing import Annotated, Any, Optional

from e2b_code_interpreter import Sandbox

from arcade.sdk import tool


def get_secret(name: str, default: Optional[Any] = None) -> Any:
    secret = os.getenv(name)
    if secret is None:
        if default is not None:
            return default
        raise ValueError(f"Secret {name} is not set.")
    return secret


@tool
def run_code(
    code: Annotated[str, "The code to run"],
    language: Annotated[str, "The language of the code"] = "python",
) -> Annotated[str, "The text representation of the executed code's output"]:
    """
    Run code in a sandbox and return the output.
    """
    api_key = get_secret("E2B_API_KEY")
    sbx = Sandbox(api_key=api_key)  # By default the sandbox is alive for 5 minutes
    execution = sbx.run_code(code=code, language=language)  # Execute Python inside the sandbox
    sbx.kill()

    return str(execution)


@tool
def create_static_matplotlib_charts(
    code: Annotated[str, "The code to run"],
    language: Annotated[str, "The language of the code"] = "python",
) -> Annotated[str, "The text representation of the executed code's output"]:
    """
    Run the provided code to generate static matplotlib chart(s). The resulting charts are converted to images, encoded in base64 format, and then decoded into a string for return.
    """
    api_key = get_secret("E2B_API_KEY")
    sbx = Sandbox(api_key=api_key)  # By default the sandbox is alive for 5 minutes
    execution = sbx.run_code(code=code, language=language)  # Execute Python inside the sandbox
    # There's only one result in this case - the plot displayed with `plt.show()`
    first_result = execution.results[0]

    if first_result.png:
        # Save the png to a file. The png is in base64 format.
        with open("chart.png", "wb") as f:
            f.write(base64.b64decode(first_result.png))
        print("Chart saved as chart.png")

    return "Successfully created static matplotlib chart(s) and saved as chart.png"
