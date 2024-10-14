import os
from typing import Annotated

from arcade.sdk import tool

from .utils import cat, cp, grep, ls, mv, rm, stat


@tool
def get_text_file_details(
    file_path: Annotated[str, "The path to the file"],
) -> Annotated[dict, "A dictionary containing file details"]:
    """
    Get detailed information about a text file, including its contents and metadata.
    This tool is essentially the terminal command `cat file_path && stat file_path`
    """
    contents = cat(file_path)
    file_stats = stat(file_path)

    file_details = {**file_stats, "contents": contents}

    return file_details


@tool
def search_file(
    file_path: Annotated[str, "The path to the file"],
    pattern: Annotated[str, "The pattern to search for"],
) -> Annotated[list[str], "A list of matching lines"]:
    """
    Search for a pattern in a file and return matching lines.
    This tool is similar to the terminal command `grep pattern file_path`
    """
    return grep(file_path, pattern)


@tool
def list_directory(
    directory: Annotated[str, "The directory path"],
) -> Annotated[list[str], "A list of directory contents"]:
    """
    List directory contents.
    This tool is essentially the terminal command `ls directory`
    """
    return ls(directory)


@tool
def create_file(
    file_path: Annotated[str, "The path to the new file"],
    contents: Annotated[str, "The contents to write to the file"],
) -> Annotated[str, "A message indicating success or failure"]:
    """
    Create a new file with the specified contents if it doesn't already exist.
    This tool is similar to the terminal command `echo contents > file_path` but won't overwrite existing files.
    """
    # Ensure the directory exists
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        return f"No such directory '{directory}'"

    # Ensure the file doesn't already exist
    if os.path.exists(file_path):
        return f"File '{file_path}' already exists."

    with open(file_path, "x", encoding="utf-8") as file:
        file.write(contents)

    return f"File '{file_path}' created successfully."


@tool
def create_directory(
    directory_path: Annotated[str, "The path to the new directory"],
) -> Annotated[str, "A message indicating success or failure"]:
    """
    Create a new directory at the specified path if it doesn't already exist, creating any necessary parent directories along the specified path.
    This tool is similar to the terminal command `mkdir -p directory_path`.
    """
    if os.path.exists(directory_path):
        return f"Directory '{directory_path}' already exists."

    os.makedirs(directory_path)
    return f"Directory '{directory_path}' created successfully."


@tool
def remove_file(
    file_path: Annotated[str, "The path to the file to be removed"],
) -> Annotated[str, "A message indicating success or failure"]:
    """
    Remove a file at the specified path.
    This tool is similar to the terminal command `rm file_path`.
    """
    return rm(file_path)


@tool
def copy_file(
    source_path: Annotated[str, "The path to the source file"],
    destination_path: Annotated[str, "The path to the destination file"],
) -> Annotated[str, "A message indicating success or failure"]:
    """
    Copy a file from the source path to the destination path.
    This tool is similar to the terminal command `cp source_path destination_path`.
    """
    return cp(source_path, destination_path)


@tool
def move_file(
    source_path: Annotated[str, "The path to the source file"],
    destination_path: Annotated[str, "The path to the destination file"],
) -> Annotated[str, "A message indicating success or failure"]:
    """
    Move a file from the source path to the destination path.
    This tool is similar to the terminal command `mv source_path destination_path`.
    """
    return mv(source_path, destination_path)


@tool
def rename_file(
    file_path: Annotated[str, "The path to the file to be renamed"],
    new_name: Annotated[str, "The new name for the file"],
) -> Annotated[str, "A message indicating success or failure"]:
    """
    Rename a file to a new name.
    This tool is similar to the terminal command `mv file_path new_name`.
    """
    if not os.path.exists(file_path):
        return f"No such file: '{file_path}'"

    directory = os.path.dirname(file_path)
    new_path = os.path.join(directory, new_name)

    return mv(file_path, new_path)


@tool
def copy_folder(
    source_path: Annotated[str, "The path to the source folder"],
    destination_path: Annotated[str, "The path to the destination folder"],
) -> Annotated[str, "A message indicating success or failure"]:
    """
    Copy a folder and its contents from the source path to the destination path.
    This tool is similar to the terminal command `cp -r source_path destination_path`.
    """
    return cp(source_path, destination_path)


@tool
def move_folder(
    source_path: Annotated[str, "The path to the source folder"],
    destination_path: Annotated[str, "The path to the destination folder"],
) -> Annotated[str, "A message indicating success or failure"]:
    """
    Move a folder and its contents from the source path to the destination path.
    This tool is similar to the terminal command `mv source_path destination_path`.
    """
    return mv(source_path, destination_path)


@tool
def rename_folder(
    folder_path: Annotated[str, "The path to the folder to be renamed"],
    new_name: Annotated[str, "The new name for the folder"],
) -> Annotated[str, "A message indicating success or failure"]:
    """
    Rename a folder to a new name.
    This tool is similar to the terminal command `mv folder_path new_name`.
    """
    if not os.path.exists(folder_path):
        return f"No such folder: '{folder_path}'"

    parent_directory = os.path.dirname(folder_path)
    new_path = os.path.join(parent_directory, new_name)

    return mv(folder_path, new_path)
