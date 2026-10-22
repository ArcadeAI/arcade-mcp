import os

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("echo-server")


@mcp.tool()
def echo(text: str) -> str:
    """Echo the text back."""
    return text


def main() -> None:
    # A non-default port and the root path, set only in code.
    mcp.run(
        "streamable-http",
        port=int(os.environ.get("FIXTURE_PORT", "8123")),
        streamable_http_path="/",
    )


if __name__ == "__main__":
    main()
