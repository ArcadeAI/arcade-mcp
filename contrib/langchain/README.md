<div align="center">

<img width="400px" src="https://docs-112.pages.dev/images/logo/arcade-ai-logo.png" />

### LLM Tool Calling Platform

<p>
<img alt="GitHub Last Commit" src="https://img.shields.io/github/last-commit/arcadeai/arcade-ai" />
<img alt="GitHub Issues" src="https://img.shields.io/github/issues/arcadeai/arcade-ai" />
<img alt="GitHub Pull Requests" src="https://img.shields.io/github/issues-pr/arcadeai/arcade-ai" />
<img alt="GitHub License" src="https://img.shields.io/badge/License-MIT-yellow.svg" />
<img alt="Discord" src="https://img.shields.io/discord/1110910277110743103?label=Discord&logo=discord&logoColor=white&style=plastic&color=d7b023)](https://discord.gg/" />
</p>

---

<p align="center">
  <a href="https://docs-112.pages.dev" target="_blank">Docs</a> •
  <a href="https://docs-112.pages.dev/guides" target="_blank">Guides</a> •
  <a href="https://docs-112.pages.dev/integrations" target="_blank">Integrations</a> •
  <a href="https://discord.com/invite/" target="_blank">Discord</a>

</p>

<br />

</div>

Arcade AI is the developer platform for building tools designed to be used with language models. With Arcade, developers can create, deploy, and easily integrate new tools with language models to enhance their capabilities.

## Setup

Follow [these instructions](https://docs-112.pages.dev/home/quickstart) to Install Arcade AI and create an API key.

This example is using OpenAI, as the LLM provider. Ensure you have an [OpenAI API key](https://platform.openai.com/docs/quickstart).

Copy the `.env.example` file to `.env` and supply your API keys for `OPENAI_API_KEY` and `ARCADE_API_KEY`.

## Usage with LangGraph API

### Local testing with LangGraph Studio

For testing locally (e.g., currently supported only on MacOS), you can use the LangGraph Studio desktop application.

[Download LangGraph Studio](https://github.com/langchain-ai/langgraph-studio?tab=readme-ov-file#download) and open this directory in the Studio application.

The `langgraph.json` file in this directory specifies the graph that will be loaded in Studio.

### Deploying to LangGraph Cloud

Follow [these instructions](https://langchain-ai.github.io/langgraph/cloud/quick_start/#deploy-to-cloud) to deploy your graph to LangGraph Cloud.
