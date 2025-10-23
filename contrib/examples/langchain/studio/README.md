## Setup

### Environment

Copy the `env.example` file to `.env` and supply your API keys for **at least** `OPENAI_API_KEY` and `ARCADE_API_KEY`.

-   Arcade API key: `ARCADE_API_KEY` (instructions [here](https://docs.arcade.dev/home/api-keys))
-   OpenAI API key: `OPENAI_API_KEY` (instructions [here](https://platform.openai.com/docs/quickstart))

## Usage with LangGraph API

### Local testing with LangGraph Studio

[Download LangGraph Studio](https://github.com/langchain-ai/langgraph-studio?tab=readme-ov-file#download) and open this directory in the Studio application.

The `langgraph.json` file in this directory specifies the graph that will be loaded in Studio.

### Deploying to LangGraph Cloud

Follow [these instructions](https://langchain-ai.github.io/langgraph/cloud/quick_start/#deploy-to-cloud) to deploy your graph to LangGraph Cloud.
