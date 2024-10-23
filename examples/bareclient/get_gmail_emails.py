from arcadepy import Arcade

client = Arcade(
    base_url="http://localhost:9099",
)

user_id = "you@example.com"

# Start the authorization process
auth_response = client.tools.authorize(
    tool_name="Google.ListEmails",
    user_id=user_id,
)

if auth_response.status != "completed":
    print(f"Click this link to authorize: {auth_response.authorization_url}")
    input("After you have authorized, press Enter to continue...")

inputs = {"n_emails": 5}

response = client.tools.execute(
    tool_name="Google.ListEmails",
    inputs=inputs,
    user_id=user_id,
)
print(response)
