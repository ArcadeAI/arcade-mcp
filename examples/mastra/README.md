<h3 align="center">
  <a name="readme-top"></a>
  <img
    src="https://docs.arcade.dev/images/logo/arcade-logo.png"
  >
</h3>
<div align="center">
  <h3>Arcade - Mastra Example</h3>
    <a href="https://github.com/your-organization/agents-arcade/blob/main/LICENSE">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</a>
<p align="center">
    <a href="https://docs.arcade.dev" target="_blank">Arcade Documentation</a> •
    <a href="https://docs.arcade.dev/toolkits" target="_blank">Integrations</a> •
    <a href="https://github.com/ArcadeAI/arcade-js" target="_blank">Arcade JS Client</a> •
    <a href="https://github.com/mastra-ai/mastra" target="_blank">Mastra</a>
</p>
</div>

# Arcade - Mastra Integration

This example demonstrates how to integrate [Arcade](https://docs.arcade.dev) with [Mastra](https://mastra.ai/en/docs) to create powerful AI agents. Arcade provides access to a wide range of tools including Gmail, Slack, LinkedIn, and more, while Mastra provides a robust framework for building AI agents with TypeScript.

For a list of all available tools and authentication options, see the [Arcade Integrations](https://docs.arcade.dev/toolkits) documentation. You can also build custom tools with the [Tool SDK](https://github.com/ArcadeAI/arcade-ai) as described in our [documentation](https://docs.arcade.dev/home/build-tools/create-a-toolkit).

## Prerequisites

- [Node.js](https://nodejs.org/en/download/) (v20.0 or higher)
- [pnpm](https://pnpm.io/installation) (v9.15.9 or higher)
- [OpenAI API key](https://platform.openai.com/account/api-keys)
- [Arcade API key](https://docs.arcade.dev/home/api-keys)

## Installation

1. Install dependencies:

```bash
pnpm install
```

2. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Fill in your API keys:

     ```
     OPENAI_API_KEY=your_openai_api_key
     ARCADE_API_KEY=your_arcade_api_key
     ```

## Basic Usage

This example demonstrates how to use Arcade's Google toolkit with Mastra to create an AI agent that can help users manage their Google services (Gmail, Calendar, Sheets, Drive, and Contacts). The agent will access your Google account (after authorization) and perform various tasks based on user requests.

To get started:

1. Start the Mastra playground:

```bash
pnpm dev
```

2. Open your browser and navigate to <http://localhost:4111/>

The Mastra playground provides an interactive interface where you can:

- Chat with your agent
- Execute specific tools

## Authorization

When using tools that require authorization, the agent will provide an authorization URL. You'll need to:

1. Click on the authorization URL provided in the chat/execution interface
2. Complete the authorization flow in your browser
3. Return to the Mastra playground to continue your interaction

This authorization process is handled by the `executeOrAuthorizeZodTool` helper function, which checks if a tool requires authorization and returns the appropriate URL when needed. Once authorized, the tool will execute normally in subsequent requests without requiring re-authorization.

## Development

To modify or extend the functionality:

1. Update the `userId` in `agents/google.ts` with your application's user identification
2. Modify the `toolkit` parameter in `arcade.tools.list()` to access different tools. Available toolkits include:
   - `"google"` - Gmail, Google Calendar, Google Drive
   - `"slack"` - Slack messaging and channels
   - `"github"` - GitHub repositories and issues
   - And more in [Arcade Integrations](https://docs.arcade.dev/toolkits) documentation

## Security

- Never commit your `.env` file
- Use appropriate user identification in production

## License

This project is licensed under the MIT License - see the LICENSE file for details.
