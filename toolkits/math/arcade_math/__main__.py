import sys
from typing import cast

from arcade_mcp_server import MCPApp
from arcade_mcp_server.mcp_app import TransportType

import arcade_math

app = MCPApp(
    name="Math",
    instructions=(
        "Use this server when you need to perform mathematical calculations to help users "
        "with arithmetic, trigonometry, statistics, exponents, rounding, and other math operations."
    ),
)

app.add_tools_from_module(arcade_math)


def main() -> None:
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 8000

    app.run(transport=cast(TransportType, transport), host=host, port=port)


if __name__ == "__main__":
    main()
