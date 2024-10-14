import os
import shutil
from datetime import datetime


def cat(file_path: str) -> str:
    """Read the contents of a file."""
    with open(file_path, encoding="utf-8") as file:
        return file.read()


def stat(file_path: str) -> dict:
    """Get file statistics."""
    file_stats = os.stat(file_path)
    return {
        "name": os.path.basename(file_path),
        "size": file_stats.st_size,
        "permissions": oct(file_stats.st_mode)[-3:],
        "owner_id": file_stats.st_uid,
        "group_id": file_stats.st_gid,
        "creation_time": datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
        "modification_time": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
        "access_time": datetime.fromtimestamp(file_stats.st_atime).isoformat(),
    }


def ls(directory: str) -> list[str]:
    """List directory contents."""
    if not os.path.exists(directory):
        raise FileNotFoundError(f"No such file or directory: '{directory}'")
    return os.listdir(directory)


def grep(file_path: str, pattern: str) -> list[str]:
    """Search for a pattern in a file and return matching lines."""
    import re

    with open(file_path, encoding="utf-8") as file:
        return [line.strip() for line in file if re.search(pattern, line)]


def rm(file_path: str) -> str:
    """Remove a file at the specified path."""
    if not os.path.exists(file_path):
        return f"No such file: '{file_path}'"

    os.remove(file_path)
    return f"File '{file_path}' removed successfully."


def cp(source_path: str, destination_path: str) -> str:
    """Copy a file or folder from the source path to the destination path."""
    if not os.path.exists(source_path):
        return f"No such file or directory: '{source_path}'"

    directory = os.path.dirname(destination_path)
    if not os.path.exists(directory):
        return f"No such directory '{directory}'"

    try:
        if os.path.isdir(source_path):
            shutil.copytree(source_path, destination_path)
            return f"Folder copied from '{source_path}' to '{destination_path}' successfully."
        else:
            shutil.copy2(source_path, destination_path)
            return f"File copied from '{source_path}' to '{destination_path}' successfully."
    except Exception as e:
        return f"Error copying: {e!s}"


def mv(source_path: str, destination_path: str) -> str:
    """Move a file or folder from the source path to the destination path."""
    if not os.path.exists(source_path):
        return f"No such file or directory: '{source_path}'"

    directory = os.path.dirname(destination_path)
    if not os.path.exists(directory):
        return f"No such directory '{directory}'"

    try:
        shutil.move(source_path, destination_path)
        return f"{'Folder' if os.path.isdir(source_path) else 'File'} moved from '{source_path}' to '{destination_path}' successfully."
    except Exception as e:
        return f"Error moving: {e!s}"
