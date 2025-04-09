import type { RunnableConfig } from "@langchain/core/runnables";
/**
 * Define the configurable parameters for the agent.
 */
import { Annotation } from "@langchain/langgraph";
import { SYSTEM_PROMPT_TEMPLATE } from "./prompts.js";

export const ConfigurationSchema = Annotation.Root({
	/**
	 * The system prompt to be used by the agent.
	 */
	systemPromptTemplate: Annotation<string>,

	/**
	 * The name of the language model to be used by the agent.
	 */
	model: Annotation<string>,
});

export function ensureConfiguration(
	config: RunnableConfig,
): typeof ConfigurationSchema.State {
	/**
	 * Ensure the defaults are populated.
	 */
	const configurable = config.configurable ?? {};
	return {
		systemPromptTemplate:
			configurable.systemPromptTemplate ?? SYSTEM_PROMPT_TEMPLATE,
		model: configurable.model ?? "gpt-4o-mini",
	};
}
