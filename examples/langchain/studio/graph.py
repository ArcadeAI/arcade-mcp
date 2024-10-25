import os
import time

from configuration import AgentConfigurable
from langchain_arcade import ArcadeToolManager
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

# Initialize the Arcade Tool Manager with your API key
arcade_api_key = os.getenv("ARCADE_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

toolkit = ArcadeToolManager(api_key=arcade_api_key)
# Retrieve tools compatible with LangGraph
tools = toolkit.get_tools(langgraph=True)
tool_node = ToolNode(tools)

# Initialize the language model with your OpenAI API key
model = ChatOpenAI(model="gpt-4o", api_key=openai_api_key)
# make the model aware of the tools
model_with_tools = model.bind_tools(tools)


# Define the agent function that invokes the model
def call_agent(state):
    messages = state["messages"]
    response = model_with_tools.invoke(messages)
    # Return the updated message history
    return {"messages": [*messages, response]}


# Function to determine the next step based on the model's response
def should_continue(state: MessagesState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        tool_name = last_message.tool_calls[0]["name"]
        if toolkit.requires_auth(tool_name):
            # If the tool requires authorization, proceed to the authorization step
            return "authorization"
        else:
            # If no authorization is needed, proceed to execute the tool
            return "tools"
    # If no tool calls are present, end the workflow
    return END


# Function to handle tool authorization
def authorize(state: MessagesState, config: dict):
    user_id = config["configurable"].get("user_id")
    tool_name = state["messages"][-1].tool_calls[0]["name"]
    auth_response = toolkit.authorize(tool_name, user_id)

    if auth_response.status == "completed":
        # Authorization is complete; proceed to the next step
        return {"messages": state["messages"]}
    else:
        # Prompt the user to complete authorization
        print("Please authorize the application in your browser:")
        print(auth_response.authorization_url)
        input("Press Enter after completing authorization...")

        # Poll for authorization status
        while not toolkit.is_authorized(auth_response.authorization_id):
            time.sleep(3)
        return {"messages": state["messages"]}


# Build the workflow graph
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
