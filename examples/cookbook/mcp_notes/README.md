# Note-Taking MCP Tools

Local note-taking tools designed specifically for MCP (Model Context Protocol) integration. Perfect for AI assistants that need to maintain notes during conversations.

## Features

- **Create Notes**: Support for markdown, text, and JSON formats
- **Search Notes**: Full-text search with tag and date filtering
- **List & Read**: Browse and read notes with metadata
- **Configurable Storage**: Set custom notes directory via context

## Setup

```bash
pip install arcade-ai
```

## Running as MCP Server

### Via stdio (for Claude Desktop, etc.):
```bash
arcade serve --local
```

### Via Server-Sent Events:
```bash
arcade serve --sse --no-auth
```

### Via HTTPS streaming:
```bash
arcade serve --stream --no-auth
```

## Configuration

The `worker.toml` sets default metadata including the notes directory:

```toml
[worker.config.local_context.metadata]
notes_dir = "./notes"
default_format = "markdown"
```

## Usage Examples

### Create a note:
```json
{
  "tool": "CreateNote",
  "arguments": {
    "title": "Meeting Notes",
    "content": "Discussed project timeline...",
    "tags": ["meeting", "project-x"],
    "format": "markdown"
  }
}
```

### Search notes:
```json
{
  "tool": "SearchNotes",
  "arguments": {
    "query": "project timeline",
    "tags": ["meeting"],
    "date_from": "2024-01-01"
  }
}
```

### List recent notes:
```json
{
  "tool": "ListNotes",
  "arguments": {
    "sort_by": "modified",
    "limit": 10
  }
}
```

## MCP Client Configuration

For Claude Desktop, add to your config:

```json
{
  "mcpServers": {
    "notetaker": {
      "command": "arcade",
      "args": ["serve", "--local", "-f", "path/to/worker.toml"]
    }
  }
}
```

## Notes Storage

Notes are stored in the `./notes` directory by default. Each note is saved with:
- Timestamp prefix for uniqueness
- Safe filename based on title
- Appropriate extension (.md, .txt, .json)

The tools automatically create the notes directory if it doesn't exist.
