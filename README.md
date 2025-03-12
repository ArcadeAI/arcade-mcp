<h3 align="center">
  <a name="readme-top"></a>
  <img
    src="https://docs.arcade.dev/images/logo/arcade-logo.png"
    style="width: 400px;"
  >
</h3>
<div align="center">
    <a href="https://github.com/arcadeai/arcade-ai/blob/main/LICENSE">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</a>
  <img src="https://img.shields.io/github/last-commit/ArcadeAI/arcade-ai" alt="GitHub last commit">
</a>
<a href="https://github.com/arcadeai/arcade-ai/actions/workflow/on-release-main.yml">
<img src="https://img.shields.io/github/actions/workflow/status/arcadeai/arcade-ai/check-toolkits.yml" alt="GitHub Actions Status">
</a>
<a href="https://img.shields.io/pypi/pyversions/arcade-ai">
  <img src="https://img.shields.io/pypi/pyversions/arcade-ai" alt="Python Version">
</a>
</div>
<div>
  <p align="center" style="display: flex; justify-content: center; gap: 10px;">
    <a href="https://x.com/TryArcade">
      <img src="https://img.shields.io/badge/Follow%20on%20X-000000?style=for-the-badge&logo=x&logoColor=white" alt="Follow on X" style="width: 125px;height: 25px; padding-top: .8px; border-radius: 5px;" />
    </a>
    <a href="https://www.linkedin.com/company/arcade-ai" >
      <img src="https://img.shields.io/badge/Follow%20on%20LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" alt="Follow on LinkedIn" style="width: 150px; padding-top: 1.5px;height: 22px; border-radius: 5px;" />
    </a>
    <a href="https://discord.com/invite/GUZEMpEZ9p">
      <img src="https://img.shields.io/badge/Join%20our%20Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Join our Discord" style="width: 150px; padding-top: 1.5px; height: 22px; border-radius: 5px;" />
    </a>
  </p>
</div>

<p align="center" style="display: flex; justify-content: center; gap: 5px; font-size: 15px;">
    <a href="https://docs.arcade.dev/home" target="_blank">Documentation</a> •
    <a href="https://docs.arcade.dev/tools" target="_blank">Tools</a> •
    <a href="https://docs.arcade.dev/home/quickstart" target="_blank">Quickstart</a> •
    <a href="https://docs.arcade.dev/home/contact-us" target="_blank">Contact Us</a>

# Arcade Tool SDK

Arcade is a developer platform that lets you build, deploy, and manage tools for AI agents.

The Tool SDK makes it easy to create powerful, secure tools that your agents can use to interact with the world.

