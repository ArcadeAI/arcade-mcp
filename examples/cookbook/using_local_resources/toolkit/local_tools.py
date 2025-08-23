"""
Local Resources Example - Using secrets, files, and external APIs
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

import aiofiles
import httpx
from arcade_tdk import ToolContext, tool


@tool(requires_secrets=["DATABASE_URL", "REDIS_URL"])
async def check_connections(ctx: ToolContext = None) -> dict[str, any]:
    """
    Check connections to local resources using secrets.

    Args:
        ctx: Tool context with secrets

    Returns:
        Connection status for each resource
    """
    results = {}

    # Check database connection
    try:
        db_url = ctx.get_secret("DATABASE_URL")
        # In real implementation, would connect to database
        results["database"] = {
            "status": "connected" if db_url else "missing_secret",
            "url_prefix": db_url[:20] + "..." if db_url else None,
        }
    except Exception as e:
        results["database"] = {"status": "error", "error": str(e)}

    # Check Redis connection
    try:
        redis_url = ctx.get_secret("REDIS_URL")
        results["redis"] = {
            "status": "connected" if redis_url else "missing_secret",
            "url_prefix": redis_url[:20] + "..." if redis_url else None,
        }
    except Exception as e:
        results["redis"] = {"status": "error", "error": str(e)}

    # Check local filesystem
    workspace = "./workspace"
    if ctx and ctx.metadata:
        for item in ctx.metadata:
            if item.key == "workspace_path":
                workspace = item.value
                break

    results["filesystem"] = {
        "workspace": workspace,
        "exists": os.path.exists(workspace),
        "writable": os.access(workspace, os.W_OK) if os.path.exists(workspace) else False,
    }

    return results


@tool(requires_secrets=["OPENAI_API_KEY"])
async def analyze_document(
    file_path: str, analysis_type: str = "summary", ctx: ToolContext = None
) -> dict[str, any]:
    """
    Analyze a local document using AI (demonstrates API key usage).

    Args:
        file_path: Path to the document
        analysis_type: Type of analysis (summary, keywords, sentiment)
        ctx: Tool context with secrets

    Returns:
        Analysis results
    """
    # Get workspace path
    workspace = "./workspace"
    if ctx and ctx.metadata:
        for item in ctx.metadata:
            if item.key == "workspace_path":
                workspace = item.value
                break

    full_path = Path(workspace) / file_path

    if not full_path.exists():
        return {"error": f"File not found: {file_path}"}

    # Read file content
    try:
        async with aiofiles.open(full_path) as f:
            content = await f.read()
    except Exception as e:
        return {"error": f"Failed to read file: {e!s}"}

    # Get API key
    try:
        api_key = ctx.get_secret("OPENAI_API_KEY")
    except:
        api_key = None

    # Mock analysis (in production would call OpenAI)
    if not api_key or api_key.startswith("sk-mock"):
        # Provide mock analysis
        word_count = len(content.split())
        lines = content.split("\n")

        if analysis_type == "summary":
            result = {
                "summary": f"Document contains {word_count} words across {len(lines)} lines. "
                + f"First line: {lines[0][:100] if lines else 'Empty document'}"
            }
        elif analysis_type == "keywords":
            # Simple keyword extraction
            words = content.lower().split()
            word_freq = {}
            for word in words:
                if len(word) > 4:  # Simple filter
                    word_freq[word] = word_freq.get(word, 0) + 1

            keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            result = {"keywords": [{"word": k, "count": v} for k, v in keywords]}
        else:
            result = {"analysis_type": analysis_type, "status": "not_implemented"}

        return {
            "file": file_path,
            "size": len(content),
            "analysis": result,
            "api_used": "mock",
        }

    # Real API call would go here
    return {"error": "Real API implementation not included in example"}


@tool
async def cache_resource(
    url: str, refresh: bool = False, ctx: ToolContext = None
) -> dict[str, any]:
    """
    Download and cache a resource from the internet.

    Args:
        url: URL to download
        refresh: Force refresh even if cached
        ctx: Tool context

    Returns:
        Information about the cached resource
    """
    # Get cache directory
    cache_dir = "./cache"
    if ctx and ctx.metadata:
        for item in ctx.metadata:
            if item.key == "cache_dir":
                cache_dir = item.value
                break

    # Create cache directory
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    # Generate cache filename
    url_hash = hashlib.md5(url.encode()).hexdigest()
    cache_file = cache_path / f"{url_hash}.json"

    # Check if already cached
    if cache_file.exists() and not refresh:
        try:
            async with aiofiles.open(cache_file) as f:
                cached_data = json.loads(await f.read())

            age_seconds = (
                datetime.now() - datetime.fromisoformat(cached_data["cached_at"])
            ).total_seconds()
            cached_data["age_seconds"] = age_seconds
            cached_data["from_cache"] = True

            return cached_data
        except:
            pass  # If cache read fails, re-download

    # Download resource
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            # Prepare cache data
            cache_data = {
                "url": url,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", "unknown"),
                "content_length": len(response.content),
                "cached_at": datetime.now().isoformat(),
                "cache_file": str(cache_file),
                "from_cache": False,
            }

            # Save content based on type
            if "json" in cache_data["content_type"]:
                cache_data["content"] = response.json()
            elif "text" in cache_data["content_type"]:
                cache_data["content"] = response.text[:1000]  # First 1000 chars
                cache_data["truncated"] = len(response.text) > 1000
            else:
                # For binary content, just save metadata
                cache_data["binary"] = True
                cache_data["content"] = None

            # Write to cache
            async with aiofiles.open(cache_file, "w") as f:
                await f.write(json.dumps(cache_data, indent=2))

            return cache_data

    except Exception as e:
        return {"error": f"Failed to download resource: {e!s}", "url": url}


@tool
async def process_workspace_files(
    pattern: str = "*.txt", operation: str = "list", ctx: ToolContext = None
) -> dict[str, any]:
    """
    Process files in the workspace directory.

    Args:
        pattern: File pattern to match
        operation: Operation to perform (list, count, total_size)
        ctx: Tool context

    Returns:
        Results of the operation
    """
    # Get workspace path
    workspace = "./workspace"
    if ctx and ctx.metadata:
        for item in ctx.metadata:
            if item.key == "workspace_path":
                workspace = item.value
                break

    workspace_path = Path(workspace)

    # Create workspace if it doesn't exist
    workspace_path.mkdir(parents=True, exist_ok=True)

    # Find matching files
    files = list(workspace_path.glob(pattern))

    if operation == "list":
        file_list = []
        for file in files[:20]:  # Limit to 20 files
            stat = file.stat()
            file_list.append({
                "name": file.name,
                "path": str(file.relative_to(workspace_path)),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

        return {
            "operation": "list",
            "pattern": pattern,
            "files": file_list,
            "total_found": len(files),
            "showing": len(file_list),
        }

    elif operation == "count":
        return {"operation": "count", "pattern": pattern, "count": len(files)}

    elif operation == "total_size":
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        return {
            "operation": "total_size",
            "pattern": pattern,
            "total_bytes": total_size,
            "human_readable": f"{total_size / 1024 / 1024:.2f} MB",
        }

    else:
        return {"error": f"Unknown operation: {operation}"}
