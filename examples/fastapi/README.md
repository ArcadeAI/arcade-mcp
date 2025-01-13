# Arcade FastAPI Example

## How to Run the Example

Follow these steps to set up and run the Arcade FastAPI example:

1. **Install Dependencies**
   ```bash
   pip install poetry==1.8.4 && poetry install
   ```

2. **Set Environment Variables**
   ```bash
   export ARCADE_API_KEY=<your-api-key>
   export ARCADE_WORKER_SECRET=<your-worker-secret> # Use 'dev' for development
   ```

3. **Navigate to the Project Directory**
   ```bash
   cd arcade_example_fastapi
   ```

4. **Run the Worker**
   ```bash
   uvicorn main:app --host 127.0.0.1 --port 8002 --reload
   ```

## Testing the Setup

### 1. Health Check
In a separate terminal, run the following command to test the setup:
```bash
curl -X GET "http://127.0.0.1:8002/worker/health"
```
**Expected Output:**
```json
{
  "status": "ok",
  "tool_count": 9
}
```

### 2. Get Tool Definitions
To retrieve tool definitions, use the following command:
```bash
curl -X GET "http://127.0.0.1:8002/worker/tools"
```

### 3. Chat with Tools
1. **Set OpenAI API Key**
   ```bash
   export OPENAI_API_KEY=<your-openai-api-key> # Only if you want to test the chat route
   ```

2. **Run the Arcade Engine**
   In a separate terminal, execute:
   ```bash
   arcade-engine
   ```

3. **Send a Chat Request**
   Use the following command to send a request to the chat route:
   ```bash
   curl -X POST "http://127.0.0.1:8002/chat" \
       -H "Content-Type: application/json" \
       -d '{"message": "What is the square root of 16?", "user_id": "user@example.com"}'
   ```
