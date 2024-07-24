from arcade.actor.fastapi.actor import FastAPIActor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import AsyncOpenAI
from arcade_example_nate.tools import arithmetic


client = AsyncOpenAI(base_url="http://localhost:6901")

app = FastAPI()

actor = FastAPIActor(app)
actor.register_tool(arithmetic.add)
actor.register_tool(arithmetic.multiply)
actor.register_tool(arithmetic.divide)
actor.register_tool(arithmetic.sqrt)


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        raw_response = await client.chat.completions.with_raw_response.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": request.message},
            ],
            model="gpt-4o-mini",
            max_tokens=150,
            tool_choice="execute",
        )
        chat_completion = raw_response.parse()

        return {
            "response": chat_completion.choices[0].message.content.strip(),
            "tool_call_count": raw_response.headers["arcade-tool-calls"],
            "tool_call_duration_ms": raw_response.headers["arcade-total-tool-duration"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
