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
    print(execution.logs)

    return execution.text
