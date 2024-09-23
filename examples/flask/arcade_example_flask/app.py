from flask import Flask, jsonify, request
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from arcade_math.tools import arithmetic

from arcade.actor.flask.actor import FlaskActor

client = OpenAI(base_url="http://localhost:9099")

app = Flask(__name__)

actor = FlaskActor(app)
actor.register_tool(arithmetic.add)
actor.register_tool(arithmetic.multiply)
actor.register_tool(arithmetic.divide)
actor.register_tool(arithmetic.sqrt)


class ChatRequest(BaseModel):
    message: str


@app.route("/")
def hello_world():
    return "Hello, World!"


@app.route("/chat", methods=["POST"])
def chat():
    try:
        # Parse JSON request body
        req_data = request.get_json()
        request_obj = ChatRequest(**req_data)

        raw_response = client.chat.completions.with_raw_response.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": request_obj.message},
            ],
            model="gpt-4o-mini",
            max_tokens=150,
            tools=["add", "subtract", "multiply", "divide", "sqrt"],
            tool_choice="execute",
        )
        chat_completion = raw_response.parse()

        return jsonify(
            {
                "response": chat_completion.choices[0].message.content.strip(),
                "tool_call_count": raw_response.headers["arcade-tool-calls"],
                "tool_call_duration_ms": raw_response.headers[
                    "arcade-total-tool-duration"
                ],
            }
        )

    except ValidationError as e:
        return jsonify({"error": e.errors()}), 422
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
