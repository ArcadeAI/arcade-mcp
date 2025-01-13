# Arcade FastAPI Example

## How to run the example

1. `pip install poetry==1.8.4 && poetry install`
2. `export ARCADE_API_KEY=<your-api-key>`
3. `export ARCADE_WORKER_SECRET=<your-worker-secret>` (you can use the secret `dev` for development)
4. `export OPENAI_API_KEY=<your-openai-api-key>` (optional, only if you want to test the chat route)
5. `cd arcade_example_fastapi`
6. `uvicorn main:app --host 127.0.0.1 --port 8002 --reload`

## Test the setup
In a separate terminal, run the following command to test the setup.

### Health check
```bash
curl -X GET "http://127.0.0.1:8002/worker/health"
```
*Expected Output:*
```json
{
  "status": "ok",
  "tool_count": 9
}
```

## Test out other routes
### Get tool definitions
```bash
curl -X GET "http://127.0.0.1:8002/worker/tools"
```

### Chat with tools
```bash
curl -X POST "http://127.0.0.1:8002/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "What is the square root of 16?", "user_id": "user@example.com"}'
```
