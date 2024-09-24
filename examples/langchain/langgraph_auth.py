import time  # Import time for polling delays

from google.oauth2.credentials import Credentials
from langchain_google_community import GmailToolkit
from langchain_google_community.gmail.utils import (
    build_resource_service,
)
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# Step 1: Install required packages
# Run the following in your terminal:
# %pip install -qU langchain-google-community[gmail]
# %pip install -qU langchain-openai
# %pip install -qU langgraph
from arcade.client import Arcade, AuthProvider

client = Arcade()

# Start the authorization process for the tool "ListEmails"
auth_response = client.auth.authorize(
    provider=AuthProvider.google,
    scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    user_id="sam@arcade-ai.com",
)

# If authorization is not completed, prompt the user and poll for status
if auth_response.status != "completed":
    print(
        "Please complete the authorization challenge in your browser before continuing:"
    )
    print(auth_response.auth_url)
    input("Press Enter to continue...")

    # Poll for authorization status using the auth polling method
    while auth_response.status != "completed":
        # Wait before polling again to avoid spamming the server
        time.sleep(4)
        auth_response = client.auth.status(auth_response)

# Authorization is completed; proceed with obtaining credentials
creds = Credentials(auth_response.context.token)
api_resource = build_resource_service(credentials=creds)
toolkit = GmailToolkit(api_resource=api_resource)

# Step 4: Get available tools
tools = toolkit.get_tools()

# Step 5: Initialize the LLM and create an agent
llm = ChatOpenAI(model="gpt-4o")
agent_executor = create_react_agent(llm, tools)

# Step 6: Draft an email using the agent
example_query = "Read my latest emails to me and summarize them."
events = agent_executor.stream(
    {"messages": [("user", example_query)]},
    stream_mode="values",
)
for event in events:
    event["messages"][-1].pretty_print()
