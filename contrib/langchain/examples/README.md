# LangChain-Arcade Examples

Examples demonstrating the integration between [Arcade AI](https://arcade.dev) tools and [LangChain](https://langchain.com)/[DeepAgents](https://github.com/langchain-ai/deepagents).

## Research Agent

An AI agent that researches topics, creates Google Docs reports, and emails them to you.

> **Note:** This example requires **Python 3.11+** (deepagents requirement).

### Features

- 🔬 **End-to-end research workflow** - Research → Create Doc → Email
- 🔐 **Just-in-time OAuth** - Automatic authorization when tools need access
- 📄 **Creates real Google Docs** - Reports saved to your Google Drive
- 📧 **Sends via Gmail** - Delivers report link to your inbox
- 🤖 **Powered by DeepAgents** - Uses LangChain's deep agent framework

### Setup

#### 1. Install Dependencies

```bash
cd contrib/langchain
pip install -e ".[dev]"
```

#### 2. Configure Environment

```bash
cd examples
cp env.example .env
```

Edit `.env` with your credentials:

```env
# Get your Arcade API key at https://arcade.dev
ARCADE_API_KEY=arc_your_key_here

# OpenAI or Anthropic API key
OPENAI_API_KEY=sk-your_key_here

# Your email (used for OAuth authorization)
USER_EMAIL=your-email@gmail.com

# Email to receive research reports
RECIPIENT_EMAIL=recipient@example.com
```

### Running the Agent

#### Interactive Mode

```bash
python research_agent.py
```

#### Single Query Mode

```bash
python research_agent.py --query "Research power banks released in 2025"
```

### Example Queries

- `Research the latest trends in AI chips`
- `Research power banks released in 2025`
- `Research electric vehicle market in Europe`
- `Research remote work tools for 2024`

The agent will automatically:
1. Research the topic
2. Create a Google Doc with findings
3. Email the document link to you

### What to Expect

#### 1. Initialization
```
🚀 Initializing Research Agent...
✓ Loaded 55 tools
```

#### 2. Just-in-Time OAuth Authorization

First time only - you'll see authorization prompts:

```
📋 Checking tool authorizations...

🔐 Authorization required for: Google_CreateDocumentFromText

   Please authorize by visiting:
   🔗 https://accounts.arcade.dev/oauth/authorize?...

   Waiting for authorization...
```

**Click the link** → Sign in with Google → Grant permissions → Agent continues!

```
   ✓ Authorization completed!

🔐 Authorization required for: Google_SendEmail

   Please authorize by visiting:
   🔗 https://accounts.arcade.dev/oauth/authorize?...

   Waiting for authorization...
   ✓ Authorization completed!
```

#### 3. Agent Execution

```
✓ Using OpenAI GPT-4o
✓ Agent ready!
✓ Reports will be sent to: recipient@example.com

============================================================
🔬 Research Agent - Interactive Mode
============================================================

📧 User: your-email@gmail.com
📬 Reports sent to: recipient@example.com

Examples:
  • Research the latest trends in AI chips
  • Research power banks released in 2025
  • Research electric vehicle market in Europe

The agent will create a Google Doc and email it to you.
Type 'quit' to exit.

You: Research power banks released in 2025
```

#### 4. Tool Execution & Results

```
────────────────────────────────────────────────────────────
📝 Query: Research power banks released in 2025
────────────────────────────────────────────────────────────

   🔧 Tool: Google_CreateDocumentFromText
   📄 Document: https://docs.google.com/document/d/1ABC.../edit

   🔧 Tool: Google_SendEmail
   ✓ Email sent successfully

🤖 Agent: I've created a research report on power banks released in 2025 
and sent it to recipient@example.com. You can also view the document here:
https://docs.google.com/document/d/1ABC.../edit
```

### Troubleshooting

#### "Missing required environment variables"
Ensure your `.env` file exists and has valid API keys.

#### "Authorization required" keeps appearing
- Click the authorization URL and complete the OAuth flow in your browser
- Make sure you're signed into the correct Google account
- Grant all requested permissions

#### Email not received
- Check your spam folder
- Verify RECIPIENT_EMAIL is correct in `.env`
- Ensure Gmail authorization was completed

### Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  DeepAgents     │────▶│ langchain-   │────▶│   Arcade API    │
│  (LangChain)    │     │ arcade       │     │                 │
└─────────────────┘     └──────────────┘     └────────┬────────┘
                                                      │
                                                      ▼
                                             ┌─────────────────┐
                                             │ Google Workspace│
                                             │ • Docs          │
                                             │ • Gmail         │
                                             │ • Calendar      │
                                             └─────────────────┘
```
