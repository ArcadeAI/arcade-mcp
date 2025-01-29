"""
This example shows how to call a tool that requires authorization with an LLM using the OpenAI Python client.
"""

import os

from openai import OpenAI


def call_tool_with_openai(client: OpenAI) -> dict:
    response = client.chat.completions.create(
        messages=[
            {"role": "user", "content": "Star the ArcadeAI/arcade-ai repository."},
        ],
        model="gpt-4o-mini",  # TODO: Try "claude-3-5-sonnet-20240620" or other models from our supported model providers. Checkout out our docs for a full list https://docs.arcade.dev
        user="you@example.com",
        tools=["Github.SetStarred"],
        tool_choice="generate",  # TODO: Try "execute" and note any differences
    )

    return response


if __name__ == "__main__":
    arcade_api_key = os.environ.get(
        "ARCADE_API_KEY"
    )  # If you forget your Arcade API key, it is stored at ~/.arcade/credentials.yaml on `arcade login`
    cloud_host = "https://api.arcade.dev" + "/v1"

    openai_client = OpenAI(
        api_key=arcade_api_key,
        base_url=cloud_host,  # Alternatively, use http://localhost:9099/v1 if you are running Arcade Engine locally
    )

    chat_result = call_tool_with_openai(openai_client)
    # If the tool call requires authorization, then wait for the user to authorize and then call the tool again
    if (
        chat_result.choices[0].tool_authorizations
        and chat_result.choices[0].tool_authorizations[0].get("status") == "pending"
    ):
        print(chat_result.choices[0].message.content)
        input("After you have authorized, press Enter to continue...")
        chat_result = call_tool_with_openai(openai_client)

    print(chat_result.choices[0].message.content)
