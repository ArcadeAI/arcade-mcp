<h3 align="center">
  <a name="readme-top"></a>
  <img
    src="https://docs.arcade.dev/images/logo/arcade-ai-logo.png"
    style="width: 400px;"
  >
</h3>
<div align="center">
    <a href="https://github.com/arcadeai/arcade-ai/blob/main/LICENSE">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</a>
    <a href="https://pepy.tech/project/arcade-ai">
  <img src="https://static.pepy.tech/badge/arcade-ai" alt="Downloads">
</a>
  <img src="https://img.shields.io/github/last-commit/ArcadeAI/arcade-ai" alt="GitHub last commit">
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
    <a href="https://docs.arcade.dev/home" target="_blank">Docs</a> •
    <a href="https://docs.arcade.dev/toolkits" target="_blank">Toolkits</a> •
    <a href="https://docs.arcade.dev/supported-models" target="_blank">Model Providers</a> •
    <a href="https://docs.arcade.dev/auth-providers" target="_blank">Auth Providers</a> •
    <a href="https://github.com/ArcadeAI/arcade-ai/tree/main/examples" target="_blank">Examples</a>

## What is Arcade?

[Arcade](https://arcade.dev?ref=github) provides developer-focused tooling and APIs designed to improve the capabilities of LLM applications and agents.

By removing the complexity of connecting agentic applications with your users' data and services, Arcade enables developers to focus on building their agentic applications.

To learn more, check out our [documentation](https://docs.arcade.dev/home).

_Pst. hey, you, give us a star if you like it!_

<a href="https://github.com/ArcadeAI/arcade-ai">
  <img src="https://img.shields.io/github/stars/ArcadeAI/arcade-ai.svg?style=social&label=Star&maxAge=2592000" alt="GitHub stars">
</a>

## Quickstart

### Requirements

1. An **[Arcade account]([https://arcade-ai.typeform.com/early-access](https://account.arcade.dev/registerOrRedirect?return_to=https%3A%2F%2Fapi.arcade.dev%2Fdashboard&new_user_return_to=https%3A%2F%2Fapi.arcade.dev%2Fdashboard%2Fwelcome))**
2. **Python 3.10+** and **pip**

### Installation

Install the package:

```bash
pip install arcade-ai
```

Log in to your account via the CLI:

```bash
arcade login
```

This opens a browser window for authentication.

### Verify Installation with `arcade chat`

Use the `arcade chat` CLI app to test tools:

```bash
arcade chat
```

This connects to the Arcade Cloud Engine (`api.arcade.dev`) with all pre-built Arcade tools.

For example, try:

```text
User (dev@arcade.dev):
> star the ArcadeAI/arcade-ai repo on Github
```

Arcade will prompt you to authorize with GitHub and will star the [ArcadeAI/arcade-ai](https://github.com/ArcadeAI/arcade-ai) repo on your behalf.

You'll see:

```text
Assistant (gpt-4o):
I starred the ArcadeAI/arcade-ai repo on Github for you!
```

Press `Ctrl-C` to exit the chat.

## Arcade Cloud

Arcade Cloud is a hosted version of the Arcade engine that hosts a number of prebuilt toolkits for interacting with a variety of services.

### Prebuilt Toolkits

Arcade offers a number of prebuilt toolkits that can be used by agents to interact with a variety of services.

<table>
  <thead>
    <tr>
      <th style="text-align: center;">Service</th>
      <th style="text-align: center;">Auth Type</th>
      <th style="text-align: center;">Toolkit</th>
      <th style="text-align: center;">Documentation</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/github.png" alt="GitHub" width="30" /></td>
      <td style="text-align: center;">OAuth</td>
      <td style="text-align: center;"><a href="https://github.com/ArcadeAI/arcade-ai/tree/main/toolkits/github">Github</a></td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/toolkits/development/github/github">GitHub Toolkit Docs</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/gmail.png" alt="Gmail" width="30" /></td>
      <td style="text-align: center;">OAuth</td>
      <td style="text-align: center;"><a href="https://github.com/ArcadeAI/arcade-ai/tree/main/toolkits/google/arcade_google/tools/gmail">Google</a></td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/toolkits/productivity/google/gmail">Gmail Toolkit Docs</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/google_calendar.png" alt="Google Calendar" width="30" /></td>
      <td style="text-align: center;">OAuth</td>
      <td style="text-align: center;"><a href="https://github.com/ArcadeAI/arcade-ai/tree/main/toolkits/google/arcade_google/tools/calendar">Google</a></td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/toolkits/productivity/google/calendar">Google Calendar Toolkit Docs</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/google_docs.png" alt="Google Docs" width="30" /></td>
      <td style="text-align: center;">OAuth</td>
      <td style="text-align: center;"><a href="https://github.com/ArcadeAI/arcade-ai/tree/main/toolkits/google/arcade_google/tools/docs">Google</a></td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/toolkits/productivity/google/docs">Google Docs Toolkit Docs</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/google_drive.png" alt="Google Drive" width="30" /></td>
      <td style="text-align: center;">OAuth</td>
      <td style="text-align: center;"><a href="https://github.com/ArcadeAI/arcade-ai/tree/main/toolkits/google/arcade_google/tools/drive">Google</a></td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/toolkits/productivity/google/drive">Google Drive Toolkit Docs</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/serpapi.png" alt="Search" width="30" /></td>
      <td style="text-align: center;">API Key</td>
      <td style="text-align: center;"><a href="https://github.com/ArcadeAI/arcade-ai/tree/main/toolkits/search">Search</a></td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/toolkits/development/search">Search Toolkit Docs</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/slack.png" alt="Slack" width="30" /></td>
      <td style="text-align: center;">OAuth</td>
      <td style="text-align: center;"><a href="https://github.com/ArcadeAI/arcade-ai/tree/main/toolkits/slack">Slack</a></td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/toolkits/social-communication/slack">Slack Toolkit Docs</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/spotify.png" alt="Spotify" width="30" /></td>
      <td style="text-align: center;">OAuth</td>
      <td style="text-align: center;"><a href="https://github.com/ArcadeAI/arcade-ai/tree/main/toolkits/spotify">Spotify</a></td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/toolkits/entertainment/spotify">Spotify Toolkit Docs</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/web.png" alt="Web" width="30" /></td>
      <td style="text-align: center;">API Key</td>
      <td style="text-align: center;"><a href="https://github.com/ArcadeAI/arcade-ai/tree/main/toolkits/web">Web</a></td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/toolkits/development/web/web">Web Toolkit Docs</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/twitter.png" alt="Twitter" width="30" /></td>
      <td style="text-align: center;">OAuth</td>
      <td style="text-align: center;"><a href="https://github.com/ArcadeAI/arcade-ai/tree/main/toolkits/x">X</a></td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/toolkits/social-communication/x">X Toolkit Docs</a></td>
    </tr>
  </tbody>
</table>

<br>

### Supported Auth Providers

<table>
  <thead>
    <tr>
      <th style="text-align: center;">Provider</th>
      <th style="text-align: center;">Name</th>
      <th style="text-align: center;">Documentation</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/github.png" alt="GitHub" width="30" /></td>
      <td style="text-align: center;">github</td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/home/auth-providers/github">GitHub Auth Docs</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/google.png" alt="Google" width="30" /></td>
      <td style="text-align: center;">google</td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/home/auth-providers/google">Google Auth Docs</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/linkedin.png" alt="LinkedIn" width="30" /></td>
      <td style="text-align: center;">linkedin</td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/home/auth-providers/linkedin">LinkedIn Auth Docs</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/msft.png" alt="Microsoft" width="30" /></td>
      <td style="text-align: center;">microsoft</td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/home/auth-providers/microsoft">Microsoft Auth Docs</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/slack.png" alt="Slack" width="30" /></td>
      <td style="text-align: center;">slack</td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/home/auth-providers/slack">Slack Auth Docs</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/spotify.png" alt="Spotify" width="30" /></td>
      <td style="text-align: center;">spotify</td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/home/auth-providers/spotify">Spotify Auth Docs</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/twitter.png" alt="X" width="30" /></td>
      <td style="text-align: center;">x</td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/home/auth-providers/x">X Auth Docs</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/zoom.png" alt="Zoom" width="30" /></td>
      <td style="text-align: center;">zoom</td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/home/auth-providers/zoom">Zoom Auth Docs</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="https://docs.arcade.dev/images/icons/oauth2.png" alt="OAuth 2.0" width="30" /></td>
      <td style="text-align: center;">oauth2</td>
      <td style="text-align: center;"><a href="https://docs.arcade.dev/home/auth-providers/oauth2">Generic OAuth2 Auth Docs</a></td>
    </tr>
  </tbody>
</table>

### Supported Language Models

The LLM API supports a variety of language models. Currently, the ones supported in Arcade Cloud are OpenAI, Anthropic, Ollama, and Groq.

<table>
  <thead>
    <tr>
      <th style="text-align: center;">Model</th>
      <th style="text-align: center;">Provider</th>
      <th style="text-align: center;">Documentation</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="text-align: center;">
        <img src="https://docs.arcade.dev/images/icons/openai.png" alt="OpenAI" width="30" height="30" />
      </td>
      <td style="text-align: center;">OpenAI</td>
      <td style="text-align: center;">
        <a href="https://docs.arcade.dev/home/supported-models/openai">OpenAI Models Docs</a>
      </td>
    </tr>
    <tr>
      <td style="text-align: center;">
        <img src="https://docs.arcade.dev/images/icons/anthropic.png" alt="Anthropic" width="30" height="30" />
      </td>
      <td style="text-align: center;">Anthropic</td>
      <td style="text-align: center;">
        <a href="https://docs.arcade.dev/home/supported-models/anthropic">Anthropic Models Docs</a>
      </td>
    </tr>
    <tr>
      <td style="text-align: center;">
        <img src="https://docs.arcade.dev/images/icons/ollama.png" alt="Ollama" width="30" height="30" />
      </td>
      <td style="text-align: center;">Ollama</td>
      <td style="text-align: center;">
        <a href="https://docs.arcade.dev/home/supported-models/ollama">Ollama Models Docs</a>
      </td>
    </tr>
    <tr>
      <td style="text-align: center;">
        <img src="https://docs.arcade.dev/images/icons/groq.png" alt="Groq" width="30" height="30" />
      </td>
      <td style="text-align: center;">Groq</td>
      <td style="text-align: center;">
        <a href="https://docs.arcade.dev/home/supported-models/groq">Groq Models Docs</a>
      </td>
    </tr>
  </tbody>
</table>

For more information, refer to the [supported models documentation](https://docs.arcade.dev/home/supported-models).

### Get Started with Arcade

To get started with Arcade, check out our [quickstart guide](https://docs.arcade.dev/home/quickstart).

### Building Your Own Tools

Learn how to build your own tools by following our [creating a custom toolkit guide](https://docs.arcade.dev/home/build-tools/create-a-toolkit).

### Evaluating Tools

Arcade enables you to evaluate your custom tools to ensure they function correctly with the AI assistant, including defining evaluation cases and using different critics.

Learn how to evaluate your tools by following our [evaluating tools guide](https://docs.arcade.dev/home/evaluate-tools/create-an-evaluation-suite).

## Contributing

We love contributions! Please read our [contributing guide](CONTRIBUTING.md) before submitting a pull request. If you'd like to self-host, refer to the [self-hosting documentation](https://docs.arcade.dev/home/install/overview).

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
    <a href="#readme-top" style="text-decoration: none; color: #007bff; font-weight: bold;">
        ↑ Back to Top ↑
    </a>
</p>
