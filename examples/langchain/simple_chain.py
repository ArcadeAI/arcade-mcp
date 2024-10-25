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
tools = manager.get_tools(langgraph=False)

# specify which Arcade tools to use
tools = manager.get_tools(tools=["Search.SearchGoogle"])

# init the LLM
llm = ChatOpenAI(api_key=openai_api_key)

# Define agent
agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Execute using agent_executor
agent_executor.invoke({"input": "Lookup Seymour Cray on Google"})
