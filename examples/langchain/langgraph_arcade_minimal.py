import os

from langchain_arcade import ArcadeToolManager
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import NodeInterrupt
from langgraph.prebuilt import create_react_agent

# 1) Set API keys (place your real keys in env variables or directly below)
arcade_api_key = os.environ.get("ARCADE_API_KEY", "YOUR_ARCADE_API_KEY")
openai_api_key = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")

# 2) Create an ArcadeToolManager and fetch tools from the "Google" toolkit.
manager = ArcadeToolManager(api_key=arcade_api_key)

# Tool names follow the format "ToolkitName.ToolName"
tools = manager.get_tools(tools=["Web.ScrapeUrl"])
print(manager.tools)

# Get all tools from a toolkit
tools = manager.get_tools(toolkits=["Google"])
print(manager.tools)

# 3) Create a ChatOpenAI model and bind the Arcade tools.
model = ChatOpenAI(model="gpt-4o", api_key=openai_api_key)
bound_model = model.bind_tools(tools)

# 4) Use MemorySaver for checkpointing.
memory = MemorySaver()

# 5) Create a ReAct-style agent from the prebuilt function.
graph = create_react_agent(model=bound_model, tools=tools, checkpointer=memory)

# 6) Provide basic config and a user query.
# Note: user_id is required for the tool to be authorized
config = {"configurable": {"thread_id": "1", "user_id": "user@example.coom"}}
user_input = {"messages": [("user", "List any new and important emails in my inbox.")]}

# 7) Stream the agent's output. If the tool is unauthorized, it may trigger NodeInterrupt.
try:
    for chunk in graph.stream(user_input, config, stream_mode="values"):
        chunk["messages"][-1].pretty_print()
except NodeInterrupt as exc:
    print(f"\nNodeInterrupt occurred: {exc}")
    print("Please authorize the tool or update the request, then re-run.")

# If you need to authorize, you can do so via:
# auth_res = manager.authorize("Google_ListEmails", user_id="someone@example.com")
# manager.wait_for_auth(auth_res.id)
# Then run the graph again or edit the final tool call and call graph.stream(None, config).
