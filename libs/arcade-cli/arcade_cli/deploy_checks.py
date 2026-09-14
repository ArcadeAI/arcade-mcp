from __future__ import annotations

from pathlib import Path

SUPPORTED_HINT = "arcade deploy supports Arcade MCP (Framework) Python servers built with MCPApp."

_FASTMCP_MARKERS = ("mcp.server.fastmcp", "import fastmcp", "from fastmcp", "FastMCP(")
_ARCADE_MCP_MARKERS = ("MCPApp", "arcade_mcp_server", "arcade_mcp")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _uses_fastmcp(text: str) -> bool:
    return any(marker in text for marker in _FASTMCP_MARKERS)


def _uses_arcade_mcp(text: str) -> bool:
    return any(marker in text for marker in _ARCADE_MCP_MARKERS)


def _looks_like_k8s_manifest(path: Path) -> bool:
    text = _read_text(path)
    return "apiVersion:" in text and "kind:" in text


def detect_unsupported_input(project_dir: Path, entrypoint: str) -> str | None:
    pyproject = project_dir / "pyproject.toml"

    if not pyproject.exists():
        if (project_dir / "package.json").exists():
            return f"This checkout looks like a TypeScript SDK MCP server. {SUPPORTED_HINT}"
        if (project_dir / "Dockerfile").exists():
            return f"This checkout contains only a Dockerfile. {SUPPORTED_HINT}"
        for pattern in ("*.yaml", "*.yml"):
            for candidate in sorted(project_dir.glob(pattern)):
                if _looks_like_k8s_manifest(candidate):
                    return f"This checkout contains only a Kubernetes manifest. {SUPPORTED_HINT}"
        return None

    entry_text = _read_text(project_dir / entrypoint)
    if entry_text and _uses_fastmcp(entry_text) and not _uses_arcade_mcp(entry_text):
        return f"This checkout looks like a FastMCP server. {SUPPORTED_HINT}"

    return None
