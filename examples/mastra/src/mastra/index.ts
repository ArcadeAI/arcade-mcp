import { Mastra } from "@mastra/core";
import { LibSQLStore } from "@mastra/libsql";
import { gmailAgent } from "./agents/gmail";

export const mastra = new Mastra({
	agents: { gmailAgent },
	storage: new LibSQLStore({
		url: "file:../mastra.db",
	}),
});
