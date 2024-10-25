import os

# Import necessary modules and classes
from langchain_arcade import ArcadeToolManager
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

arcade_api_key = os.environ["ARCADE_API_KEY"]
openai_api_key = os.environ["OPENAI_API_KEY"]

# Initialize the tool manager that fetches
# tools from arcade and wraps them as langgraph tools
tool_manager = ArcadeToolManager(api_key=arcade_api_key)
tools = tool_manager.get_tools(langgraph=True)

# Create an instance of the AI language model
model = ChatOpenAI(model="gpt-4o", api_key=openai_api_key)

# Init a prebuilt agent that can use tools
# in a REACT style langgraph
graph = create_react_agent(model, tools=tools)

# Define the initial input message from the user
inputs = {
    "messages": [HumanMessage(content="Star arcadeai/arcade-ai on GitHub!")],
}

# Configuration parameters for the agent and tools
config = {
    "configurable": {
        "thread_id": "2",
        "user_id": "user@example.com",
    }
}

# Stream the assistant's responses by executing the graph
for chunk in graph.stream(inputs, stream_mode="values", config=config):
    # Access the latest message from the conversation
    last_message = chunk["messages"][-1]
    # Print the assistant's message content
    print(last_message.content)
