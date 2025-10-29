#!/usr/bin/env python3
"""prompts MCP server"""

import sys
from typing import Annotated

from arcade_mcp_server import MCPApp
from arcade_mcp_server.types import PromptArgument, PromptMessage

app = MCPApp(name="prompts", version="1.0.0", log_level="DEBUG")

# # Define a prompt
# greeting_prompt = Prompt(
#     name="greeting",
#     description="A greeting prompt",
#     arguments=[
#         PromptArgument(name="name", description="The name to greet", required=True),
#         PromptArgument(name="formal", description="Use formal greeting", required=False),
#     ],
# )


@app.prompt
def brainstorm(args: dict[str, str]) -> list[PromptMessage]:
    """Start a creative brainstorming session"""
    return [
        PromptMessage(
            role="user",
            content={
                "type": "text",
                "text": "Let's brainstorm creative solutions! Think outside the box and explore unconventional ideas.",
            },
        )
    ]


@app.prompt(
    name="code_review",
    title="Request Code Review",
    description="Asks the LLM to analyze code quality and suggest improvements",
    arguments=[
        PromptArgument(name="code", description="The code to review", required=True),
        PromptArgument(
            name="language",
            description="Programming language (e.g., python, javascript)",
            required=True,
        ),
    ],
)
def review_code(args: dict[str, str]) -> list[PromptMessage]:
    """Generate a code review prompt"""
    code = args.get("code", "")
    language = args.get("language", "unknown")

    return [
        PromptMessage(
            role="user",
            content={
                "type": "text",
                "text": f"Review the code for {language} and suggest improvements: {code}",
            },
        )
    ]


@app.tool
def greet(name: Annotated[str, "The name of the person to greet"]) -> str:
    """Greet a person by name."""
    return f"Hello, {name}!"


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    app.run(transport=transport, host="127.0.0.1", port=8000)
