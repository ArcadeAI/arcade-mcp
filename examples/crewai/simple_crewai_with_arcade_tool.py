"""
This is a simple example of how to use Arcade with CrewAI.
The example authenticates into the user's Gmail account, retrieves their 5 most recent emails, and summarizes them.

The example assumes the following:
1. You have an Arcade API key and have set the ARCADE_API_KEY environment variable.
2. You have an OpenAI API key and have set the OPENAI_API_KEY environment variable.
3. You have installed the necessary dependencies in the requirements.txt file: `pip install -r requirements.txt`

"""

from crewai import Agent, Crew, Task
from crewai.llm import LLM
from crewai_arcade import ArcadeToolManager

manager = ArcadeToolManager(default_user_id="user@example.com")
tools = manager.get_tools(tools=["Google.ListEmails"])

crew_agent = Agent(
    role="Main Agent",
    backstory="You are a helpful assistant",
    goal="Help the user with their requests",
    tools=tools,
    allow_delegation=False,
    verbose=True,
    llm=LLM(model="gpt-4o"),
)

task = Task(
    description="Get the 5 most recent emails from the user's inbox and summarize them and recommend a response for each.",
    expected_output="A bulleted list with a one sentence summary of each email and a recommended response to the email.",
    agent=crew_agent,
    tools=crew_agent.tools,
)

crew = Crew(
    agents=[crew_agent],
    tasks=[task],
    verbose=True,
    memory=True,
)

result = crew.kickoff()

print("\n\n\n ------------ Result ------------ \n\n\n")
print(result)
