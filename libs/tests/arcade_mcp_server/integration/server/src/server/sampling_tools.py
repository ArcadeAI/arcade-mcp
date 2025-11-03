from typing import Annotated

from arcade_mcp_server import Context, tool


@tool
async def sampling(
    context: Context, text: Annotated[str, "The text to be summarized by the client's model"]
) -> str:
    """Summarize the text using the client's model."""
    result = await context.sampling.create_message(
        messages=text,
        system_prompt=(
            "You are a helpful assistant that summarizes text. "
            "Given a text, you should summarize it in a few sentences."
        ),
    )
    return result.text
