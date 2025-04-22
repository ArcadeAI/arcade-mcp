<h3 align="center">
  <a name="readme-top"></a>
  <img
    src="https://docs.arcade.dev/images/logo/arcade-logo.png"
  >
</h3>
<div align="center">
  <h3>Arcade Langchain Integration</h3>
    <a href="https://github.com/arcadeai/langchain-arcade/blob/main/LICENSE">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</a>
    <a href="https://pepy.tech/project/langchain-arcade">
  <img src="https://static.pepy.tech/badge/langchain-arcade" alt="Downloads">
  <a href="https://pypi.org/project/langchain-arcade/">
    <img src="https://img.shields.io/pypi/v/langchain-arcade.svg" alt="PyPI">
  </a>
</a>

</div>

<p align="center">
    <a href="https://docs.arcade.dev" target="_blank">Arcade Documentation</a> •
    <a href="https://docs.arcade.dev/toolkits" target="_blank">Toolkits</a> •
    <a href="https://github.com/ArcadeAI/arcade-py" target="_blank">Python Client</a> •
    <a href="https://github.com/ArcadeAI/arcade-js" target="_blank">JavaScript Client</a>
</p>

## Overview

`langchain-arcade` allows you to use Arcade tools in your LangChain and LangGraph applications. This integration provides a simple way to access Arcade's extensive toolkit ecosystem, including tools for search, email, document processing, and more.

## Installation

```bash
pip install langchain-arcade
```

## Basic Usage

### 1. Initialize the Tool Manager

The `ToolManager` is the main entry point for working with Arcade tools in LangChain:

```python
import os
from langchain_arcade import ToolManager

# Initialize with your API key
manager = ToolManager(api_key=os.environ["ARCADE_API_KEY"])

# Initialize with specific tools or toolkits
tools = manager.init_tools(
    tools=["Web.ScrapeUrl"],     # Individual tools
    toolkits=["Search"]          # All tools from a toolkit
)

# Convert to LangChain tools
langchain_tools = manager.to_langchain()
```

### 2. Use with LangGraph

```bash
pip install langgraph
```

Here's a simple example of using Arcade tools with LangGraph:

```python
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

# Create a LangGraph agent
model = ChatOpenAI(model="gpt-4o")
memory = MemorySaver()
graph = create_react_agent(model, tools, checkpointer=memory)

config = {"configurable": {"thread_id": "1", "user_id": "user@example.com"}}
user_input = {"messages": [("user", "List my important emails")]}

for chunk in graph.stream(user_input, config, stream_mode="values"):
    print(chunk["messages"][-1].content)
```

## Using Tools with Authorization in LangGraph

Many Arcade tools require user authorization. Here's how to handle it:

### 1. Using with prebuilt agents

```python
import os

from langchain_arcade import ToolManager
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# Initialize tools
manager = ToolManager(api_key=os.environ["ARCADE_API_KEY"])
manager.init_tools(toolkits=["Github"])
tools = manager.to_langchain(use_interrupts=True)

# Create agent
model = ChatOpenAI(model="gpt-4o")
graph = create_react_agent(model, tools)

# Run the agent with the "user_id" field in the config
# IMPORTANT the "user_id" field is required for tools that require user authorization
config = {"configurable": {"user_id": "user@lgexample.com"}}
user_input = {"messages": [("user", "Star the arcadeai/arcade-ai repository on GitHub")]}

for chunk in graph.stream(user_input, config, debug=True):
    if chunk.get("__interrupt__"):
        # print the authorization url
        print(chunk["__interrupt__"][0].value)
        # visit the URL to authorize the tool
        # once you have authorized the tool, you can run again and the agent will continue
    elif chunk.get("agent"):
        print(chunk["agent"]["messages"][-1].content)

# see the functional example for continuing the agent after authorization
# and for handling authorization errors gracefully

```

See the Functional examples in the [examples directory](https://github.com/ArcadeAI/arcade-ai/tree/main/examples/langchain) that continue the agent after authorization and handle authorization errors gracefully.

### Async Support

For asynchronous applications, use `AsyncToolManager`:

```python
import asyncio
from langchain_arcade import AsyncToolManager

async def main():
    manager = AsyncToolManager(api_key=os.environ["ARCADE_API_KEY"])
    await manager.init_tools(toolkits=["Google"])
    tools = await manager.to_langchain()

    # Use tools with async LangChain/LangGraph components

asyncio.run(main())
```

## Tool Authorization Flow

Many Arcade tools require user authorization. This can be handled in many ways but the `ToolManager` provides a simple flow that can be used with prebuilt agents and also the functional API. The typical flow is:

1. Attempt to use a tool that requires authorization
2. Check the state for interrupts from the `NodeInterrupt` exception (or Command)
3. Call `manager.authorize(tool_name, user_id)` to get an authorization URL
4. Present the URL to the user
5. Call `manager.wait_for_auth(auth_response.id)` to wait for completion
6. Resume the agent execution

## Available Toolkits

Arcade provides many toolkits including:

-   `Search`: Google search, Bing search
-   `Google`: Gmail, Google Drive, Google Calendar
-   `Web`: Crawling, scraping, etc
-   `Github`: Repository operations
-   `Slack`: Sending messages to Slack
-   `Linkedin`: Posting to Linkedin
-   `X`: Posting and reading tweets on X
-   And many more

For a complete list, see the [Arcade Toolkits documentation](https://docs.arcade.dev/toolkits).

## More Examples

For more examples, see the [examples directory](https://github.com/ArcadeAI/arcade-ai/tree/main/examples/langchain).
