import base64
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Annotated

from arcade_mcp_server import tool

from local_filesystem.utils import is_hidden, match_any, match_none, path_type, split_globs


@tool
def list_directory(
    path: Annotated[str, "Directory to list"],
    recursive: Annotated[bool, "Recurse into subdirectories"] = False,
    max_depth: Annotated[int, "Maximum recursion depth (1 = just this dir)"] = 1,
    include_globs: Annotated[str, "Comma-separated include patterns (e.g. *.py,*.md)"] = "",
    exclude_globs: Annotated[str, "Comma-separated exclude patterns"] = "",
    show_hidden: Annotated[bool, "Include dotfiles"] = False,
    follow_symlinks: Annotated[bool, "Follow symlinks during traversal"] = False,
    max_entries: Annotated[int, "Maximum number of entries to return"] = 1000,
) -> list[dict]:
    """Enumerate files and folders with metadata."""
    root = Path(path).expanduser().resolve()
    includes = split_globs(include_globs)
    excludes = split_globs(exclude_globs)

    results: list[dict] = []
    entries_count = 0

    def add_entry(p: Path) -> None:
        nonlocal entries_count
        try:
            st = p.stat() if follow_symlinks else p.lstat()
        except FileNotFoundError:
            return
        entry_type = path_type(p, follow_symlinks)
        if not show_hidden and is_hidden(p):
            return
        name = p.name
        if not match_any(name, includes) or not match_none(name, excludes):
            return
        results.append(
            {
                "path": str(p),
                "name": name,
                "type": entry_type,
                "size": int(st.st_size),
                "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(),
                "mode": int(st.st_mode),
                "is_symlink": p.is_symlink(),
            }
        )
        entries_count += 1

    if not root.exists() or not root.is_dir():
        return []

    if not recursive:
        for child in root.iterdir():
            if entries_count >= max_entries:
                break
            add_entry(child)
        return results

    # Recursive traversal with depth control
    start_depth = len(root.parts)
    for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
        current = Path(dirpath)
        depth = len(current.parts) - start_depth + 1
        if depth > max_depth:
            # Prevent descent by clearing dirnames
            dirnames[:] = []
            continue

        # Optionally filter hidden directories early
        if not show_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]

        for name in dirnames + filenames:
            if entries_count >= max_entries:
                break
            add_entry(current / name)
        if entries_count >= max_entries:
            break

    return results


@tool
def read_file(
    path: Annotated[str, "Path to file"],
    binary: Annotated[bool, "Return base64 when true"] = False,
    encoding: Annotated[str, "Text encoding when binary is false"] = "utf-8",
    start: Annotated[int, "Start byte offset (0-based)"] = 0,
    end: Annotated[int, "End byte offset (0 for EOF)"] = 0,
    max_bytes: Annotated[int, "Maximum bytes to read (0 for unlimited)"] = 1048576,
) -> dict:
    """Read file contents safely with optional slicing."""
    p = Path(path).expanduser().resolve()
    if not p.exists() or not p.is_file():
        return {"content": "", "bytes_read": 0, "encoding": encoding, "truncated": False}

    total_size = p.stat().st_size
    start_offset = max(0, start)
    end_offset = total_size if end <= 0 else min(end, total_size)
    if end_offset < start_offset:
        end_offset = start_offset
    to_read = end_offset - start_offset
    if max_bytes > 0:
        to_read = min(to_read, max_bytes)

    with open(p, "rb") as f:
        f.seek(start_offset)
        data = f.read(to_read)

    truncated = False
    if (end <= 0 and max_bytes > 0 and (start_offset + len(data)) < total_size) or (
        end > 0 and len(data) < (end_offset - start_offset)
    ):
        truncated = True

    if binary:
        return {
            "content": base64.b64encode(data).decode("ascii"),
            "bytes_read": len(data),
            "encoding": "base64",
            "truncated": truncated,
        }
    else:
        text = data.decode(encoding, errors="replace")
        return {
            "content": text,
            "bytes_read": len(data),
            "encoding": encoding,
            "truncated": truncated,
        }


