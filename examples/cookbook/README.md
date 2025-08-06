# Arcade Cookbook

A collection of example Arcade tool implementations demonstrating various patterns and use cases.

## Examples

### 🔧 [simple_tool](./simple_tool/)
Basic Arcade tool patterns including parameters, return types, and using ToolContext.

**Key concepts:**
- Simple function tools
- Using ToolContext for user information
- Different return types (strings, numbers, objects)

### 📧 [gmail_curator](./gmail_curator/)
Intelligent Gmail inbox organizer with OAuth authentication.

**Key concepts:**
- OAuth authentication with mock tokens
- Tool authorization requirements
- Working with external APIs

### 📝 [notetaker_local_mcp](./notetaker_local_mcp/)
Note-taking tools designed for MCP (Model Context Protocol) integration.

**Key concepts:**
- MCP-compatible tools
- Local file operations
- Configurable storage paths via context

### 💾 [using_local_resources](./using_local_resources/)
Working with secrets, files, and external resources.

**Key concepts:**
- Secrets management
- File system operations
- API calls with caching
- Environment-based configuration

## Running Examples

Each example includes:
- `worker.toml` - Configuration file
- `toolkit/` - Tool implementations
- `README.md` - Detailed documentation
- `env.example` - Environment variables template (where applicable)

### Quick Start

1. Navigate to an example:
```bash
cd simple_tool
```

2. Install Arcade:
```bash
pip install arcade-ai
```

3. Run the worker:
```bash
# Standard HTTP mode
arcade serve

# MCP stdio mode
arcade serve --local

# MCP SSE mode
arcade serve --sse --no-auth
```

## ToolContext Handling

Arcade ensures that `ToolContext` is properly passed to tools in both local and deployed settings:

### Local Development
When running `arcade serve` locally, the context is populated from:
1. **worker.toml** - The `local_context` section defines default values
2. **Environment variables** - `ARCADE_USER_ID`, `ARCADE_USER_EMAIL` override config
3. **Request data** - Values sent in the API request take highest priority

Example worker.toml:
```toml
[worker.config.local_context]
user_id = "dev-user"

[worker.config.local_context.metadata]
environment = "development"
notes_dir = "./notes"
```

### Deployed (Arcade Cloud)
In production, the Arcade Engine automatically populates ToolContext with:
- User authentication details
- Authorized secrets
- Request metadata

### Using ToolContext in Tools
```python
@tool
async def my_tool(input: str, ctx: ToolContext = None) -> str:
    # Access user ID
    user_id = ctx.user_id if ctx else "anonymous"

    # Access secrets
    api_key = ctx.get_secret("API_KEY") if ctx else None

    # Access metadata
    env = ctx.get_metadata("environment") if ctx else "unknown"

    return f"Hello {user_id} from {env}!"
```

The context parameter is automatically injected by Arcade - you don't need to pass it explicitly when calling tools.

## Common Patterns

### Using Secrets
```python
@tool(requires_secrets=["API_KEY"])
async def my_tool(ctx: ToolContext):
    api_key = ctx.get_secret("API_KEY")
```

### OAuth Authentication
```python
@tool(requires_auth=Google(scopes=["gmail.readonly"]))
async def gmail_tool(ctx: ToolContext):
    token = ctx.get_auth_token_or_empty()
```

### Local Development
Configure mock auth providers in `worker.toml`:
```toml
[[worker.config.local_auth_providers]]
provider_id = "google"
mock_tokens = { "test-user" = "mock-token" }
```

## Contributing

Feel free to add more examples! Each example should:
1. Demonstrate a specific use case or pattern
2. Include clear documentation
3. Be self-contained and runnable
4. Follow Arcade best practices