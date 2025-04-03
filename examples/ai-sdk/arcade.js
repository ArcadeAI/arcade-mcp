import { Arcade } from "@arcadeai/arcadejs";
import { PermissionDeniedError } from "@arcadeai/arcadejs";
import { ToolExecutionError } from "ai";
import { jsonSchema } from "ai";

const arcadeClient = new Arcade({
  baseURL: "http://localhost:9099",
});

/**
 * Retrieves and formats tools from Arcade.dev to the format required by the AI SDK.
 * @param {Object} options - The options object
 * @param {string} [options.toolkit] - Optional toolkit name to filter tools (e.g. "google", "slack")
 * @param {string} options.user_id - The user ID from your application (e.g. an email, UUID, etc.)
 */
export const getArcadeTools = async ({ toolkit, user_id }) => {
  const tools = await arcadeClient.tools.list({
    ...(toolkit && { toolkit }),
  });

  const toolsSet = {};

  for (const item of tools.items) {
    if (!item.name) continue;

    const toolName = `${item.toolkit.name}.${item.name}`;

    const formattedTool = await arcadeClient.tools.formatted.get(toolName, {
      format: "openai",
    });

    toolsSet[formattedTool.function.name] = {
      parameters: jsonSchema(formattedTool.function.parameters),
      description: item.description,
      execute: async (input) =>
        await arcadeClient.tools.execute({
          tool_name: toolName,
          input,
          user_id,
        }),
    };
  }

  return toolsSet;
};

/**
 * Determines if the error indicates that user authorization is needed for the tool
 * @param {Error} error - The error caught during tool execution
 * @returns {boolean} True if the error indicates authorization is required
 */
export const isAuthorizationRequiredError = (error) => {
  return (
    error instanceof ToolExecutionError &&
    error.cause instanceof PermissionDeniedError
  );
};

/**
 * Gets the authorization response for a tool that requires authentication
 * @param {string} toolName - The name of the tool that needs authorization
 * @param {string} user_id - The user ID from your application
 * @returns {Promise<{url: string}>} The authorization response
 */
export const getAuthorizationResponse = async (toolName, user_id) => {
  return await arcadeClient.tools.authorize({
    tool_name: toolName,
    user_id,
  });
};

/**
 * Handles authorization errors by returning the authorization URL if needed, otherwise rethrows the error
 * @param {Error} error - The error to handle
 * @param {string} user_id - The user ID from your application
 * @returns {Promise<string>} The authorization URL if needed, otherwise the error is rethrown
 */
export const handleAuthorizationError = async (error, user_id) => {
  if (isAuthorizationRequiredError(error)) {
    const response = await getAuthorizationResponse(error.toolName, user_id);
    return response.url;
  }

  throw error;
};