@tool
def write_file(
    path: Annotated[str, "Path to write"],
    content: Annotated[str, "Text or base64 when binary=true"],
    binary: Annotated[bool, "Interpret content as base64 when true"] = False,
    encoding: Annotated[str, "Text encoding when binary is false"] = "utf-8",
    mode: Annotated[str, "overwrite | append | create_new"] = "overwrite",
    make_parents: Annotated[bool, "Create parent directories if needed"] = True,
) -> dict:
    """Create/overwrite/append text or binary file."""
    p = Path(path).expanduser().resolve()
    if make_parents:
        p.parent.mkdir(parents=True, exist_ok=True)

    data = base64.b64decode(content) if binary else content.encode(encoding)

    created = False
    appended = False

    if mode == "create_new":
        if p.exists():
            raise FileExistsError(f"Path already exists: {p}")
        with open(p, "wb") as f:
            f.write(data)
        created = True
    elif mode == "append":
        with open(p, "ab") as f:
            f.write(data)
        appended = True
        created = not (p.stat().st_size > len(data))  # heuristic
    elif mode == "overwrite":
        with open(p, "wb") as f:
            f.write(data)
        created = True
    else:
        raise ValueError("Invalid mode. Use overwrite | append | create_new")

    return {"bytes_written": len(data), "created": created, "appended": appended}


@tool
def tail_file(
    path: Annotated[str, "Path to file"],
    lines: Annotated[int, "Number of lines from end (ignored if bytes>0)"] = 100,
    bytes: Annotated[int, "Number of bytes from end (0 to disable)"] = 0,
    encoding: Annotated[str, "Text encoding for output"] = "utf-8",
) -> dict:
    """Return last N lines or bytes from a file."""
    p = Path(path).expanduser().resolve()
    if not p.exists() or not p.is_file():
        return {"content": "", "truncated": False}

    size = p.stat().st_size
    if bytes > 0:
        start = max(0, size - bytes)
        with open(p, "rb") as f:
            f.seek(start)
            data = f.read(bytes)
        text = data.decode(encoding, errors="replace")
        return {"content": text, "truncated": start > 0}

    # Tail by lines
    block_size = 8192
    data = bytearray()
    newline_count = 0
    with open(p, "rb") as f:
        pos = size
        while pos > 0 and newline_count <= lines:
            read_size = block_size if pos >= block_size else pos
            pos -= read_size
            f.seek(pos)
            chunk = f.read(read_size)
            data[:0] = chunk
            newline_count = data.count(b"\n")
            if len(data) > 8 * 1024 * 1024:  # 8MB safety cap
                break
    decoded = data.decode(encoding, errors="replace")
    split_lines = decoded.splitlines()[-lines:]
    return {"content": "\n".join(split_lines), "truncated": len(split_lines) < lines}


@tool
def stat_path(
    path: Annotated[str, "Path to stat"],
    follow_symlinks: Annotated[bool, "Follow symlinks"] = False,
) -> dict:
    """Return metadata for file/dir/symlink."""
    p = Path(path).expanduser().resolve()
    exists = p.exists() or p.is_symlink()
    try:
        st = p.stat() if follow_symlinks else p.lstat()
    except FileNotFoundError:
        return {"exists": False}
    info = {
        "exists": exists,
        "path": str(p),
        "type": path_type(p, follow_symlinks),
        "size": int(st.st_size),
        "mode": int(st.st_mode),
        "uid": int(getattr(st, "st_uid", 0)),
        "gid": int(getattr(st, "st_gid", 0)),
        "atime": datetime.fromtimestamp(st.st_atime).isoformat(),
        "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(),
        "ctime": datetime.fromtimestamp(st.st_ctime).isoformat(),
        "is_symlink": p.is_symlink(),
    }
    if p.is_symlink():
        try:
            info["target"] = str(p.resolve(strict=False))
        except Exception:
            info["target"] = None
    return info


@tool
def create_directory(
    path: Annotated[str, "Directory path to create"],
    exist_ok: Annotated[bool, "Do not error if directory exists"] = True,
    parents: Annotated[bool, "Create missing parents"] = True,
    mode: Annotated[int, "POSIX permissions like 0o755"] = 0o755,
) -> dict:
    """Create a directory path."""
    p = Path(path).expanduser().resolve()
    if parents:
        p.mkdir(mode=mode, parents=True, exist_ok=exist_ok)
    else:
        if p.exists() and not exist_ok:
            raise FileExistsError(f"Directory exists: {p}")
        p.mkdir(mode=mode)
    return {"created": True}


