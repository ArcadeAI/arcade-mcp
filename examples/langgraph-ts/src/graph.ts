import type { AIMessage } from "@langchain/core/messages";
import type { RunnableConfig } from "@langchain/core/runnables";
import { MessagesAnnotation, StateGraph } from "@langchain/langgraph";
import { ToolNode } from "@langchain/langgraph/prebuilt";
import { getArcadeTools } from "./arcade.ts";
import { ConfigurationSchema, ensureConfiguration } from "./configuration.ts";
import { loadChatModel } from "./utils.ts";
import { ChatOpenAI } from "@langchain/openai";


// Replace this with your application's user ID (e.g. email address, UUID, etc.)
const USER_ID = "user@example.com";
// Get the Arcade tools, you can customize the toolkit (e.g. "github", "notion", "google", etc.)
const arcadeTools = await getArcadeTools({
	toolkits: ["google", "github"],
	user_id: USER_ID,
});
// Define the function that calls the model
async function callModel(
	state: typeof MessagesAnnotation.State,
	config: RunnableConfig,
): Promise<typeof MessagesAnnotation.Update> {
	/** Call the LLM powering our agent. **/
	const configuration = ensureConfiguration(config);

	/**
	 * Initialize the model and bind the tools
	 */
	const model = new ChatOpenAI({
		model: configuration.model,
		apiKey: process.env.OPENAI_API_KEY,
	}).bindTools(arcadeTools);

	const response = await model.invoke([
		{
			role: "system",
			content: configuration.systemPromptTemplate.replace(
				"{system_time}",
				new Date().toISOString(),
			),
		},
		...state.messages,
	]);

	// We return a list, because this will get added to the existing list
	return { messages: [response] };
}

// Define the function that determines whether to continue or not
function routeModelOutput(state: typeof MessagesAnnotation.State): string {
	const messages = state.messages;
	const lastMessage = messages[messages.length - 1];
	// If the LLM is invoking tools, route there.
	if ((lastMessage as AIMessage)?.tool_calls?.length) {
		return "tools";
	}
	// Otherwise end the graph.

	return "__end__";
}

// Define a new graph. We use the prebuilt MessagesAnnotation to define state:
// https://langchain-ai.github.io/langgraphjs/concepts/low_level/#messagesannotation
const workflow = new StateGraph(MessagesAnnotation, ConfigurationSchema)
	// Define the two nodes we will cycle between
	.addNode("callModel", callModel)
	.addNode("tools", new ToolNode(arcadeTools))
	// Set the entrypoint as `callModel`
	// This means that this node is the first one called
	.addEdge("__start__", "callModel")
	.addConditionalEdges(
		// First, we define the edges' source node. We use `callModel`.
		// This means these are the edges taken after the `callModel` node is called.
		"callModel",
		// Next, we pass in the function that will determine the sink node(s), which
		// will be called after the source node is called.
		routeModelOutput,
	)
	// This means that after `tools` is called, `callModel` node is called next.
	.addEdge("tools", "callModel");

// Finally, we compile it!
// This compiles it into a graph you can invoke and deploy.
export const graph = workflow.compile({
	interruptBefore: [], // if you want to update the state before calling the tools
	interruptAfter: [],
});
