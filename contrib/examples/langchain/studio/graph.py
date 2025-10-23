import os
from datetime import datetime

from configuration import AgentConfigurable
from langchain_arcade import ToolManager
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.errors import NodeInterrupt
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

# Initialize the Arcade Tool Manager with your API key
arcade_api_key = os.getenv("ARCADE_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

manager = ToolManager(api_key=arcade_api_key)
manager.init_tools(toolkits=["Github"])
tools = manager.to_langchain(use_interrupts=True)
tool_node = ToolNode(tools)

PROMPT_TEMPLATE = f"""
You are a helpful assistant who can use tools to help users with tasks
Today's date is {datetime.now().strftime("%Y-%m-%d")}

ALL RESPONSES should be in plain text and not markdown.
"""
# prompt for the main agent
prompt = ChatPromptTemplate.from_messages([
    ("system", PROMPT_TEMPLATE),
    ("placeholder", "{messages}"),
])
# Initialize the language model with your OpenAI API key
model = ChatOpenAI(model="gpt-4o", api_key=openai_api_key).bind_tools(tools)
prompted_model = prompt | model


class AgentState(MessagesState):
    auth_url: str | None = None


def call_agent(state):
    """Define the agent function that invokes the model"""
    messages = state["messages"]
    # replace placeholder with messages from state
    response = prompted_model.invoke({"messages": messages})
    return {"messages": [response]}


def should_continue(state: AgentState, config: dict):
    """Function to determine the next step based on the model's response"""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "check_auth"
    # If no tool calls are present, end the workflow
    return END


def check_auth(state: AgentState, config: dict):
    user_id = config["configurable"].get("user_id")
    tool_name = state["messages"][-1].tool_calls[0]["name"]
    auth_response = manager.authorize(tool_name, user_id)
    if auth_response.status != "completed":
        return {"auth_url": auth_response.url}
    else:
        return {"auth_url": None}


def authorize(state: AgentState, config: dict):
    """Function to handle tool authorization"""
    user_id = config["configurable"].get("user_id")
    tool_name = state["messages"][-1].tool_calls[0]["name"]
    auth_response = manager.authorize(tool_name, user_id)
    if auth_response.status != "completed":
        auth_message = (
            f"Please authorize the application in your browser:\n\n {state.get('auth_url')}"
        )
        raise NodeInterrupt(auth_message)


# Build the workflow graph
workflow = StateGraph(AgentState, AgentConfigurable)

# Add nodes to the graph
workflow.add_node("agent", call_agent)
workflow.add_node("tools", tool_node)
workflow.add_node("authorization", authorize)
workflow.add_node("check_auth", check_auth)

# Define the edges and control flow
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["check_auth", END])
workflow.add_edge("check_auth", "authorization")
workflow.add_edge("authorization", "tools")
workflow.add_edge("tools", "agent")

# Compile the graph with an interrupt after the authorization node
# so that we can prompt the user to authorize the application
graph = workflow.compile()
