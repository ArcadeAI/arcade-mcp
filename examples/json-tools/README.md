# JSON Tools Example

This directory demonstrates using Arcade JSON tool definitions with a simple local API.

## Contents
- `HelloWorld.json`: A tool definition that calls a local HTTP endpoint.
- `app.py`: A small Flask server that implements the endpoint used by the tool.

## Run the demo API server
```bash
pip install -r toolkits/sample_api/demo_server/requirements.txt
python examples/json-tools/app.py
```
The server will run at `http://localhost:9123`.

## Load JSON tools into Arcade
Use the unified loader on `ToolCatalog`:
```python
from arcade_core import ToolCatalog

catalog = ToolCatalog()
# Loads all .json files from this directory (recursively by default)
catalog.from_directory("examples/json-tools", toolkit_or_name="SampleApi")

# Now you can find and invoke the tool by its name
mt = catalog.get_tool_by_name("SampleApi.HelloWorld")
```

## Invoke the tool (example)
With the server running and the tool loaded, invoke through your normal runner. Conceptually, the inputs map to HTTP:
- `salutation` -> URL path param `{salute}`
- `name` -> request JSON body `{"sample_name": "..."}`
- Secret `sample_api_key` -> `Authorization: Basic {sample_api_key}` header

The tool definition sets `Content-Type: application/json` so the request body is sent as JSON.

## Notes
- You can store JSON tool definitions anywhere; this path is just a convenient example.
- `from_json` is available if you prefer to pass JSON strings directly instead of scanning a directory.