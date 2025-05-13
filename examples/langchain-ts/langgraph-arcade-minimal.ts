import { Arcade } from "@arcadeai/arcadejs";
import { executeOrAuthorizeZodTool, toZod } from "@arcadeai/arcadejs/lib";
import { tool } from "@langchain/core/tools";
import { MemorySaver } from "@langchain/langgraph";
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { ChatOpenAI } from "@langchain/openai";

// 1) Initialize Arcade
const arcade = new Arcade();

// 2) Fetch Google toolkit from Arcade and prepare tools for LangGraph integration
const googleToolkit = await arcade.tools.list({ toolkit: "google", limit: 30 });
const arcadeTools = toZod({
	tools: googleToolkit.items,
	client: arcade,
	userId: "<YOUR_SYSTEM_USER_ID>", // Replace this with your application's user ID (e.g. email address, UUID, etc.)
	executeFactory: executeOrAuthorizeZodTool,
});
// Convert Arcade tools to LangGraph tools
const tools = arcadeTools.map(({ name, description, execute, parameters }) =>
	tool(execute, {
		name,
		description,
		schema: parameters,
	}),
);

// 3) Create a ChatOpenAI model and bind the Arcade tools.
const model = new ChatOpenAI({
	model: "gpt-4o",
	apiKey: process.env.OPENAI_API_KEY,
});
const boundModel = model.bindTools(tools);

// 4) Use MemorySaver for checkpointing.
const memory = new MemorySaver();

// 5) Create a ReAct-style agent from the prebuilt function.
const graph = createReactAgent({
	llm: boundModel,
	tools,
	checkpointer: memory,
});

// 6)  Provide basic config and a user query.
// Note: user_id is required for the tool to be authorized
const config = {
	configurable: {
		thread_id: "1",
		user_id: "user@example.com",
	},
	streamMode: "values" as const,
};
const user_input = {
	messages: [
		{
			role: "user",
			content: "List any new and important emails in my inbox.",
		},
	],
};

// 7) Stream the agent's output. If the tool is unauthorized, the agent will ask the user to authorize the tool.
try {
	const stream = await graph.stream(user_input, config);
	for await (const chunk of stream) {
		console.log(chunk.messages[chunk.messages.length - 1]);
	}
} catch (error) {
	console.error("Error streaming response:", error);
}
// Once you login using the printed link, you can resume the agent.
