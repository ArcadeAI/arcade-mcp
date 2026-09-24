from __future__ import annotations

import ast
from pathlib import Path

SUPPORTED_HINT = "arcade deploy supports Arcade MCP (Framework) Python servers built with MCPApp."

_FASTMCP_MODULES = ("fastmcp", "mcp.server.fastmcp")
_ARCADE_MCP_MODULE_PREFIX = "arcade_mcp"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _imported_modules(text: str) -> set[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _uses_fastmcp(modules: set[str]) -> bool:
    return any(
        module == root or module.startswith(f"{root}.")
        for module in modules
        for root in _FASTMCP_MODULES
    )


def _uses_arcade_mcp(modules: set[str]) -> bool:
    return any(module.startswith(_ARCADE_MCP_MODULE_PREFIX) for module in modules)


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

    modules = _imported_modules(_read_text(project_dir / entrypoint))
    if _uses_fastmcp(modules) and not _uses_arcade_mcp(modules):
        return f"This checkout looks like a FastMCP server. {SUPPORTED_HINT}"

    return None
