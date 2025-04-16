import json

from arcadepy import Arcade

client = Arcade(base_url="http://localhost:9099")

USER_ID = "rmbyrro+hubspot1@gmail.com"
TOOL_NAME = "Hubspot.CreateContact"

auth_response = client.tools.authorize(tool_name=TOOL_NAME, user_id=USER_ID)

if auth_response.status != "completed":
    print(f"Click this link to authorize: {auth_response.url}")

# Wait for the authorization to complete
client.auth.wait_for_completion(auth_response)

tool_input = {
    "company_id": "32033989556",
    "first_name": "Jason2",
    "last_name": "Bourne2",
    "email": "jason.bourne2@acme.com",
    "phone": "+1234567890",
    "mobile_phone": "+1234567890",
    "job_title": "Unbeatable2",
    # "keywords": "Acme",
    # "limit": 2,
    # "next_page_token": "1",
}

response = client.tools.execute(
    tool_name=TOOL_NAME,
    input=tool_input,
    user_id=USER_ID,
)
print(response.output.value)

with open("try.json", "w") as f:
    f.write(json.dumps(response.output.value, indent=4))
