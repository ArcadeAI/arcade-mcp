import os

from langchain import hub
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_arcade import ArcadeToolManager
from langchain_openai import ChatOpenAI

arcade_api_key = os.environ["ARCADE_API_KEY"]
openai_api_key = os.environ["OPENAI_API_KEY"]

# Pull relevant agent model.
prompt = hub.pull("hwchase17/openai-functions-agent")

# Get all the tools available in Arcade
manager = ArcadeToolManager(api_key=arcade_api_key)

# Tool names follow the format "ToolkitName.ToolName"
tools = manager.get_tools(tools=["Web.ScrapeUrl"])
print(manager.tools)

# clear and init new tools from a toolkit
manager.init_tools(toolkits=["Search"])
print(manager.tools)
# get more tools
tools = manager.get_tools(toolkits=["Math"])
print(manager.tools)

# init the LLM
llm = ChatOpenAI(api_key=openai_api_key)

# Define agent
agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Try a few examples
agent_executor.invoke({"input": "Lookup Seymour Cray on Google"})
agent_executor.invoke({"input": "What is 1234567890 * 9876543210?"})
