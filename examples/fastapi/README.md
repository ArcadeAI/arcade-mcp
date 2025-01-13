# Arcade FastAPI Example

## How to run the example

1. `poetry install`
2. `export ARCADE_API_KEY=<your-api-key>`
3. `export ARCADE_WORKER_SECRET=<your-worker-secret>` (you can use the secret `dev` for development)
4. `export OPENAI_API_KEY=<your-openai-api-key>`
5. `uvicorn main:app --reload --port 8002`

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
### Get tools
```bash
curl -X GET "http://127.0.0.1:8002/worker/tools"
```

### Chat with tools
```bash
curl -X POST "http://127.0.0.1:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "What is the square root of 16?", "user_id": "user@example.com"}'
```
