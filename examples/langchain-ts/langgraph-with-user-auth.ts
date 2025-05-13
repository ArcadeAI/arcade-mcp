import { pathToFileURL } from "node:url";
import { Arcade } from "@arcadeai/arcadejs";
import { toZod } from "@arcadeai/arcadejs/lib";
import type { AIMessage } from "@langchain/core/messages";
import { tool } from "@langchain/core/tools";
import { MessagesAnnotation, StateGraph } from "@langchain/langgraph";
import { ToolNode } from "@langchain/langgraph/prebuilt";
import { ChatOpenAI } from "@langchain/openai";

// Initialize Arcade with API key from environment
const arcade = new Arcade();

// Replace with your application's user ID (e.g. email address, UUID, etc.)
const USER_ID = "user@example.com";

// Initialize tools from GitHub toolkit
const githubToolkit = await arcade.tools.list({ toolkit: "github", limit: 30 });
const arcadeTools = toZod({
	tools: githubToolkit.items,
	client: arcade,
	userId: USER_ID,
});

// Convert Arcade tools to LangGraph tools
const tools = arcadeTools.map(({ name, description, execute, parameters }) =>
	tool(execute, {
		name,
		description,
		schema: parameters,
	}),
);

// Initialize the prebuilt tool node
const toolNode = new ToolNode(tools);

// Create a language model instance and bind it with the tools
const model = new ChatOpenAI({
	model: "gpt-4o",
	apiKey: process.env.OPENAI_API_KEY,
});
const modelWithTools = model.bindTools(tools);

// Function to check if a tool requires authorization
async function requiresAuth(toolName: string): Promise<{
	needsAuth: boolean;
	id: string;
	authUrl: string;
}> {
	const authResponse = await arcade.tools.authorize({
		tool_name: toolName,
		user_id: USER_ID,
	});
	return {
		needsAuth: authResponse.status === "pending",
		id: authResponse.id ?? "",
		authUrl: authResponse.url ?? "",
	};
}

// Function to invoke the model and get a response
async function callAgent(
	state: typeof MessagesAnnotation.State,
): Promise<typeof MessagesAnnotation.Update> {
	const messages = state.messages;
	const response = await modelWithTools.invoke(messages);
	return { messages: [response] };
}

// Function to determine the next step in the workflow based on the last message
async function shouldContinue(
	state: typeof MessagesAnnotation.State,
): Promise<string> {
	const lastMessage = state.messages[state.messages.length - 1] as AIMessage;
	if (lastMessage.tool_calls?.length) {
		for (const toolCall of lastMessage.tool_calls) {
			const { needsAuth } = await requiresAuth(toolCall.name);
			if (needsAuth) {
				return "authorization";
			}
		}
		return "tools"; // Proceed to tool execution if no authorization is needed
	}
	return "__end__"; // End the workflow if no tool calls are present
}

// Function to handle authorization for tools that require it
async function authorize(
	state: typeof MessagesAnnotation.State,
): Promise<typeof MessagesAnnotation.Update> {
	const lastMessage = state.messages[state.messages.length - 1] as AIMessage;
	for (const toolCall of lastMessage.tool_calls || []) {
		const toolName = toolCall.name;
		const { needsAuth, id, authUrl } = await requiresAuth(toolName);
		if (needsAuth) {
			// Prompt the user to visit the authorization URL
			console.log(`Visit the following URL to authorize: ${authUrl}`);

			// Wait for the user to complete the authorization
			const response = await arcade.auth.waitForCompletion(id);
			if (response.status !== "completed") {
				throw new Error("Authorization failed");
			}
		}
	}

	return { messages: [] };
}

// Build the workflow graph
const workflow = new StateGraph(MessagesAnnotation)
	.addNode("agent", callAgent)
	.addNode("tools", toolNode)
	.addNode("authorization", authorize)
	.addEdge("__start__", "agent")
	.addConditionalEdges("agent", shouldContinue, [
		"authorization",
		"tools",
		"__end__",
	])
	.addEdge("authorization", "tools")
	.addEdge("tools", "agent");

// Compile the graph
const graph = workflow.compile();

const main = async () => {
	// Define the input messages from the user
	const inputs = {
		messages: [
			{
				role: "user",
				content: "Star arcadeai/arcade-ai on github",
			},
		],
	};
	// Run the graph and stream the outputs
	const stream = await graph.stream(inputs, { streamMode: "values" });
	for await (const chunk of stream) {
		// Print the last message in the chunk
		console.log(chunk.messages[chunk.messages.length - 1].content);
	}
};

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
	main().catch(console.error);
}

export { graph };
