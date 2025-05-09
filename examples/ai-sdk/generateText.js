import { openai } from "@ai-sdk/openai"
import { Arcade } from "@arcadeai/arcadejs"
import { executeOrAuthorizeZodTool, toZodToolSet } from "@arcadeai/arcadejs/lib"
import { generateText } from "ai"

const arcade = new Arcade()

const googleToolkit = await arcade.tools.list({
    limit: 25,
    toolkit: "google",
})

const googleTools = toZodToolSet({
    tools: googleToolkit.items,
    client: arcade,
    userId: "<YOUR_USER_ID>", // Your app's internal ID for the user (an email, UUID, etc). It's used internally to identify your user in Arcade
    executeFactory: executeOrAuthorizeZodTool, // Checks if tool is authorized and executes it, or returns authorization URL if needed
})

const result = await generateText({
    model: openai("gpt-4o-mini"),
    prompt: "Read my last email and summarize it in a few sentences",
    tools: googleTools,
    maxSteps: 5,
})

console.log(result.text)
