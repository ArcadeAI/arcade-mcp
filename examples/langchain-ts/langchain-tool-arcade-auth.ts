import { Arcade } from "@arcadeai/arcadejs";
import {
	GmailCreateDraft,
	GmailGetMessage,
	GmailGetThread,
	GmailSearch,
	GmailSendMessage,
} from "@langchain/community/tools/gmail";
import type { StructuredTool } from "@langchain/core/tools";
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { ChatOpenAI } from "@langchain/openai";

// Initialize Arcade with API key from environment
const arcade = new Arcade();
// Replace this with your application's user ID (e.g. email address, UUID, etc.)
const USER_ID = "user@example.com";

// Start the authorization process for Gmail
// see all possible gmail scopes here:
// https://developers.google.com/gmail/api/auth/scopes
const authResponse = await arcade.auth.start(USER_ID, "google", {
	scopes: ["https://www.googleapis.com/auth/gmail.readonly"],
});

// Prompt the user to authorize if not already completed
if (authResponse.status !== "completed") {
	console.log("Please authorize the application in your browser:");
	console.log(authResponse.url);
}

// Wait for the user to complete the authorization process, if necessary...
const completedAuth = await arcade.auth.waitForCompletion(authResponse);

if (!completedAuth.context?.token) {
	throw new Error("Failed to get authorization token");
}

// Get Gmail tools with credentials
const gmailParam = {
	credentials: {
		accessToken: completedAuth.context.token,
	},
};
const tools: StructuredTool[] = [
	new GmailCreateDraft(gmailParam),
	new GmailGetMessage(gmailParam),
	new GmailGetThread(gmailParam),
	new GmailSearch(gmailParam),
	new GmailSendMessage(gmailParam),
];

// Initialize the language model and create an agent
const llm = new ChatOpenAI({ model: "gpt-4o" });
const agent_executor = createReactAgent({
	llm,
	tools,
});

// Define the user query
const exampleQuery = "Read my latest emails and summarize them.";

// Execute the agent with the user query
const events = await agent_executor.stream(
	{
		messages: [
			{
				role: "user",
				content: exampleQuery,
			},
		],
	},
	{
		streamMode: "values",
	},
);

for await (const event of events) {
	console.log(event.messages[event.messages.length - 1]);
}
