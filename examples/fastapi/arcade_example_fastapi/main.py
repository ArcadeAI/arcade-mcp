import os

import arcade_math
from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel

from arcade.actor.fastapi.actor import FastAPIActor
from arcade.sdk import Toolkit

client = AsyncOpenAI(api_key=os.environ["ARCADE_API_KEY"], base_url="http://localhost:9099/v1")

app = FastAPI()

actor_secret = os.environ.get("ARCADE_ACTOR_SECRET")
actor = FastAPIActor(app, secret=actor_secret)
actor.register_toolkit(Toolkit.from_module(arcade_math))


class ChatRequest(BaseModel):
    message: str
    user_id: str


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
                # "Google.GetEmails",
                # "Google.SearchEmailsByHeader",
                # "Google.WriteDraft",
                # "GitHub.CountStargazers",
                # "GitHub.SetStarred",
                # "GitHub.SearchIssues",
                # "Slack.SendDmToUser",
                # "Slack.SendMessageToChannel",
            ],
            tool_choice=tool_choice,
            user=request.user_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    else:
        return raw_response.choices
