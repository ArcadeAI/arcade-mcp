<h3 align="center">
  <a name="readme-top"></a>
  <img
    src="https://docs.arcade-ai.com/images/logo/arcade-ai-logo.png"
    height="200"
  >
</h3>
<div align="center">
    <a href="https://github.com/arcadeai/arcade-ai/blob/main/LICENSE">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</a>
    <a href="https://pepy.tech/project/arcade-ai">
  <img src="https://static.pepy.tech/badge/arcade-ai" alt="Downloads">
</a>
<a href="https://github.com/ArcadeAI/arcade-ai/graphs/contributors">
  <img src="https://img.shields.io/github/contributors/arcadeai/arcade-ai.svg" alt="GitHub Contributors">
</a>
<a href="https://arcade-ai.com">
  <img src="https://img.shields.io/badge/Visit_Our_Website-orange" alt="Visit arcade-ai.com">
</a>
</div>
<div>
  <p align="center">
    <a href="https://x.com/TryArcade">
      <img src="https://img.shields.io/badge/Follow%20on%20X-000000?style=for-the-badge&logo=x&logoColor=white" alt="Follow on X" />
    </a>
    <a href="https://www.linkedin.com/company/arcade-ai">
      <img src="https://img.shields.io/badge/Follow%20on%20LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" alt="Follow on LinkedIn" />
    </a>
    <a href="https://discord.com/invite/GUZEMpEZ9p">
      <img src="https://img.shields.io/badge/Join%20our%20Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Join our Discord" />
    </a>
  </p>
</div>

<p align="center">
    <a href="https://docs.arcade-ai.com" target="_blank">Docs</a> •
    <a href="https://docs.arcade-ai.com/integrations" target="_blank">Integrations</a> •
    <a href="https://github.com/ArcadeAI/cookbook" target="_blank">Cookbook</a> •
    <a href="https://github.com/ArcadeAI/arcade-py" target="_blank">Python Client</a> •
    <a href="https://github.com/ArcadeAI/arcade-js" target="_blank">JavaScript Client</a>
</p>

# <img src="https://docs.arcade-ai.com/images/logo/arcadeai-title-dark.png" alt="" width="139.98" height="27.84" style="vertical-align: bottom;" />

Arcade AI empowers any developer to seamlessly integrate large language models (LLMs) with real-world systems, enabling secure, user-authenticated interactions with data and services.

## What is Arcade AI?

