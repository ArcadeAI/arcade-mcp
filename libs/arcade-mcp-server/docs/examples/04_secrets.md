# 04 - Tool Secrets

Read secrets from environment and `.env` files securely via Context.

## Running the Example

- **Run**: `uv run 04_secrets.py`
- **Run (stdio)**: `uv run 04_secrets.py stdio`
- **Create `.env`**: Add `API_KEY=supersecret` to a `.env` file

## Source Code

```python
--8<-- "docs/examples/04_secrets.py"
```

## Working with Secrets

### 1. Environment Variables

Secrets can be provided via environment variables:
```bash
export API_KEY="your-secret-key"
export DATABASE_URL="postgresql://localhost/mydb"
```

### 2. Using .env Files

Create a `.env` file in the directoryof your server:
```
API_KEY=supersecret
DATABASE_URL=postgresql://user:pass@localhost/db
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

### 3. Declaring Required Secrets

Use the `requires_secrets` parameter to declare which secrets your tool needs:
```python
@tool(requires_secrets=["API_KEY", "DATABASE_URL"])
def my_secure_tool(context: Context) -> str:
    api_key = context.get_secret("API_KEY")
    db_url = context.get_secret("DATABASE_URL")
```

### 4. Security Best Practices

- **Never log secret values**: Always mask or truncate when displaying
- **Declare requirements**: Use `requires_secrets` to document dependencies
- **Handle missing secrets**: Use try/except when accessing secrets
- **Use descriptive names**: Make it clear what each secret is for

## Key Concepts

- **Secure Access**: Secrets are accessed through context, not imported directly
- **Environment Integration**: Works with both environment variables and .env files
- **Error Handling**: Always handle the case where a secret might be missing
- **Masking**: Never expose full secret values in logs or return values
- **Declaration**: Use `requires_secrets` to make dependencies explicit
