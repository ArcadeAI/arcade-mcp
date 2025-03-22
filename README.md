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

-   [Quickstart: Install and call a tool](#quickstart-install-and-call-a-tool)
-   [Build LLM Tools with Arcade SDK](#build-llm-tools-with-arcade-sdk)
    -   [Tool SDK Installation](#tool-sdk-installation)
    -   [Creating a new Toolkit](#creating-a-new-toolkit)
    -   [Deploy your tools to call with LLMs](#deploy-your-tools-to-call-with-llms)
-   [Calling your tools](#calling-your-tools)
    -   [LLM API](#llm-api)
    -   [Tools API](#tools-api)
    -   [Integrating with Agent Frameworks](#integrating-with-agent-frameworks)
    -   [Arcade Auth API](#arcade-auth-api)
-   [Client Libraries](#client-libraries)
-   [Support and Community](#support-and-community)

## Quickstart: Install and call a tool

```bash
# Install the Arcade CLI
pip install arcade-ai

# Log in to Arcade
arcade login

# Show what tools are hosted by Arcade
arcade show

# show what tools are in a toolkit
arcade show -T GitHub

# look at the definition of a tool
arcade show -t GitHub.SetStarred
```

The GitHub.SetStarred tool is hosted by Arcade, so you can call it directly
without any additional setup of OAuth or servers. A simple way to test tools,
wether hosted by Arcade or not, is to use the `arcade chat` app.

```bash
arcade chat
```

This will start a chat with an LLM that can call tools.

try calling the GitHub.SetStarred tool with a message like "Star the arcade-ai repo"

```
> arcade chat

=== Arcade Chat ===

Chatting with Arcade Engine at https://api.arcade.dev

User sam@arcade.dev:
star the arcadeai/arcade-ai repo

Assistant:
Thanks for authorizing the action! Sending your request...

Assistant:
I have successfully starred the repository arcadeai/arcade-ai for you.
```

If Arcade already hosts the tools you need to build your agent, you
can navigate to the [Quickstart](https://docs.arcade.dev/home/quickstart) to
learn how to call tools programmatically in Python, Typescript, or HTTP.

You can also build your own tools with the SDK and deploy them in one command
on Arcade Cloud

## Build LLM Tools with Arcade SDK

Arcade provides a tool SDK that allows you to build your own tools and use them in your agentic applications just like the existing tools Arcade provides. This is useful for building new tools, customizing existing tools to fit your needs, combining multiple tools, or building tools that are not yet supported by Arcade.

### Tool SDK Installation

**Prerequisites**

-   **Python 3.10+** and **pip**

Now you can install the Tool SDK through pip.

1. **Install the Arcade CLI:**

    ```bash
    pip install arcade-ai
    ```

    If you plan on writing evaluations for your tools and the LLMs you use, you will also need to install the `evals` extra.

    ```bash
    pip install 'arcade-ai[evals]'
    ```

2. **Log in to Arcade:**
    ```bash
    arcade login
    ```
    This will prompt you to open a browser and authorize the CLI. It will then save the credentials to your machine typically in `~/.arcade/credentials.json`. If you haven't used the CLI before, you will need to create an account on this page.

Now you're ready to build tools with Arcade!

### Creating a New Toolkit

Toolkits are the main building blocks of Arcade. They are a collection of tools that are related to a specific service, use case,
or agent. Toolkits are created and distributed python packages to facilitate version, dependency, and distribution.

To create a new toolkit, you can use the `arcade new` command. This will create a new toolkit in the current directory.

1. **Generate a new toolkit template:**

    ```bash
    arcade new
    ```

    ```text
    Name of the new toolkit?: mytoolkit
    Description of the toolkit?: myToolkit is a toolkit for ...
    Github owner username?: mytoolkit
    Author's email?: user@example.com
    ```

    This will create a new toolkit in the current directory.

    The generated toolkit includes all the scaffolding you need for a working tool. Look for the `mytoolkit/tool.py` file to customize the behavior of your tool.

2. **Install your new toolkit:**

    ```bash
    # make sure you have python installed
    python --version

    # install your new toolkit
    cd mytoolkit
    make install
    ```

    This will install the toolkit in your local python environment using poetry.

    The template is meant to be customized so feel free to change anything about the structure,
    package management, linting, etc.

4. **Show the tools in the template Toolkit:**

    ```bash
    # show the tools in Mytoolkit
    arcade show --local -T Mytoolkit

    # show the definition of a tool
    arcade show --local -t Mytoolkit.SayHello

    # show all tools installed in your local python environment
    arcade show --local
    ```

Now you can edit the `mytoolkit/tool.py` file to customize the behavior of your tool. Next,
you can host your tools to call with LLMs by deploying your toolkit to Arcade Cloud.

### Deploy your tools to call with LLMs

To make your tools in the toolkit available to call with LLMs, you can deploy your toolkit to Arcade Cloud.

The `worker.toml` file created in the directory where you ran `arcade new` will be used to deploy your toolkit.

In that directory, run the following command to deploy your toolkit:

```bash
# from inside the mytoolkit dir
cd ../

arcade deploy
```

This command will package your toolkit and deploy it as a worker instance in Arcade's cloud infrastructure:

```
[11:52:44] Deploying 'demo-worker...'
⠦ Deploying 1 workers             Changed Packages
┏━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Added    ┃ Removed ┃ Updated ┃ No Changes ┃
┡━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━┩
│ Mytoolkit│         │         │            │
└──────────┴─────────┴─────────┴────────────┘
[11:53:13] ✅ Worker 'demo-worker' deployed successfully.
```

You can manage your deployed workers with the following commands:

```bash
# List all workers (both local and cloud-deployed)
arcade worker list

# Remove a deployed worker
arcade worker rm demo-worker
```

Once deployed, your toolkit is immediately available through the Arcade platform. You can now call your tools through the playground, LLM API, or Tools API without any additional setup.

For local development and testing when running the Arcade Engine locally or tunneling to it, you can
use `arcade serve` to host your toolkit locally and connect it to the Arcade Engine.

If you are running the Arcade Engine locally, go to localhost:9099 (or other local address)
and add the worker address in the "workers" page.

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
