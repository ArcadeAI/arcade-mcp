import { openai } from "@ai-sdk/openai";
import { Arcade } from "@arcadeai/arcadejs";
import {
	executeOrAuthorizeZodTool,
	toZodToolSet,
} from "@arcadeai/arcadejs/lib";
import { Agent } from "@mastra/core/agent";
import { Memory } from "@mastra/memory";
import { LibSQLStore } from "@mastra/libsql";

// Initialize Arcade
const arcade = new Arcade();

// Get Google tools
const googleToolkit = await arcade.tools.list({ toolkit: "google", limit: 30 });

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
export const googleTools = toZodToolSet({
	tools: googleToolkit.items,
	client: arcade,
	userId: "<YOUR_USER_ID>", // Your app's internal ID for the user (an email, UUID, etc). It's used internally to identify your user in Arcade
	executeFactory: executeOrAuthorizeZodTool, // Checks if tool is authorized and executes it, or returns authorization URL if needed
});

// Initialize memory
const memory = new Memory({
  storage: new LibSQLStore({
    url: "file:../../memory.db",
  }),
});

// Create an agent with Google tools
export const googleAgent = new Agent({
	name: "googleAgent",
	instructions: `You are a Google assistant that helps users manage their Google services (Gmail, Calendar, Sheets, Drive, and Contacts).

When helping users:
- Always verify their intent before performing actions
- Keep responses clear and concise
- Confirm important actions before executing them
- Respect user privacy and data security
- Specify which Google service you're working with

Use the googleTools to interact with various Google services and perform related tasks.`,
	model: openai("gpt-4o-mini"),
	memory,
	tools: googleTools,
});
