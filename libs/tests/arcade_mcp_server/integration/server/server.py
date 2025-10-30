#!/usr/bin/env python3
"""E2E integration test MCP server"""

import sys

from arcade_mcp_server import MCPApp
from logging_tools import logging_tool
from progress_tools import reporting_progress
from sampling_tools import sampling
from tool_chaining_tools import (
    call_other_tool,
    the_other_tool,
)
from user_elicitation_tools import elicit_nickname

app = MCPApp(name="Test", version="1.0.0", log_level="DEBUG")

# Logging
app.add_tool(logging_tool)

# Report progress
app.add_tool(reporting_progress)

# Sampling
app.add_tool(sampling)

# User elicitation
app.add_tool(elicit_nickname)

# Tool chaining
app.add_tool(call_other_tool)
app.add_tool(the_other_tool)

if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "http"
    app.run(transport=transport, host="127.0.0.1", port=8000)
