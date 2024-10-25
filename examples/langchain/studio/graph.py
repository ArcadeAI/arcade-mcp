import time

from langchain_arcade import ArcadeToolkit
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from studio.configuration import AgentConfigurable

# Initialize the Arcade Toolkit with tools
toolkit = ArcadeToolkit()
tools = toolkit.get_tools(langgraph=True)
tool_node = ToolNode(tools)

# Define the model
model = ChatOpenAI(model="gpt-4o")
model_with_tools = model.bind_tools(tools)


# Define the agent node
def call_agent(state):
    messages = state["messages"]
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}


def should_continue(state: MessagesState):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        if toolkit.requires_auth(last_message.tool_calls[0]["name"]):
            return "authorization"
        else:
            return "tools"
    return END


def authorize(state: MessagesState, config: dict):
    user_id = config["configurable"].get("user_id")
    tool_name = state["messages"][-1].tool_calls[0]["name"]
    auth_response = toolkit.authorize(tool_name, user_id)
    if auth_response.status == "completed":
        return {"messages": state["messages"][-1]}
    else:
        print(f"Visit the following URL to authorize: {auth_response.authorization_url}")
        while not toolkit.is_authorized(auth_response.authorization_id):
            time.sleep(3)
        return {"messages": state["messages"][-1]}


# Build the graph
workflow = StateGraph(MessagesState, AgentConfigurable)

# Add nodes to the graph
workflow.add_node("agent", call_agent)
workflow.add_node("tools", tool_node)
workflow.add_node("authorization", authorize)

# Define the edges and control flow
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["authorization", "tools", END])
workflow.add_edge("authorization", "tools")
workflow.add_edge("tools", "agent")

# Compile the graph
graph = workflow.compile()
