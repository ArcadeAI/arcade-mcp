import json

from arcadepy import Arcade

client = Arcade()  # Automatically finds the `ARCADE_API_KEY` env variable

TOOL_NAME = "Hubspot.SearchCompanies"

auth_response = client.tools.authorize(tool_name=TOOL_NAME)

if auth_response.status != "completed":
    print(f"Click this link to authorize: {auth_response.url}")

# Wait for the authorization to complete
client.auth.wait_for_completion(auth_response)

tool_input = {
    "query": "Acme Inc",
}

response = client.tools.execute(
    tool_name=TOOL_NAME,
    input=tool_input,
)
print(response.output.text)

with open("try.json", "w") as f:
    f.write(json.dumps(response.output.text, indent=4))
