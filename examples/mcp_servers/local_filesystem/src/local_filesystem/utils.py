import fnmatch
import stat
from pathlib import Path


def split_globs(globs: str) -> list[str]:
    patterns = [p.strip() for p in globs.split(",") if p.strip()]
    return patterns


def is_hidden(path: Path) -> bool:
    return path.name.startswith(".")


def match_any(name: str, patterns: list[str]) -> bool:
    if not patterns:
        return True
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def match_none(name: str, patterns: list[str]) -> bool:
    return all(not fnmatch.fnmatch(name, pattern) for pattern in patterns)


def path_type(path: Path, follow_symlinks: bool) -> str:
    try:
        st = path.stat() if follow_symlinks else path.lstat()
        mode = st.st_mode
        if stat.S_ISDIR(mode):
            return "dir"
        if stat.S_ISLNK(mode):
            return "symlink"
        return "file"  # noqa: TRY300
    except FileNotFoundError:
        return "unknown"
