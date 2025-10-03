import Arcade from '@arcadeai/arcadejs';
import { isAuthorizationRequiredError, toZod } from "@arcadeai/arcadejs/lib";
import { Agent, run, tool } from '@openai/agents';

async function main() {
  // 1) Initialize Arcade client
  const client = new Arcade();

  // 2) Fetch Gmail toolkit from Arcade and prepare tools for OpenAI Agents
  const gmailToolkit = await client.tools.list({ toolkit: "gmail", limit: 30 });
  const tools = toZod({
    tools: gmailToolkit.items,
    client,
    userId: "<YOUR_SYSTEM_USER_ID_2>", // Replace this with your application's user ID (e.g. email address, UUID, etc.)
  }).map(tool);

  // 3) Create a new agent with the Gmail toolkit
  const gmailAgent = new Agent({
    name: "Gmail agent",
    instructions: "You are a helpful assistant that can assist with Gmail API calls.",
    model: "gpt-4o-mini",
    tools
  });

  // 4) Run the agent, if authorization is required, wait for it to complete and retry
  while (true) {
    try {
      const result = await run(gmailAgent, "What are my latest emails?");
      console.log(result.finalOutput);
      break; // Exit the loop if the result is successful
    } catch (error) {
      if (error instanceof Error && isAuthorizationRequiredError(error)) {
        const response = await client.tools.authorize({
          tool_name: "Gmail_ListEmails",
          user_id: "<YOUR_SYSTEM_USER_ID_2>",
        });
        if (response.status !== "completed") {
          console.log(`Please complete the authorization challenge in your browser: ${response.url}`);
        }

        // Wait for the authorization to complete
        await client.auth.waitForCompletion(response);
        console.log("Authorization completed, retrying...");
      }
    }
  }
}

main();
