import Arcade from '@arcadeai/arcadejs';
import { executeOrAuthorizeZodTool, toZod } from "@arcadeai/arcadejs/lib";
import { Agent, run, tool } from '@openai/agents';

// 1) Initialize Arcade client
const client = new Arcade();

// 2) Fetch Google toolkit from Arcade and prepare tools for OpenAI Agents
const googleToolkit = await client.tools.list({ toolkit: "google", limit: 30 });
const tools = toZod({
  tools: googleToolkit.items,
  client,
  userId: "<YOUR_SYSTEM_USER_ID>", // Replace this with your application's user ID (e.g. email address, UUID, etc.)
  executeFactory: executeOrAuthorizeZodTool,
}).map(tool);

// 3) Create a new agent with the Google toolkit
const googleAgent = new Agent({
  name: "Google agent",
  instructions: "You are a helpful assistant that can assist with Google API calls.",
  model: "gpt-4o-mini",
  tools
});

// 4) Run the agent
const result = await run(googleAgent, "What are my latest emails?");

// 5) Print the result
console.log(result.finalOutput);
