# Gmail Curator Example

An intelligent Gmail inbox organizer that analyzes email patterns and suggests organization strategies.

## Features

- **Inbox Analysis**: Analyze email patterns, top senders, and categories
- **Smart Labels**: Create labels based on email patterns
- **Unsubscribe Helper**: Find subscriptions you might want to unsubscribe from
- **Filter Generator**: Generate Gmail filter rules based on patterns

## Setup

1. Copy the environment file:
```bash
cp env.example .env
```

2. For local development, the mock tokens in `worker.toml` will be used automatically.

3. For production, set up real Google OAuth:
   - Set `ARCADE_API_KEY` in your environment
   - Remove the `local_auth_providers` section from `worker.toml`

## Running

```bash
# Install dependencies
pip install arcade-ai

# Run the worker
arcade serve

# Or run as MCP server
arcade serve --sse --no-auth
```

## Example Usage

```python
# Analyze inbox patterns
analysis = await analyze_inbox(days_back=30)
print(f"Found {analysis['total_emails']} emails")
print(f"Top sender: {analysis['top_senders'][0]}")

# Generate filter rules
rules = await generate_filter_rules(analysis)
for rule in rules:
    print(f"Suggested: {rule['criteria']} -> {rule['action']}")

# Find unsubscribe candidates
candidates = await find_unsubscribe_candidates(min_emails=10)
for candidate in candidates:
    print(f"Consider unsubscribing from {candidate['sender']}")
```

## Notes

- In development mode (with mock tokens), the tools return sample data
- With real Google tokens, full Gmail API functionality is available
- Requires appropriate Gmail API scopes for each operation