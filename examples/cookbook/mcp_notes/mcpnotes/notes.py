from typing import Annotated

from arcade_tdk import ToolContext, tool

notes = []


@tool(name="get_notes", desc="Get all notes.")
def get_notes(context: ToolContext) -> list[str]:
    """Get all notes."""
    return ["Note 1", "Note 2", "Note 3"]


@tool
def add_note(context: ToolContext, note: Annotated[str, "The note to add."]) -> str:
    """Add a note."""
    print(f"Adding note: {note}")
    return "Added note: " + note


@tool
def delete_note(context: ToolContext, note: Annotated[str, "The note to delete."]) -> str:
    """Delete a note."""
    print(f"Deleting note: {note}")
    return "Deleted note: " + note


@tool
def update_note(
    context: ToolContext,
    note: Annotated[str, "The note to update."],
    new_note: Annotated[str, "The new note."],
) -> str:
    """Update a note."""
    print(f"Updating note: {note} to {new_note}")
    return "Updated note: " + new_note
