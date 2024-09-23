from arcade_google.tools import gmail
from arcade_slack.tools import chat
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from arcade.actor.fastapi.actor import FastAPIActor
from arcade.client import AsyncArcade
from arcade.core.config import config

if not config.api or not config.api.key:
    raise ValueError("Arcade API key not set. Please run `arcade login`.")

client = AsyncArcade(api_key=config.api.key)

app = FastAPI()

actor = FastAPIActor(app)
# actor.register_tool(arithmetic.add)
# actor.register_tool(arithmetic.multiply)
# actor.register_tool(arithmetic.divide)
# actor.register_tool(arithmetic.sqrt)
actor.register_tool(gmail.list_emails)
actor.register_tool(gmail.list_emails_by_header)
actor.register_tool(gmail.write_draft_email)
actor.register_tool(chat.send_dm_to_user)
actor.register_tool(chat.send_message_to_channel)


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
async def postChat(request: ChatRequest, tool_choice: str = "execute"):
    try:
        raw_response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": request.message},
            ],
            model="gpt-4o-mini",
            max_tokens=500,
            tools=[
                "GetEmails",
                "SearchEmailsByHeader",
                "WriteDraft",
                "SendDmToUser",
                "SendMessageToChannel",
            ],
            tool_choice=tool_choice,
            user=config.user.email if config.user else None,
        )
        return raw_response.choices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
