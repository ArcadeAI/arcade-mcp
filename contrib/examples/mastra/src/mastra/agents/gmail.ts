import { Agent } from "@mastra/core/agent"
import { mastraGmailTools } from "../tools/gmailTools"


export const gmailAgent = new Agent({
    name: "gmailAgent",
    id: "gmailAgent",
    instructions: `You are a Gmail assistant that helps users manage their inbox.

When helping users:
- Always verify their intent before performing actions
- Keep responses clear and concise
- Confirm important actions before executing them
- Respect user privacy and data security

Use the gmailTools to interact with various Gmail services and perform related tasks.`,
    model: 'openai/gpt-4o-mini',
    tools: mastraGmailTools,
})