[Arcade AI](https://arcade-ai.com?ref=github) bridges the gap between powerful AI models and practical applications by making it easy for developers to build tools that perform real-world actions on behalf of users. With Arcade AI, unlock the true potential of AI in your applications. Check out our [documentation](https://docs.arcade-ai.com).

_Pst. hey, you, join our stargazers! It's free!_

<a href="https://github.com/arcadeai/arcade-ai">
  <img src="https://img.shields.io/github/stars/arcadeai/arcade-ai.svg?style=social&label=Star&maxAge=2592000" alt="GitHub stars">
</a>

## How to use it?

We provide a hosted version of Arcade AI that you can use immediately.

### Requirements
1. A free **[Arcade AI account](https://arcade-ai.com/signup)**
2. **Python 3.10+** verify your Python version by running `python --version` or `python3 --version` in your terminal
3. **pip** the Python package installer that is typically included with Python

### Installation

```bash
pip install 'arcade-ai[fastapi]'
```

```bash
arcade login
```

### Verify Installation

```bash
arcade chat
```

This launches a chat with the Arcade Cloud Engine (hosted at `api.arcade-ai.com`). All pre-built Arcade tools are available to use.

For example, try asking:

```
star the ArcadeAI/arcade-ai repo on Github
```

Arcade AI will ask you to authorize with GitHub, and then the AI assistant will star the [ArcadeAI/arcade-ai](https://github.com/ArcadeAI/arcade-ai) repo on your behalf.

You'll see output similar to this:

```
Assistant (gpt-4o):
I starred the ArcadeAI/arcade-ai repo on Github for you!
```

You can use Ctrl-C to exit the chat at any time.


## Features
Arcade AI integrates with a variety of services to provide a seamless experience for developers and users.

1. **Hosted Tools**: Arcade AI offers a number of prebuilt toolkits that are ready to use out of the box. These toolkits can be used to interact with a variety of services.
1. **Custom Tools**: Developers can build their own tools to integrate with Arcade AI.
1. **Auth Providers**: Arcade AI integrates with a variety of auth providers to enable users to seamlessly and securely allow Arcade AI tools to access their data.


You can find all of Arcade AI's capabilities and how to use them in our [documentation](https://docs.arcade-ai.com).

### Arcade AI Hosted Tools
<img src="https://docs.arcade-ai.com/images/icons/github.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/gmail.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/google_calendar.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/google_docs.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/google_drive.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/serpapi.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/slack.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/web.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/twitter.png" alt="" width="30" height="30" style="vertical-align: top;" />
<br><br>
Arcade AI offers a number of prebuilt toolkits that can be used to interact with a variety of services.

#### Calling tools directly
```python
from arcadepy import Arcade

client = Arcade()

USER_ID = "you@example.com"
TOOL_NAME = "Github.SetStarred"

# Perform User Authorization
auth_response = client.tools.authorize(
    tool_name=TOOL_NAME,
    user_id=USER_ID,
)
if auth_response.status != "completed":
    print(f"Click this link to authorize: {auth_response.auth_url}")
    input("After you have authorized, press Enter to continue...")

# Run the tool
inputs = {"owner": "ArcadeAI", "name": "Hello-World", "starred": True}
response = client.tools.run(
    tool_name=TOOL_NAME,
    inputs=inputs,
    user_id=USER_ID,
)
print(response)

```

#### Calling tools with the LLM API
```python
import os
from openai import OpenAI

USER_ID = "you@example.com"
PROMPT = "Star the ArcadeAI/arcade-ai repository."
TOOL_NAME = "Github.SetStarred"
# Use "generate" to have the LLM generate a response after the tool executes. Use 'execute' to get the tool's output directly.
TOOL_CHOICE = "generate"

client = OpenAI(
    base_url="https://api.arcade-ai.com",
    api_key=os.environ.get("ARCADE_API_KEY"))

response = client.chat.completions.create(
    messages=[
        {"role": "user", "content": PROMPT},
    ],
    model="gpt-4o-mini",
    user=USER_ID,
    tools=[TOOL_NAME],
    tool_choice=TOOL_CHOICE,
)
print(response.choices[0].message.content)
```

### Building Your Own Tools

Learn how to build your own tools by following our [creating a custom toolkit guide](https://docs.arcade-ai.com/tools/overview).

### Evaluating Tools

Arcade AI enables you to evaluate your custom tools to ensure they function correctly with the AI assistant, including defining evaluation cases and using different critics.

Learn how to evaluate your tools by following our [evaluating tools guide](https://docs.arcade-ai.com/home/evaluate-tools/create-an-evaluation-suite).

### Auth
<img src="https://docs.arcade-ai.com/images/icons/github.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/google.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/linkedin.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/msft.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/slack.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/spotify.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/twitter.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/zoom.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/oauth2.png" alt="" width="30" height="30" style="vertical-align: top;" />
<br><br>

Learn how to use Arcade AI to obtain user authorization for accessing third-party services in our [authorizing agents with Arcade AI guide](https://docs.arcade-ai.com/home/get-a-token-for-a-user).

Learn how to use Arcade AI's auth providers to enable tools and agents to call other services on behalf of users in our [tools with auth guide](https://docs.arcade-ai.com/home/build-tools/create-a-tool-with-auth).

To see all available auth providers, refer to the [auth providers documentation](https://docs.arcade-ai.com/integrations).

### Models
<img src="https://docs.arcade-ai.com/images/icons/openai.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/anthropic.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/ollama.png" alt="" width="30" height="30" style="vertical-align: top;" /><img src="https://docs.arcade-ai.com/images/icons/groq.png" alt="" width="30" height="30" style="vertical-align: top;" />
<br><br>
Arcade AI supports a variety of model providers when using the Arcade AI LLM API.

To see all available models, refer to the [models documentation](https://docs.arcade-ai.com/integrations/models/openai).

## Contributing

We love contributions! Please read our [contributing guide](CONTRIBUTING.md) before submitting a pull request. If you'd like to self-host, refer to the [self-hosting documentation](https://docs.arcade-ai.com/home/install/overview).

## Contributors

<a href="https://github.com/ArcadeAI/arcade-ai/graphs/contributors">
  <img alt="contributors" src="https://contrib.rocks/image?repo=ArcadeAI/arcade-ai"/>
</a>

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
    <a href="#readme-top" style="text-decoration: none; color: #007bff; font-weight: bold;">
        ↑ Back to Top ↑
    </a>
</p>
