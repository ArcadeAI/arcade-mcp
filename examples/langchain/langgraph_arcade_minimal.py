import os

from langchain_arcade import ToolManager
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

# 1) Set API keys (place your real keys in env variables or directly below)
arcade_api_key = os.environ.get("ARCADE_API_KEY", "YOUR_ARCADE_API_KEY")
openai_api_key = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")

# 2) Create an ToolManager and fetch/add tools/toolkits
manager = ToolManager(api_key=arcade_api_key)

# Tool names follow the format "ToolkitName.ToolName"
tools = manager.init_tools(tools=["Web.ScrapeUrl"])
print(manager.tools)

# Get all tools from a toolkit
tools = manager.init_tools(toolkits=["github"])
print(manager.tools)

# add a tool
manager.add_tool("Search.SearchGoogle")
print(manager.tools)

# add a toolkit
manager.add_toolkit("Search")
print(manager.tools)

# 3) Get StructuredTool objects for langchain
lc_tools = manager.to_langchain()

# 4) Create a ChatOpenAI model and bind the Arcade tools.
model = ChatOpenAI(model="gpt-4o", api_key=openai_api_key)
bound_model = model.bind_tools(lc_tools)

# 5) Use MemorySaver for checkpointing.
memory = MemorySaver()

# 5) Create a ReAct-style agent from the prebuilt function.
graph = create_react_agent(model=bound_model, tools=lc_tools, checkpointer=memory)

# 6) Provide basic config and a user query.
# Note: user_id is required for the tool to be authorized
config = {"configurable": {"thread_id": "1", "user_id": "user@example.com"}}
user_input = {"messages": [("user", "star the arcadeai/arcade-ai repo on github")]}

# 7) Stream the agent's output. If the tool is unauthorized, it may trigger interrupts
for chunk in graph.stream(user_input, config, stream_mode="values"):
    chunk["messages"][-1].pretty_print()

# if we were interrupted, we can check for interrupts in state
current_state = graph.get_state(config)
if current_state.tasks:
    for task in current_state.tasks:
        if hasattr(task, "interrupts"):
            for interrupt in task.interrupts:
                print(interrupt.value)
# Once you login using the printed link, you can resume the agent
