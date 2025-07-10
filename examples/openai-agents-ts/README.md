<h3 align="center">
  <a name="readme-top"></a>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ArcadeAI/.github/refs/heads/main/profile/assets/new_arcade_logo_white.svg" width="300">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/ArcadeAI/.github/refs/heads/main/profile/assets/new_arcade_logo_black.svg" width="300">
    <img alt="Arcade AI Logo" src="https://raw.githubusercontent.com/ArcadeAI/.github/refs/heads/main/profile/assets/new_arcade_logo_black.svg" width="300" >
  </picture>
</h3>
<div align="center">
  <h3>OpenAI Agents + Arcade AI Example</h3>
    <a href="https://github.com/your-organization/openai-ts/blob/main/LICENSE">
  <img src="https://img.shields.io/badge/License-ISC-blue.svg" alt="License">
</a>
<p align="center">
    <a href="https://docs.arcade.dev" target="_blank">Arcade Documentation</a> •
    <a href="https://docs.arcade.dev/toolkits" target="_blank">Integrations</a> •
    <a href="https://github.com/ArcadeAI/arcade-js" target="_blank">Arcade JS Client</a> •
    <a href="https://platform.openai.com/docs/assistants/tools" target="_blank">OpenAI Agents</a>
</p>
</div>

# OpenAI Agents + Arcade AI

This TypeScript project demonstrates how to integrate [Arcade AI](https://docs.arcade.dev) with [OpenAI Agents](https://openai.github.io/openai-agents-js/) to create powerful AI agents that can interact with external services. Arcade provides access to a wide range of tools including Gmail, Slack, LinkedIn, and more through its Google toolkit and other integrations.

The project showcases two approaches:

- **Basic integration** (`src/index.ts`): Simple one-time execution with Google toolkit
- **Authorization handling** (`src/waitForCompletion.ts`): Manual authorization flow management

For a list of all hosted tools and auth providers, see the [Arcade Integrations](https://docs.arcade.dev/toolkits) documentation.

## Prerequisites

- [Node.js](https://nodejs.org/en/download/) (v18.20.8 or higher)
- [npm](https://www.npmjs.com/) or [pnpm](https://pnpm.io/installation)
- [OpenAI API key](https://platform.openai.com/account/api-keys)
- [Arcade API key](https://docs.arcade.dev/home/api-keys)

## Installation

1. Clone the repository and install dependencies:

```bash
npm install
```

2. Set up environment variables:
   - Create a `.env` file in the root directory
   - Add your API keys:

     ```
     OPENAI_API_KEY=your_openai_api_key
     ARCADE_API_KEY=your_arcade_api_key
     ```

3. Update the user ID placeholder:
   - In both `src/index.ts` and `src/waitForCompletion.ts`
   - Replace `<YOUR_SYSTEM_USER_ID>` with your application's user identifier (e.g., email address, UUID, etc.)

## Basic Usage

This example creates an AI agent that can read and process your Gmail emails using Arcade's Google toolkit.

### Simple Execution

Run the basic example:

```bash
npm run dev
```

This script will:

1. Initialize the Arcade client
2. Fetch available Google toolkit tools (up to 30)
3. Convert them to OpenAI Agents compatible format
4. Create an agent that can assist with Google API calls
5. Ask "What are my latest emails?" and display the result

### Authorization Flow Example

For a more robust implementation that handles authorization flows:

```bash
npm run dev:waitForCompletion
```

This version includes:

- Automatic authorization detection and handling
- Browser-based OAuth flow initiation
- Waiting for authorization completion
- Automatic retry after successful authorization

If you haven't authorized Arcade with Google yet, you'll see a message like:

```bash
Please complete the authorization challenge in your browser: https://accounts.google.com/o/oauth2/v2/auth?access_type=offline&client_id=...
```

Visit the provided URL to authorize Arcade with your Google account. The script will automatically detect when authorization is complete and continue execution.

## Project Structure

```
openai-ts/
├── src/
│   ├── index.ts              # Basic OpenAI Agents + Arcade integration
│   └── waitForCompletion.ts  # Manual authorization flow management
├── package.json              # Dependencies and scripts
└── README.md                 # This file
```

## Available Toolkits

You can modify the `toolkit` parameter to access different integrations:

- `"google"` - Gmail, Google Calendar, Google Drive, Google Docs
- `"slack"` - Slack messaging and channels
- `"github"` - GitHub repositories and issues
- `"linkedin"` - LinkedIn posts and connections
- And more in [Arcade Integrations](https://docs.arcade.dev/toolkits) documentation

## Development

To extend or modify the functionality:

1. **Change the toolkit**: Update the `toolkit` parameter in the `client.tools.list()` call
2. **Modify the query**: Change the question asked to the agent in the `run()` function
3. **Add custom instructions**: Update the agent's `instructions` parameter for different behaviors
4. **Handle different models**: Switch the `model` parameter to use different OpenAI models

Example customization:

```typescript
const slackToolkit = await client.tools.list({ toolkit: "slack", limit: 30 });
// ... rest of setup

const slackAgent = new Agent({
  name: "Slack agent",
  instructions: "You are a helpful assistant for managing Slack communications.",
  model: "gpt-4o",
  tools
});

const result = await run(slackAgent, "Send a message to the #general channel");
```

## Security Best Practices

- Never commit your `.env` file to version control
- Keep your API keys secure and rotate them regularly
- Use appropriate user identification in production

## License

This project is licensed under the MIT License - see the LICENSE file for details.
