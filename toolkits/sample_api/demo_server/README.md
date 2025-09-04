# Sample API Demo Server

A simple Flask server that implements the HelloWorld endpoint specified in `../sample_api/wrapper_tools/HelloWorld.json`.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python app.py
```

The server will start on `http://localhost:9123`.

## API Endpoints

### POST /hello/{salute}

Greets a user with a custom salutation.

**Parameters:**
- `salute` (path): The salutation to use (e.g., "hello", "hi", "greetings")
- `sample_name` (body): The name to greet

**Headers:**
- `Authorization: Basic {api_key}`: Required authentication header

**Example Request:**
```bash
curl -X POST http://localhost:9123/hello/greetings \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic my-secret-key" \
  -d '{"sample_name": "Alice"}'
```

**Example Response:**
```json
{
  "message": "Greetings, Alice! Welcome to the Sample API."
}
```

### GET /health

Simple health check endpoint.

**Example Request:**
```bash
curl http://localhost:9123/health
```

**Example Response:**
```json
{
  "status": "healthy"
}
```