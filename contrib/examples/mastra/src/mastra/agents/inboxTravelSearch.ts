import { Agent } from "@mastra/core/agent"
import { mastraGmailTools } from "../tools/gmailTools"
import { flightTools } from "../tools/flightSearchTools"
import { hotelTools } from "../tools/hotelSearchTools"



// Create an agent with Gmail, FlightSearch, and HotelSearch tools
export const inboxTravelSearchAgent = new Agent({
    name: "inboxTravelSearchAgent",
    id: "inboxTravelSearchAgent",
    instructions: `You are an assistant that helps users manage their Gmail inbox and can help with travel related tasks and planning.

When helping users:
- Always verify their intent before performing actions
- Keep responses clear and concise
- Confirm important actions before executing them
- Respect user privacy and data security

Use the gmailTools to interact with various Gmail services and perform related tasks.
Use the flightTools to interact with various flight services and perform related tasks.
Use the hotelTools to interact with various hotel services and perform related tasks.`,
    model: 'openai/gpt-4o-mini',
    tools: { ...mastraGmailTools, ...flightTools, ...hotelTools },
})
