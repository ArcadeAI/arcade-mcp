from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel

from arcade_gmail.tools import gmail
from arcade_github.tools import repo, user
from arcade_slack.tools import chat

from arcade.actor.fastapi.actor import FastAPIActor

client = AsyncOpenAI(base_url="http://localhost:9099/v1")

app = FastAPI()

actor = FastAPIActor(app)
# actor.register_tool(arithmetic.add)
# actor.register_tool(arithmetic.multiply)
# actor.register_tool(arithmetic.divide)
# actor.register_tool(arithmetic.sqrt)
actor.register_tool(gmail.get_emails)
actor.register_tool(gmail.write_draft)
actor.register_tool(repo.count_stargazers)
actor.register_tool(repo.search_issues)
actor.register_tool(user.set_starred)
actor.register_tool(chat.send_dm_to_user)


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
            # TODO tests for tool choice
            tools=[
                "GetEmails",
                "WriteDraft",
                "CountStargazers",
                "SetStarred",
                "SearchIssues",
                "SendDmToUser",
            ],
            tool_choice=tool_choice,
            user="sam",
        )
        return raw_response.choices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
