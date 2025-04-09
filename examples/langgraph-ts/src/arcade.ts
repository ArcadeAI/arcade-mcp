import { Arcade } from "@arcadeai/arcadejs";
import { JSONSchemaToZod } from "@dmitryrechkin/json-schema-to-zod";
import { tool } from "@langchain/core/tools";
import { z } from "zod";

export const arcadeClient = new Arcade({
	baseURL: process.env.ARCADE_BASE_URL,
	apiKey: process.env.ARCADE_API_KEY,
});

const arcadeToolMinimumSchema = z.object({
	function: z.object({
		name: z.string(),
		parameters: z.record(z.any()),
		description: z.string(),
	}),
});

function isAuthorizationRequiredError(error: Error) {
	return (
		error?.name === "PermissionDeniedError" ||
		error?.message?.includes("permission denied") ||
		error?.message?.includes("authorization required")
	);
}

async function getAuthorizationResponse(toolName: string, user_id: string) {
	return await arcadeClient.tools.authorize({
		tool_name: toolName,
		user_id,
	});
}

type LangChainTool = ReturnType<typeof tool>;

export const getArcadeTools = async ({
	toolkits,
	user_id,
}: {
	toolkits?: string[];
	user_id: string;
}): Promise<LangChainTool[]> => {
	// If no toolkits provided, fetch all tools
	if (!toolkits || toolkits.length === 0) {
		const tools = await arcadeClient.tools.formatted.list({
			format: "openai",
		});
		return processTools(tools.items, user_id);
	}

	// Fetch tools for each toolkit and merge them
	const toolkitPromises = toolkits.map((toolkit) =>
		arcadeClient.tools.formatted.list({
			toolkit,
			format: "openai",
		})
	);

	const toolkitResults = await Promise.all(toolkitPromises);
	const allTools = toolkitResults.flatMap((result) => result.items);

	// Remove duplicates based on tool name
	const uniqueTools = Array.from(
		new Map(allTools.map((item) => [item.function.name, item])).values()
	);

	return processTools(uniqueTools, user_id);
};

// Helper function to process tools and create LangChain tools
const processTools = (tools: unknown[], user_id: string): LangChainTool[] => {
	const validTools = tools
		.filter((item) => arcadeToolMinimumSchema.safeParse(item).success)
		.map((item) => arcadeToolMinimumSchema.parse(item));

	return validTools.map((item) => {
		const { name, description, parameters } = item.function;
		const zodSchema = JSONSchemaToZod.convert(parameters);

		return tool(
			async (input: unknown) => {
				try {
					return await arcadeClient.tools.execute({
						tool_name: name,
						input: input as Record<string, unknown>,
						user_id,
					});
				} catch (error) {
					if (error instanceof Error && isAuthorizationRequiredError(error)) {
						const response = await getAuthorizationResponse(name, user_id);
						return {
							authorization_required: true,
							url: response.url,
							message: "Forward this url to the user for authorization",
						};
					}
					throw error;
				}
			},
			{ name, description, schema: zodSchema },
		) as unknown as LangChainTool;
	});
};
