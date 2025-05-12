import { openai } from "@ai-sdk/openai"
import { Arcade } from "@arcadeai/arcadejs"
import { executeOrAuthorizeZodTool, toZodToolSet } from "@arcadeai/arcadejs/lib"
import { streamText } from "ai"

const arcade = new Arcade()

/**
 * Get the Google toolkit.
 */
const googleToolkit = await arcade.tools.list({
    limit: 25,
    toolkit: "google",
})

/**
 * The Vercel AI SDK requires tools to be defined using Zod, a TypeScript-first schema validation library
 * that has become the standard for runtime type checking. Zod is particularly valuable because it:
 * - Provides runtime type safety and validation
 * - Offers excellent TypeScript integration with automatic type inference
 * - Has a simple, declarative API for defining schemas
 * - Is widely adopted in the TypeScript ecosystem
 *
 * Arcade provides `toZodToolSet` to convert our tools into Zod format, making them compatible
 * with the AI SDK.
 *
 * The `executeOrAuthorizeZodTool` helper function simplifies authorization.
 * It checks if the tool requires authorization: if so, it returns an authorization URL,
 * otherwise, it runs the tool directly without extra boilerplate.
 *
 * Learn more: https://docs.arcade.dev/home/use-tools/get-tool-definitions#get-zod-tool-definitions
 */
const googleTools = toZodToolSet({
    tools: googleToolkit.items,
    client: arcade,
    userId: "<YOUR_USER_ID>", // Your app's internal ID for the user (an email, UUID, etc). It's used internally to identify your user in Arcade
    executeFactory: executeOrAuthorizeZodTool,
})

const { textStream } = streamText({
    model: openai("gpt-4o-mini"),
    prompt: "Read my last email and summarize it in a few sentences",
    tools: googleTools,
    maxSteps: 5,
})

// Stream the response to the console
for await (const chunk of textStream) {
    process.stdout.write(chunk)
}
