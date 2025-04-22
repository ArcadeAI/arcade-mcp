import { openai } from "@ai-sdk/openai";
import { generateText } from "ai";
import { getArcadeTools, handleAuthorizationError } from "./arcade.js";

// Your app's internal ID for the user (an email, UUID, etc). It's used internally to identify your user in Arcade
const USER_ID = "USER_ID";

const model = openai("gpt-4o-mini");
const tools = await getArcadeTools({ toolkit: "google", user_id: USER_ID });

export const answerMyQuestion = async (prompt) => {
  try {
    const result = await generateText({
      model,
      prompt,
      tools,
      maxSteps: 5,
    });

    return result.text;
  } catch (error) {
    const url = await handleAuthorizationError(error, USER_ID);
    return `Authorization Required: Please visit this link to connect your Google account: ${url}`;
  }
};

const answer = await answerMyQuestion(
  "Read my last email and summarize it in a few sentences"
);

console.log(answer);
