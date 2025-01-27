## Setup

### API keys

Follow [these instructions](https://docs.arcade.dev/home/custom-tools/) to Install Arcade and create an API key.

This example is using OpenAI, as the LLM provider. Ensure you have an [OpenAI API key](https://platform.openai.com/docs/quickstart).

### Environment variables

Copy the `env.example` file to `.env` and supply your API keys for **at least** `OPENAI_API_KEY` and `ARCADE_API_KEY`.

## Usage with LangGraph API

### Local testing with LangGraph Studio

For testing locally (e.g., currently supported only on MacOS), you can use the LangGraph Studio desktop application.

[Download LangGraph Studio](https://github.com/langchain-ai/langgraph-studio?tab=readme-ov-file#download) and open this directory in the Studio application.

The `langgraph.json` file in this directory specifies the graph that will be loaded in Studio.

### Deploying to LangGraph Cloud

Follow [these instructions](https://langchain-ai.github.io/langgraph/cloud/quick_start/#deploy-to-cloud) to deploy your graph to LangGraph Cloud.
