import { openai } from "@ai-sdk/openai"
import { Arcade } from "@arcadeai/arcadejs"
import { executeOrAuthorizeZodTool, toZodToolSet } from "@arcadeai/arcadejs/lib"
import { Agent } from "@mastra/core/agent"
import { Memory } from "@mastra/memory"
import { LibSQLStore } from "@mastra/libsql"

// Initialize Arcade
const arcade = new Arcade()
const arcadeUserId = "<YOUR_USER_ID>" // Your app's internal ID for the user (an email, UUID, etc). It's used internally to identify your user in Arcade

// Get Arcade Toolkits
// Toolkit names can be found in the Arcade dashboard via Tools > view > Toolkit
const gmailToolkit = await arcade.tools.list({ toolkit: "Gmail", limit: 30 })
const flightToolkit = await arcade.tools.list({ toolkit: "GoogleFlights", limit: 30 })
const hotelToolkit = await arcade.tools.list({ toolkit: "GoogleHotels", limit: 30 })

/**
 * Mastra requires tools to be defined using Zod, a TypeScript-first schema validation library
 * that has become the standard for runtime type checking. Zod is particularly valuable because it:
 * - Provides runtime type safety and validation
 * - Offers excellent TypeScript integration with automatic type inference
 * - Has a simple, declarative API for defining schemas
 * - Is widely adopted in the TypeScript ecosystem
 *
 * Arcade provides `toZodToolSet` to convert our tools into Zod format, making them compatible
 * with Mastra.
 *
 * The `executeOrAuthorizeZodTool` helper function simplifies authorization.
 * It checks if the tool requires authorization: if so, it returns an authorization URL,
 * otherwise, it runs the tool directly without extra boilerplate.
 *
 * Learn more: https://docs.arcade.dev/home/use-tools/get-tool-definitions#get-zod-tool-definitions
 */
export const gmailTools = toZodToolSet({
    tools: gmailToolkit.items,
    client: arcade,
    userId: arcadeUserId, // Your app's internal ID for the user (an email, UUID, etc). It's used internally to identify your user in Arcade
    executeFactory: executeOrAuthorizeZodTool, // Checks if tool is authorized and executes it, or returns authorization URL if needed
})

const flightTools = toZodToolSet({
    tools: flightToolkit.items,
    client: arcade,
    userId: arcadeUserId, // Your app's internal ID for the user (an email, UUID, etc). It's used internally to identify your user in Arcade
    executeFactory: executeOrAuthorizeZodTool, // Checks if tool is authorized and executes it, or returns authorization URL if needed
})

const hotelTools = toZodToolSet({
    tools: hotelToolkit.items,
    client: arcade,
    userId: arcadeUserId, // Your app's internal ID for the user (an email, UUID, etc). It's used internally to identify your user in Arcade
    executeFactory: executeOrAuthorizeZodTool, // Checks if tool is authorized and executes it, or returns authorization URL if needed
})

// Initialize memory
const memory = new Memory({
    storage: new LibSQLStore({
        url: "file:../../memory.db",
    }),
})

// Create an agent with Gmail tools
export const inboxTravelSearchAgent = new Agent({
    name: "inboxTravelSearchAgent",
    instructions: `You are an assistant that helps users manage their Gmail inbox and can help with travel related tasks and planning.

When helping users:
- Always verify their intent before performing actions
- Keep responses clear and concise
- Confirm important actions before executing them
- Respect user privacy and data security

Use the gmailTools to interact with various Gmail services and perform related tasks.
Use the flightTools to interact with various flight services and perform related tasks.
Use the hotelTools to interact with various hotel services and perform related tasks.`,
    model: openai("gpt-4o-mini"),
    memory,
    tools: { ...gmailTools, ...flightTools, ...hotelTools },
})
