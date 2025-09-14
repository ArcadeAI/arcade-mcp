import { Mastra } from "@mastra/core"
import { LibSQLStore } from "@mastra/libsql"
import { inboxTravelSearchAgent } from "./agents/inboxTravelSearchAgent"

export const mastra = new Mastra({
    agents: { inboxTravelSearchAgent },
    storage: new LibSQLStore({
        url: "file:../mastra.db",
    }),
})
