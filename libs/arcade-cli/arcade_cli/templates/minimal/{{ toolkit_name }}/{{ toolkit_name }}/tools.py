from typing import Annotated

from arcade_tdk import ToolContext, tool


@tool
def say_hello(name: Annotated[str, "The name of the person to greet"]) -> str:
    """Say a greeting!"""
    return f"Hello, {name}!"


@tool(requires_secrets=["MY_SECRET_KEY"])
def whisper_secret(context: ToolContext) -> str:
    """Reveal the last 4 characters of a secret"""
    # Secrets are injected into the tool context at runtime.
    # This means that LLMs and MCP clients cannot see or access your secrets
    # You can define secrets in a .env file.
    secret = context.get_secret("MY_SECRET_KEY")
    return "The last 4 characters of the secret are: " + secret[-4:]
