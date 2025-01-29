"""
Example script demonstrating how to build a simple chatbot with Arcade.

For this example, we are using the prebuilt Google Docs toolkit to create and edit documents.

Try asking questions like:
- "Create a document with the title 'My New Document' and content 'Hello, World!'"
- "List my 2 most recently modified documents and tell me the title, document id, and document URL of each one and summarize them."
- "Edit the second document from the list you just returned and add the text 'Hello, World!' to the end of it."
"""

import os

from openai import OpenAI


def chat(openai_client: OpenAI, tool_names: list[str], user_id: str) -> None:
    history = []

    print("Hello! How can I help you today?")
    while True:
        message = {"role": "user", "content": input(">")}
        history.append(message)
        chat_result = call_tool_with_openai(openai_client, tool_names, user_id, history)

        # If the tool call requires authorization, then wait for the user to authorize and then call the tool again
        if (
            chat_result.choices[0].tool_authorizations
            and chat_result.choices[0].tool_authorizations[0].get("status") == "pending"
        ):
            print("\n" + chat_result.choices[0].message.content)
            input("\nAfter you have authorized, press Enter to continue...")
            chat_result = call_tool_with_openai(openai_client, tool_names, user_id, history)

        history.append({"role": "assistant", "content": chat_result.choices[0].message.content})

        print(chat_result.choices[0].message.content)


def call_tool_with_openai(
    client: OpenAI, tool_names: list[str], user_id: str, messages: list[dict]
) -> dict:
    response = client.chat.completions.create(
        messages=messages,
        model="gpt-4o-mini",
        user=user_id,
        tools=tool_names,
        tool_choice="generate",
    )

    return response


if __name__ == "__main__":
    arcade_api_key = os.environ.get(
        "ARCADE_API_KEY"
    )  # If you forget your Arcade API key, it is stored at ~/.arcade/credentials.yaml on `arcade login`
    cloud_host = "https://api.arcade.dev/v1"
    user_id = "user@example.com"

    openai_client = OpenAI(
        api_key=arcade_api_key,
        base_url=cloud_host,
    )

    tool_names = [
        "Google.SendEmail",
        "Google.SendDraftEmail",
        "Google.WriteDraftEmail",
        "Google.UpdateDraftEmail",
        "Google.ListDraftEmails",
        "Google.ListEmailsByHeader",
        "Google.ListEmails",
    ]

    chat(openai_client, tool_names, user_id)
