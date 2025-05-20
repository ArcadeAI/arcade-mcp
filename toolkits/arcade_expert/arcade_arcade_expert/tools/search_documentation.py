from typing import Annotated

import httpx
from arcade.sdk import ToolContext, tool
from markdownify import markdownify
from openai import OpenAI
from openai.types.chat import ParsedChatCompletion

from arcade_arcade_expert.models import Links


@tool(requires_secrets=["OPENAI_API_KEY"])
async def search_documentation(
    context: ToolContext,
    query: Annotated[str, "The query to use to search for relevant Arcade.dev documentation"],
) -> Annotated[str, "The answer to the query"]:
    """Search Arcade.dev's documentation for the content of pages that are relevant to the query.

    Arcade.dev securely connects your AI to APIs, data, code, and other systems.

    Arcade is an AI Tool-calling Platform. For the first time, AI can securely act on behalf
    of users through Arcade's authenticated integrations, or "tools" in AI lingo. Connect AI
    to email, files, calendars, and APIs to build assistants that don't just chat - they get
    work done. Start building in minutes with our pre-built connectors or custom SDK.
    """
    openai_api_key = context.get_secret("OPENAI_API_KEY")
    openai_client = OpenAI(api_key=openai_api_key)

    # Get Arcade.dev documentation's llms.txt file
    url = "https://docs.arcade.dev/llms.txt"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = markdownify(response.text)

    # Get relevant links from the llms.txt file
    chat_response: ParsedChatCompletion = openai_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Provided a query, you are an expert at selecting the most relevant URLs "
                    "from a list of URLs. You return at most 5 URLs."
                ),
            },
            {"role": "user", "content": f"Question: {query}\n\nCandidate Links: {data}"},
        ],
        response_format=Links,
    )
    links = chat_response.choices[0].message.parsed

    if not links:
        return "No relevant documentation found."

    # Get the content of the relevant links
    documentation_content: list[str] = []
    async with httpx.AsyncClient() as client:
        sources = []
        for link in links.links:
            response = await client.get(link)
            if 200 <= response.status_code < 300:
                documentation_content.append(markdownify(response.text))
                sources.append(link)

    sources_str = "\n".join(sources)
    return "\n\n".join(documentation_content) + f"\n\nSources: {sources_str}"
