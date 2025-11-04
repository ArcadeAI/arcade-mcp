from arcade_mcp_server import Context, tool


@tool
async def reporting_progress(context: Context) -> str:
    """Report progress back to the client"""
    total = 5

    for i in range(total):
        await context.progress.report(i + 1, total=total, message=f"Step {i + 1} of {total}")

    return "All progress reported successfully"
