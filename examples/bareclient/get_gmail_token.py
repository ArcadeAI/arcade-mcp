from arcadepy import Arcade
from arcadepy.types.auth_authorize_params import AuthRequirement, AuthRequirementOauth2
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

client = Arcade(
    base_url="http://localhost:9099",
)

user_id = "you@example.com"

# Start the authorization process
auth_response = client.auth.authorize(
    auth_requirement=AuthRequirement(
        provider_id="google",
        oauth2=AuthRequirementOauth2(
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        ),
    ),
    user_id=user_id,
)

if auth_response.status != "completed":
    print(f"Click this link to authorize: {auth_response.authorization_url}")
    input("After you have authorized, press Enter to continue...")

# Use the token from the authorization response
creds = Credentials(auth_response.context.token)
service = build("gmail", "v1", credentials=creds)

# Now you can use the Google API
results = service.users().labels().list(userId="me").execute()
labels = results.get("labels", [])
print("Labels:", labels)
