import { openai } from "@ai-sdk/openai"
import { Agent } from "@mastra/core/agent"
import { Memory } from "@mastra/memory"
import { LibSQLStore } from "@mastra/libsql"
import { gmailTools } from "../tools/gmailTools"

// Initialize memory
const memory = new Memory({
    storage: new LibSQLStore({
        url: "file:../../memory.db",
    }),
})

// Create an agent with Gmail tools
export const gmailAgent = new Agent({
    name: "gmailAgent",
    instructions: `You are a Gmail assistant that helps users manage their inbox.

When helping users:
- Always verify their intent before performing actions
- Keep responses clear and concise
- Confirm important actions before executing them
- Respect user privacy and data security

Use the gmailTools to interact with various Gmail services and perform related tasks.`,
    model: openai("gpt-4o-mini"),
    memory,
    tools: gmailTools,
})
