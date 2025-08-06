"""
Local Note-Taking Tools - Designed for MCP integration
"""

import json
import os
from datetime import datetime
from pathlib import Path

from arcade_sdk import tool
from arcade_sdk.context import ToolContext


@tool
async def create_note(
    title: str,
    content: str,
    tags: list[str] = None,
    format: str = "markdown",
    ctx: ToolContext = None,
) -> dict[str, any]:
    """
    Create a new note in the local filesystem.

    Args:
        title: Note title
        content: Note content
        tags: Optional list of tags
        format: Note format (markdown, text, json)
        ctx: Tool context

    Returns:
        Created note information
    """
    # Get notes directory from context or use default
    notes_dir = "./notes"
    if ctx and ctx.metadata:
        for item in ctx.metadata:
            if item.key == "notes_dir":
                notes_dir = item.value
                break

    # Create directory if it doesn't exist
    Path(notes_dir).mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).rstrip()
    safe_title = safe_title.replace(" ", "_")[:50]

    extension = {"markdown": ".md", "text": ".txt", "json": ".json"}.get(format, ".md")

    filename = f"{timestamp}_{safe_title}{extension}"
    filepath = Path(notes_dir) / filename

    # Prepare note data
    note_data = {
        "title": title,
        "content": content,
        "tags": tags or [],
        "created": datetime.now().isoformat(),
        "author": ctx.user_id if ctx else "anonymous",
    }

    # Write note based on format
    if format == "json":
        with open(filepath, "w") as f:
            json.dump(note_data, f, indent=2)
    else:
        with open(filepath, "w") as f:
            if format == "markdown":
                f.write(f"# {title}\n\n")
                f.write(f"*Created: {note_data['created']}*\n")
                if tags:
                    f.write(f"*Tags: {', '.join(tags)}*\n")
                f.write(f"\n{content}\n")
            else:
                f.write(f"{title}\n{'=' * len(title)}\n\n")
                f.write(f"Created: {note_data['created']}\n")
                if tags:
                    f.write(f"Tags: {', '.join(tags)}\n")
                f.write(f"\n{content}\n")

    return {
        "filename": filename,
        "path": str(filepath),
        "title": title,
        "tags": tags or [],
        "format": format,
        "size": os.path.getsize(filepath),
    }


@tool
async def search_notes(
    query: str = None,
    tags: list[str] = None,
    date_from: str = None,
    date_to: str = None,
    ctx: ToolContext = None,
) -> list[dict[str, any]]:
    """
    Search through notes with various filters.

    Args:
        query: Text to search for in title or content
        tags: Tags to filter by
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        ctx: Tool context

    Returns:
        List of matching notes
    """
    notes_dir = "./notes"
    if ctx and ctx.metadata:
        for item in ctx.metadata:
            if item.key == "notes_dir":
                notes_dir = item.value
                break

    notes_path = Path(notes_dir)
    if not notes_path.exists():
        return []

    results = []

    for file in notes_path.iterdir():
        if not file.is_file():
            continue

        # Check date filter
        file_stat = file.stat()
        file_date = datetime.fromtimestamp(file_stat.st_ctime).date()

        if date_from:
            from_date = datetime.fromisoformat(date_from).date()
            if file_date < from_date:
                continue

        if date_to:
            to_date = datetime.fromisoformat(date_to).date()
            if file_date > to_date:
                continue

        # Read file content
        try:
            content = file.read_text()

            # Check query
            if query:
                if query.lower() not in content.lower() and query.lower() not in file.name.lower():
                    continue

            # Check tags (simple search in content)
            if tags:
                content_lower = content.lower()
                if not any(tag.lower() in content_lower for tag in tags):
                    continue

            # Extract title from content
            title = file.stem
            if file.suffix == ".md" and content.startswith("# "):
                title = content.split("\n")[0][2:]
            elif file.suffix == ".json":
                try:
                    data = json.loads(content)
                    title = data.get("title", file.stem)
                except:
                    pass

            results.append({
                "filename": file.name,
                "title": title,
                "path": str(file),
                "size": file_stat.st_size,
                "created": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                "preview": content[:200] + "..." if len(content) > 200 else content,
            })

        except Exception as e:
            continue

    # Sort by modified date, newest first
    results.sort(key=lambda x: x["modified"], reverse=True)

    return results


@tool
async def read_note(filename: str, ctx: ToolContext = None) -> dict[str, any]:
    """
    Read the full content of a note.

    Args:
        filename: Name of the note file
        ctx: Tool context

    Returns:
        Note content and metadata
    """
    notes_dir = "./notes"
    if ctx and ctx.metadata:
        for item in ctx.metadata:
            if item.key == "notes_dir":
                notes_dir = item.value
                break

    filepath = Path(notes_dir) / filename

    if not filepath.exists():
        return {"error": f"Note '{filename}' not found"}

    try:
        content = filepath.read_text()
        stat = filepath.stat()

        # Try to parse as JSON if it's a JSON file
        if filepath.suffix == ".json":
            try:
                data = json.loads(content)
                return {
                    "filename": filename,
                    "format": "json",
                    "data": data,
                    "raw_content": content,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            except:
                pass

        return {
            "filename": filename,
            "format": filepath.suffix[1:] if filepath.suffix else "text",
            "content": content,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    except Exception as e:
        return {"error": f"Failed to read note: {str(e)}"}


@tool
async def list_notes(
    sort_by: str = "modified", limit: int = 20, ctx: ToolContext = None
) -> list[dict[str, any]]:
    """
    List all notes with basic metadata.

    Args:
        sort_by: Sort field (modified, created, name, size)
        limit: Maximum number of notes to return
        ctx: Tool context

    Returns:
        List of notes with metadata
    """
    notes_dir = "./notes"
    if ctx and ctx.metadata:
        for item in ctx.metadata:
            if item.key == "notes_dir":
                notes_dir = item.value
                break

    notes_path = Path(notes_dir)
    if not notes_path.exists():
        return []

    notes = []

    for file in notes_path.iterdir():
        if not file.is_file():
            continue

        stat = file.stat()
        notes.append({
            "filename": file.name,
            "path": str(file),
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": file.suffix,
        })

    # Sort
    if sort_by == "created":
        notes.sort(key=lambda x: x["created"], reverse=True)
    elif sort_by == "name":
        notes.sort(key=lambda x: x["filename"])
    elif sort_by == "size":
        notes.sort(key=lambda x: x["size"], reverse=True)
    else:  # default to modified
        notes.sort(key=lambda x: x["modified"], reverse=True)

    return notes[:limit]