@tool
def move_path(
    src: Annotated[str, "Source path"],
    dst: Annotated[str, "Destination path"],
    overwrite: Annotated[bool, "Replace destination if exists"] = False,
    make_parents: Annotated[bool, "Create destination parents"] = True,
) -> dict:
    """Move/rename files or directories."""
    src_p = Path(src).expanduser().resolve()
    dst_p = Path(dst).expanduser().resolve()
    if make_parents:
        dst_p.parent.mkdir(parents=True, exist_ok=True)

    if dst_p.exists():
        if overwrite:
            # Atomic replace for files; for dirs, move into or replace
            if src_p.is_file():
                os.replace(src_p, dst_p)
            else:
                # Move into destination if it's an existing directory
                if dst_p.is_dir():
                    shutil.move(str(src_p), str(dst_p))
                else:
                    os.replace(src_p, dst_p)
        else:
            raise FileExistsError(f"Destination exists: {dst_p}")
    else:
        shutil.move(str(src_p), str(dst_p))
    return {"moved": True}


@tool
def copy_path(
    src: Annotated[str, "Source path"],
    dst: Annotated[str, "Destination path"],
    overwrite: Annotated[bool, "Replace destination if exists"] = False,
    preserve_metadata: Annotated[bool, "Preserve file metadata"] = True,
    follow_symlinks: Annotated[bool, "Follow symlinks when copying files"] = False,
    make_parents: Annotated[bool, "Create destination parents"] = True,
) -> dict:
    """Copy file or directory tree."""
    src_p = Path(src).expanduser().resolve()
    dst_p = Path(dst).expanduser().resolve()
    if make_parents:
        dst_p.parent.mkdir(parents=True, exist_ok=True)

    if src_p.is_dir():
        shutil.copytree(
            src=str(src_p),
            dst=str(dst_p),
            dirs_exist_ok=overwrite,
            copy_function=shutil.copy2 if preserve_metadata else shutil.copy,
        )
    else:
        if dst_p.exists() and not overwrite:
            raise FileExistsError(f"Destination exists: {dst_p}")
        copy_fn = shutil.copy2 if preserve_metadata else shutil.copy
        copy_fn(str(src_p), str(dst_p), follow_symlinks=follow_symlinks)
    return {"copied": True}


@tool
def search_files(
    root: Annotated[str, "Root directory to search"],
    name_globs: Annotated[str, "Comma-separated include name patterns"] = "",
    exclude_globs: Annotated[str, "Comma-separated exclude name patterns"] = "",
    regex: Annotated[str, "Content regex (ignored when fixed_string=true)"] = "",
    fixed_string: Annotated[bool, "Search content by plain substring"] = False,
    case_insensitive: Annotated[bool, "Regex or substring is case-insensitive"] = False,
    max_results: Annotated[int, "Maximum number of results"] = 100,
    follow_symlinks: Annotated[bool, "Follow symlinks"] = False,
    binary: Annotated[bool, "Search binary files too"] = False,
    include_hidden: Annotated[bool, "Include hidden files"] = False,
) -> list[dict]:
    """Find files by name and optionally by content."""
    base = Path(root).expanduser().resolve()
    if not base.exists() or not base.is_dir():
        return []

    includes = split_globs(name_globs)
    excludes = split_globs(exclude_globs)

    flags = re.IGNORECASE if case_insensitive else 0
    pattern = None
    if regex and not fixed_string:
        try:
            pattern = re.compile(regex, flags)
        except re.error as e:
            raise ValueError(f"Invalid regex: {e}")

    results: list[dict] = []
    for dirpath, dirnames, filenames in os.walk(base, followlinks=follow_symlinks):
        current = Path(dirpath)
        if not include_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]

        for name in filenames:
            if len(results) >= max_results:
                return results
            if not include_hidden and name.startswith("."):
                continue
            if includes and not match_any(name, includes):
                continue
            if not match_none(name, excludes):
                continue

            file_path = current / name
            if not binary:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue
                matched = False
                match_lines: list[dict] = []
                if fixed_string and regex:
                    hay = content if not case_insensitive else content.lower()
                    needle = regex if not case_insensitive else regex.lower()
                    if needle in hay:
                        matched = True
                        for idx, line in enumerate(content.splitlines(), start=1):
                            if needle in (line if not case_insensitive else line.lower()):
                                match_lines.append({"line": idx, "text": line})
                elif pattern is not None:
                    for idx, line in enumerate(content.splitlines(), start=1):
                        if pattern.search(line):
                            matched = True
                            match_lines.append({"line": idx, "text": line})
                else:
                    matched = True  # name matched and no content filter

                if matched:
                    results.append(
                        {
                            "path": str(file_path),
                            "match_lines": match_lines,
                            "match_count": len(match_lines),
                        }
                    )
            else:
                # Binary search only supports name filtering (no content scan)
                results.append({"path": str(file_path), "match_lines": [], "match_count": 0})

    return results
