import os

from arcadepy import Arcade
from arcadepy.types.auth_authorize_params import AuthRequirement, AuthRequirementOauth2
from google.oauth2.credentials import Credentials
from langchain_google_community import GmailToolkit
from langchain_google_community.gmail.utils import (
    build_resource_service,
)
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# Get the API key from the environment variable
api_key = os.getenv("ARCADE_API_KEY")

# Initialize the Arcade client
client = Arcade(api_key=api_key)

# Define the authorization requirement for Gmail
# see all possible gmail scopes here:
# https://developers.google.com/gmail/api/auth/scopes
auth_requirement = AuthRequirement(
    provider_id="google",
    oauth2=AuthRequirementOauth2(
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    ),
)

# Start the authorization process
user_id = "user@example.com"
auth_response = client.auth.authorize(
    auth_requirement=auth_requirement,
    user_id=user_id,
)

# Prompt the user to authorize if not already completed
if auth_response.status != "completed":
    print("Please authorize the application in your browser:")
    print(auth_response.authorization_url)
    input("Press Enter after completing authorization...")

    # Poll for authorization status
    while auth_response.status != "completed":
        auth_response = client.auth.status(
            authorization_id=auth_response.authorization_id,
            wait=30,  # Wait for up to 30 seconds
        )

# Obtain credentials using the authorization context
creds = Credentials(auth_response.context.token)
api_resource = build_resource_service(credentials=creds)

# Initialize the Gmail toolkit with the authorized API resource
toolkit = GmailToolkit(api_resource=api_resource)

# Retrieve the tools from the langchain gmail toolkit
tools = toolkit.get_tools()

# Initialize the language model and create an agent
llm = ChatOpenAI(model="gpt-4o")
agent_executor = create_react_agent(llm, tools)

# Define the user query
example_query = "Read my latest emails and summarize them."

# Execute the agent with the user query
events = agent_executor.stream(
    {"messages": [("user", example_query)]},
    stream_mode="values",
)

# Display the agent's response
for event in events:
    event["messages"][-1].pretty_print()
