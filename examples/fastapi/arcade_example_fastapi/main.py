import os

import arcade_math
from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel

from arcade.sdk import Toolkit
from arcade.worker.fastapi.worker import FastAPIWorker

client = AsyncOpenAI(api_key=os.environ["ARCADE_API_KEY"], base_url="http://localhost:9099/v1")

app = FastAPI()

worker_secret = os.environ["ARCADE_WORKER_SECRET"]
worker = FastAPIWorker(app, secret=worker_secret)
worker.register_toolkit(Toolkit.from_module(arcade_math))


class ChatRequest(BaseModel):
    message: str
    user_id: str | None = None


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
                "Math.Add",
                "Math.Subtract",
                "Math.Multiply",
                "Math.Divide",
                "Math.Sqrt",
                # Other tools can be added as needed:
                # "Math.SumList"
            ],
            tool_choice=tool_choice,
            user=request.user_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    else:
        return raw_response.choices
