import { Mastra } from "@mastra/core";
import { LibSQLStore } from "@mastra/libsql";
import { googleAgent } from "./agents/google";

export const mastra = new Mastra({
	agents: { googleAgent },
	storage: new LibSQLStore({
		url: "file:../mastra.db",
	}),
});
