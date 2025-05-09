<h3 align="center">
  <a name="readme-top"></a>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ArcadeAI/.github/refs/heads/main/profile/assets/new_arcade_logo_white.svg" width="300">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/ArcadeAI/.github/refs/heads/main/profile/assets/new_arcade_logo_black.svg" width="300">
    <img alt="Fallback image description" src="https://raw.githubusercontent.com/ArcadeAI/.github/refs/heads/main/profile/assets/new_arcade_logo_black.svg" width="300" >
  </picture>
</h3>
<div align="center">
  <h3>Arcade AI SDK Example</h3>
    <a href="https://github.com/your-organization/agents-arcade/blob/main/LICENSE">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">

</a>
<p align="center">
    <a href="https://docs.arcade.dev" target="_blank">Arcade Documentation</a> •
    <a href="https://docs.arcade.dev/toolkits" target="_blank">Integrations</a> •
    <a href="https://github.com/ArcadeAI/arcade-js" target="_blank">Arcade JS Client</a> •
    <a href="https://sdk.vercel.ai/" target="_blank">AI SDK</a>
</p>
</div>

# Arcade - AI SDK

This example demonstrates how to integrate [Arcade](https://docs.arcade.dev) with the [Vercel AI SDK](https://sdk.vercel.ai/) to create powerful AI agents. Arcade provides access to a wide range of tools including Gmail, Slack, LinkedIn, and more. You can also develop custom tools using the [Tool SDK](https://github.com/ArcadeAI/arcade-ai).

For a list of all hosted tools and auth providers, see the [Arcade Integrations](https://docs.arcade.dev/toolkits) documentation.

## Prerequisites

- [Node.js](<https://nodejs.org/en/download/>) (v18.20.8 or higher)
- [pnpm](<https://pnpm.io/installation>) (v9.15.9 or higher)
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

This example demonstrates how to use Arcade's Google toolkit to create an AI agent that can read and summarize emails. The agent will access your Gmail account (after authorization) and process your most recent email.

To get started, run the development server:

```bash
pnpm dev
```

If you haven't authorized Arcade with Google yet, you'll see a message like this:

```bash
> pnpm dev
Authorization Required: Please visit this link to connect your Google account: https://accounts.google.com/o/oauth2/v2/auth?access_type=offline&client_id=....
```

Visit the provided URL in your browser to authorize Arcade with Google. Once authorized, run the script again.

You can also wait for authorization to complete before running the script using the helper methods in arcade.js.

Once you've authorized Arcade with a tool, you can use it in your agent by passing the user_id and won't need to authenticate for that specific tool again.

## Development

To modify or extend the functionality:

1. Update the `USER_ID` constant in `index.js` with your application's user identification
2. Modify the `toolkit` parameter in `getArcadeTools` to access different tools. Available toolkits include:
   - `"google"` - Gmail, Google Calendar, Google Drive
   - `"slack"` - Slack messaging and channels
   - `"github"` - GitHub repositories and issues
   - And more in [Arcade Integrations](https://docs.arcade.dev/toolkits) documentation

## Security

- Never commit your `.env` file
- Keep your API keys secure
- Use appropriate user identification in production

## License

This project is licensed under the MIT License - see the LICENSE file for details.
