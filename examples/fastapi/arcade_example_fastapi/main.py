from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel

from arcade_arithmetic.tools import arithmetic
from arcade_gmail.tools import gmail
from arcade_github.tools import public_repo, user

from arcade.actor.fastapi.actor import FastAPIActor

client = AsyncOpenAI(base_url="http://localhost:9099/v1")

app = FastAPI()

actor = FastAPIActor(app)
actor.register_tool(arithmetic.add)
actor.register_tool(arithmetic.multiply)
actor.register_tool(arithmetic.divide)
actor.register_tool(arithmetic.sqrt)
actor.register_tool(gmail.get_emails)
actor.register_tool(public_repo.count_stargazers)
actor.register_tool(user.set_starred)


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
async def chat(request: ChatRequest, tool_choice: str = "execute"):
    try:
        raw_response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": request.message},
            ],
            model="gpt-4o-mini",
            max_tokens=150,
            # TODO tests for tool choice
            tools=[
                "Add",
                "Multiply",
                "Divide",
                "Sqrt",
                "GetEmails",
                "CountStargazers",
                "SetStarred",
            ],
            tool_choice=tool_choice,
            user="sam",
        )
        return raw_response.choices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
