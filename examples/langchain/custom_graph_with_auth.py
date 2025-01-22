import os

# Import necessary classes and modules
from langchain_arcade import ArcadeToolManager
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

arcade_api_key = os.environ["ARCADE_API_KEY"]
openai_api_key = os.environ["OPENAI_API_KEY"]

# Initialize the tool manager and fetch tools compatible with langgraph
tool_manager = ArcadeToolManager(api_key=arcade_api_key)
tools = tool_manager.get_tools(
    toolkits=["Github", "Google"],
    langgraph=True,  # use langgraph-specific behavior
)
tool_node = ToolNode(tools)

# Create a language model instance and bind it with the tools
model = ChatOpenAI(model="gpt-4o", api_key=openai_api_key)
model_with_tools = model.bind_tools(tools)


#### Helpers ####
def get_nth_tool_call(state: MessagesState, n: int = 0):
    last_message = state["messages"][-1]
    return last_message.tool_calls[n]


def has_tool_calls(state: MessagesState):
    last_message = state["messages"][-1]
    return last_message.tool_calls is not None and len(last_message.tool_calls) > 0


#### Workflow ####


# Function to invoke the model and get a response
def call_agent(state: MessagesState):
    messages = state["messages"]
    response = model_with_tools.invoke(messages)
    # Return the updated message history
    return {"messages": [*messages, response]}


# Function to determine the next step in the workflow based on the last message
def should_continue(state: MessagesState):
    if has_tool_calls(state):
        tool_name = get_nth_tool_call(state)["name"]
        if tool_manager.requires_auth(tool_name):
            return "authorization"  # Proceed to authorization if required
        else:
            return "tools"  # Proceed to tool execution if no authorization is needed
    return END  # End the workflow if no tool calls are present


# Function to handle authorization for tools that require it
def authorize(state: MessagesState, config: dict):
    user_id = config["configurable"].get("user_id")
    tool_name = get_nth_tool_call(state)["name"]
    auth_response = tool_manager.authorize(tool_name, user_id)
    if auth_response.status != "completed":
        # Prompt the user to visit the authorization URL
        print(f"Visit the following URL to authorize: {auth_response.url}")

        # wait for the user to complete the authorization
        # and then check the authorization status again
        tool_manager.wait_for_auth(auth_response.id)
        if not tool_manager.is_authorized(auth_response.id):
            # node interrupt?
            raise ValueError("Authorization failed")

    return {"messages": state["messages"]}


if __name__ == "__main__":
    # Build the workflow graph using StateGraph
    workflow = StateGraph(MessagesState)

    # Add nodes (steps) to the graph
    workflow.add_node("agent", call_agent)
    workflow.add_node("tools", tool_node)
    workflow.add_node("authorization", authorize)

    # Define the edges and control flow between nodes
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, ["authorization", "tools", END])
    workflow.add_edge("authorization", "tools")
    workflow.add_edge("tools", "agent")

    # Set up memory for checkpointing the state
    memory = MemorySaver()

    # Compile the graph with the checkpointer
    graph = workflow.compile(checkpointer=memory)

    # Define the input messages from the user
    inputs = {
        "messages": [HumanMessage(content="what's on my calendar today?")],
    }

    # Configuration with thread and user IDs for authorization purposes
    config = {
        "configurable": {
            "thread_id": "4",
            "user_id": "user@example.comd",
        }
    }

    # Run the graph and stream the outputs
    for chunk in graph.stream(inputs, config=config, stream_mode="values"):
        # Pretty-print the last message in the chunk
        chunk["messages"][-1].pretty_print()