![diagram](https://github.com/user-attachments/assets/1a567e5f-d6b4-4b1e-9918-c401ad232ebb)

To learn more, check out our [documentation](https://docs.arcade.dev/home).

_Pst. hey, you, give us a star if you like it!_

<a href="https://github.com/ArcadeAI/arcade-ai">
  <img src="https://img.shields.io/github/stars/ArcadeAI/arcade-ai.svg" alt="GitHub stars">
</a>

## Table of Contents

-   [The Problems with Agent Tools](#the-problems-with-agent-tools)
-   [Without Arcade vs. With Arcade](#without-arcade-vs-with-arcade)
-   [Why Build Tools with Arcade?](#why-build-tools-with-arcade)
-   [Quickstart: Call your first tool](#quickstart-call-your-first-tool)
-   [Building Your Own Tools](#building-your-own-tools)
    -   [Tool SDK Installation](#tool-sdk-installation)
    -   [Creating a New Tool](#creating-a-new-tool)
    -   [Sharing Your Toolkit](#sharing-your-toolkit)
-   [Calling your tools](#calling-your-tools)
    -   [LLM API](#llm-api)
    -   [Tools API](#tools-api)
    -   [Integrating with Agent Frameworks](#integrating-with-agent-frameworks)
    -   [Arcade Auth API](#arcade-auth-api)
-   [Client Libraries](#client-libraries)
-   [Support and Community](#support-and-community)

## The Problems with Agent Tools

**The Auth Problem**
Most agent tools lack multi-user authorization capabilities. They typically rely on hardcoded API keys or environment variables, making it impossible to securely access user-specific data or integrate with services requiring user authentication and/or authorization.

**The Execution Problem**
Tool execution typically happens on the same resources as the agent, limiting scalability and preventing the use of specialized compute resources (serverless, on-premise, etc.).

**The Tool Definition Problem**
Maintaining tool definitions separately from code is difficult, especially when tools must work across multiple agent applications and LLMs with different formats.

Arcade solves these challenges with standardized tool definition and execution, a robust multi-user auth system, and flexible integration APIs.

## Without Arcade vs. With Arcade

<table>
<tr>
<th>Without Arcade</th>
<th>With Arcade</th>
</tr>
<tr>
<td >

```python
# Building a Gmail tool without Arcade
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def get_credentials():
    # Get credentials from environment variables
    secret = os.environ["GMAIL_CREDENTIALS"]
    # Always same token same user
    # Usually we dangerously elevated privileges
    token = os.environ["GMAIL_TOKEN"]
    return secret, token

# Define the tool in code, then update
# definition for each LLM
def list_emails(max_results=10):

    # Get credentials here? pass it in?
    secret, token = get_credentials()
    # Cache the token?
    # How do we know the user?

    # What if the user isn't authorized? OAuth Flow?
    # handle token refresh?
    try:
        credentials = Credentials(
            token=token,
            secret=secret)
    except Exception as e:
        # Start the OAuth flow?
        # redirect ? how do we know the user?
        # handle token refresh?
        # what are the right scopes?
        # handle errors?
        # for EVERY SERVICE?

    # Call the API
    service = build('gmail', 'v1', credentials=credentials)

    messages = service.users().messages().list(
        userId='me', maxResults=max_results
    ).execute()

    return messages

# Problems:
# - Hardcoded credentials means no multi-user support
# - Security risks from exposing secrets/tokens/keys
# - Manual OAuth flow implementation, if any
# - Manually updated tool definitions
# - No standard format translated across LLMs
```

</td>
<td>

```python
# Building a Gmail tool with Arcade SDK

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Google
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# Define the tool in code, automatically generate
# tool definition for all LLMs
@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
) # Automatically generated tool definition from annotations
async def list_emails(
    context: ToolContext,
    max_results: Annotated[int, "Maximum emails to return"] = 10,
) -> Annotated[dict, "List of emails"]:
    """Lists emails in the user's Gmail inbox."""

    # Auth token automatically provided and managed by Arcade
    # Token is guaranteed to be valid for the user of the agent
    token = context.authorization.token

    # No need to manually refresh tokens or handle OAuth flows
    # Credentials are automatically refreshed as needed
    service = build('gmail', 'v1', credentials=token)

    messages = service.users().messages().list(
        userId='me', maxResults=max_results
    ).execute()

    return messages

# Solutions with Arcade:
# - Multi-tenant (works for any user)
# - Compliant and secure token, secret, and key management
# - Can access any user's data or services AS the user
# - Tool definition is created automatically
# - Formatted for all LLMs and ready to use
```

</td>
</tr>
</table>

## Why Build Tools with Arcade?

Arcade solves key challenges for agent developers:

1. **Auth Native to Agents**: Authentication designed for agentic workflows — the right token is always available for each user without complex integration work.

2. **Multi-Tenant Tool Calling**: Enable your agent to take actions AS the specific user of the agent

3. **Better Agent Capabilities**: Build tools that securely connect to the services your users want your agent to integrate with (Gmail, Slack, Google Drive, Zoom, etc.) without complex integration code.

4. **Clean Codebase**: Eliminate environment variables full of API keys and complex OAuth implementations from your application code.

5. **Flexible Integration**: Choose your integration approach:

    - LLM API for the simplest experience with hundreds of pre-built tools
    - Tools API for direct execution control
    - Auth API for authentication-only integration
    - Framework connectors for LangChain, CrewAI and others

6. **Zero Schema Maintenance**: Tool definitions generate automatically from code annotations and translate to any LLM format.

7. **Built-in Evaluation**: Evaluate your tools across user scenarios, llms, and context with Arcade's tool calling evaluation framework. Ensure your tools are working as expected and are useful for your agents.

8. **Complete Tooling Ecosystem**: Built-in evaluation framework, scalable execution infrastructure, and flexible deployment options (including VPC, Docker, and Kubernetes).

Arcade lets you focus on creating useful tool functionality rather than solving complex authentication, deployment, and integration challenges.

## Quickstart: Call your first tool

```bash
# Install the Arcade CLI
pip install arcade-ai

# Log in to Arcade
arcade login

# Show what tools are hosted by Arcade
arcade show

# show what tools are in a toolkit
arcade show -T Google

# look at the definition of a tool
arcade show -t Google.ListEmails

# Run Arcade Chat and call a tool
arcade chat -s
```

Ask the chat to

-   Read your latest email in gmail
-   Find latest tweets by @tryarcade

If Arcade already hosts the tools you need to build your agent, you
can navigate to the [Quickstart](https://docs.arcade.dev/home/quickstart) to
learn how to call tools programmatically in Python, Typescript, or HTTP.

However, if not, you can start building your own tools and use them through Arcade
benefitting from all the same features (like auth) that the cloud hosted tools have.

## Building Your Own Tools

Arcade provides a tool SDK that allows you to build your own tools and use them in your agentic applications just like the existing tools Arcade provides. This is useful for building new tools, customizing existing tools to fit your needs, combining multiple tools, or building tools that are not yet supported by Arcade.

### Tool SDK Installation

**Prerequisites**

-   **Python 3.10+**
-   **Arcade Account:** [Sign up here](https://api.arcade.dev/signup) to get started.

Now you can install the Tool SDK through pip.

1. **Install the Arcade CLI:**

    ```bash
    pip install arcade-ai
    ```

    If you plan on writing evaluations for your tools and the LLMs you use, you will also need to install the `evals` extra.

    ```bash
    pip install arcade-ai[evals]
    ```

2. **Log in to Arcade:**
    ```bash
    arcade login
    ```
    This will prompt you to open a browser and authorize the CLI. It will then save the credentials to your machine typically in `~/.arcade/credentials.json`.

Now you're ready to build tools with Arcade!

### Creating a New Tool

1. **Generate a new toolkit:**

    ```bash
    arcade new
    ```

    This will create a new toolkit in the current directory.

    The generated toolkit includes all the scaffolding you need for a working tool. Look for the `mytoolkit/tool.py` file to customize the behavior of your tool.

2. **Install your new toolkit:**

    ```bash
    # make sure you have python and poetry installed
    python --version
    pip install "poetry<2"

    # install your new toolkit
    cd mytoolkit
    make install
    ```

3. **Show the tools in the new Toolkit:**

    ```bash
    # show the tools in Mytoolkit
    arcade show --local -T Mytoolkit

    # show the definition of a tool
    arcade show --local -t Mytoolkit.SayHello

    # show all tools installed in your local python environment
    arcade show --local
    ```

4. **Serve the toolkit:**

    ```bash
    # serve the toolkit
    arcade serve
    ```

    This will serve the toolkit at `http://localhost:8002`.

This last command will start a server that hosts your toolkit at `http://localhost:8002`.
If you are running the Arcade Engine locally, go to localhost:9099 (or other local address)
and add the worker address in the "workers" page.

To use your tools in Arcade Cloud, you can use reverse proxy services like

-   localtunnel (`npm install localtunnel && lt --port 8002`)
-   tailscale
-   ngrok

that will provide a tunnel from the local server to Arcade cloud.

Once hosted on a public address you can head to
https://api.arcade.dev/dashboard/workers and call your toolkits
through the playground, LLM API, or Tools API of Arcade.

For more details on building your own tools, see the [Tool SDK Documentation](https://docs.arcade.dev/home/build-tools/create-a-tool-with-auth) and see more on calling your own tools below.

### Sharing Your Toolkit

To list your toolkit on Arcade, you can open a PR to add your toolkit to the [arcadeai/docs](https://github.com/ArcadeAI/docs) repository.

<br>
<br>

## Calling your tools

Arcade provides multiple ways to use your tools with various agent frameworks. Depending on your use case, you can choose the best method for your application.

### LLM API

The LLM API provides the simplest way to integrate Arcade tools into your application. It extends the standard OpenAI API with additional capabilities:

```python
import os
from openai import OpenAI

prompt = "Say hello to Sam"

api_key = os.environ["ARCADE_API_KEY"]
openai = OpenAI(
    base_url="https://api.arcade.dev/v1",
    api_key=api_key,
)

response = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
    ],
    tools=["Mytoolkit.SayHello"],
    tool_choice="generate",
    user="user@example.com"
)

print(response.choices[0].message.content)
```

When a user hasn't authorized a service, the API seamlessly returns an authorization link in the response:

```
Please authorize the tool by visiting: https://some.auth.url.arcade.will.generate.for.you...

```

All you need to do is show the url to the user, and from then on, the user will never have to do this again. All future requests will use the authorized token.

After authorization, the same API call returns the completed action:

```
Hello Sam!
```

### Tools API

Use the Tools API when you want to integrate Arcade's runtime for tool calling into an agent framework (like LangChain or LangGraph), or if you're using your own approach and want to call Arcade tools or tools you've built with the Arcade Tool SDK.

Here's an example of how to use the Tools API to call a tool directly without a framework:

```python
import os
from arcadepy import Arcade

client = Arcade(api_key=os.environ["ARCADE_API_KEY"])

# Start the authorization process for Slack
auth_response = client.tools.authorize(
    tool_name="Mytoolkit.SayHello",
    user_id="user@example.com",
)

# If the tool is not already authorized, prompt the user to authenticate
if auth_response.status != "completed":
    print("Please authorize by visiting:")
    print(auth_response.url)
    client.auth.wait_for_completion(auth_response)

# Execute the tool to send a Slack message after authorization
tool_input = {
    "username": "sam",
    "message": "I'll be late to the meeting"
}
response = client.tools.execute(
    tool_name="Mytoolkit.SayHello",
    input=tool_input,
    user_id="user@example.com",
)
print(response)

```

### Integrating with Agent Frameworks

You can also use the Tools API with a framework like LangChain or LangGraph.

Currently Arcade provides ease-of-use integrations for the following frameworks:

-   LangChain/Langgraph
-   CrewAI
-   LlamaIndex (coming soon)

Here's an example of how to use the Tools API with LangChain/Langgraph:

```python
import os
from langchain_arcade import ArcadeToolManager
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

arcade_api_key = os.environ["ARCADE_API_KEY"]
openai_api_key = os.environ["OPENAI_API_KEY"]

manager = ArcadeToolManager(api_key=arcade_api_key)
tools = manager.get_tools(tools=["Mytoolkit.SayHello"])

model = ChatOpenAI(
    model="gpt-4o",
    api_key=openai_api_key,
)

bound_model = model.bind_tools(tools)
graph = create_react_agent(model=bound_model, tools=tools)

config = {
    "configurable": {
        "thread_id": "1",
        "user_id": "user@unique_id.com",
    }
}
user_input = {
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful assistant",
        },
        {
            "role": "user",
            "content": "Say hello to Sam",
        },
    ]
}

for chunk in graph.stream(user_input, config, stream_mode="values"):
    chunk["messages"][-1].pretty_print()
```

### Arcade Auth API

The Auth API provides the lowest-level integration with Arcade, for when you only need Arcade's authentication capabilities. This API is ideal for:

-   Framework developers building their own agent systems
-   Applications with existing tool execution mechanisms
-   Developers who need fine-grained control over LLM interactions and tool execution

With the Auth API, Arcade handles all the complex authentication tasks (OAuth flow management, link creation, token storage, refresh cycles), while you retain complete control over how you interact with LLMs and execute tools.

```python
from arcadepy import Arcade
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

client = Arcade()

# Get this user UNIQUE ID from a trusted source,
# like your database or user management system
user_id = "user@example.com"

# Start the authorization process
response = client.auth.start(
    user_id=user_id,
    provider="google",
    scopes=["https://www.googleapis.com/auth/gmail.readonly"],
)

if response.status != "completed":
    print("Please complete the authorization challenge in your browser:")
    print(response.url)

# Wait for the authorization to complete
auth_response = client.auth.wait_for_completion(response)

# Use the authorized token in your own tool execution logic
token = auth_response.context.token

# Example: Using the token with your own Gmail API implementation
credentials = Credentials(token=token)
gmail_service = build('gmail', 'v1', credentials=credentials)
emails = gmail_service.users().messages().list(userId='me').execute()
```

## Client Libraries

-   **[ArcadeAI/arcade-py](https://github.com/ArcadeAI/arcade-py):**
    The Python client for interacting with Arcade.

-   **[ArcadeAI/arcade-js](https://github.com/ArcadeAI/arcade-js):**
    The JavaScript client for interacting with Arcade.

-   **[ArcadeAI/arcade-go](https://github.com/ArcadeAI/arcade-go):** (coming soon)
    The Go client for interacting with Arcade.

## Support and Community

-   **Discord:** Join our [Discord community](https://discord.com/invite/GUZEMpEZ9p) for real-time support and discussions.
-   **GitHub:** Contribute or report issues on the [Arcade GitHub repository](https://github.com/ArcadeAI/arcade-ai).
-   **Documentation:** Find in-depth guides and API references at [Arcade Documentation](https://docs.arcade.dev).
