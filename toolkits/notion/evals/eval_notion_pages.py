from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_notion_toolkit
from arcade_notion_toolkit.tools import (
    create_page,
    get_page_content_by_id,
    get_page_content_by_title,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_notion_toolkit)

PAGE_CONTENT = """## Why Build Tools with Arcade?

Arcade solves key challenges for agent developers:

1. **Auth Native to Agents**: Authentication designed for agentic workflows — the right token is always available for each user without complex integration work.

2. **Multi-Tenant Tool Calling**: Enable your agent to take actions AS the specific user of the agent

3. **Better Agent Capabilities**: Build tools that securely connect to the services your users want your agent to integrate with (Gmail, Slack, Google Drive, Zoom, etc.) without complex integration code.

4. **Clean Codebase**: Eliminate environment variables full of API keys and complex OAuth implementations from your application code.

5. **Flexible Integration**: Choose your integration approach:

    - LLM API for the simplest experience with hundreds of pre-built tools
    - Tools API for direct execution control
    - Auth API for authentication-only integration
    - Framework connectors for LangChain, CrewAI and others

6. **Zero Schema Maintenance**: Tool definitions generate automatically from code annotations and translate to any LLM format.

7. **Built-in Evaluation**: Evaluate your tools across user scenarios, llms, and context with Arcade's tool calling evaluation framework. Ensure your tools are working as expected and are useful for your agents.

8. **Complete Tooling Ecosystem**: Built-in evaluation framework, scalable execution infrastructure, and flexible deployment options (including VPC, Docker, and Kubernetes).

Arcade lets you focus on creating useful tool functionality rather than solving complex authentication, deployment, and integration challenges.
"""  # noqa: E501

# A conversation where a user asks the AI to get the content of a page named 'Arcade Notes'
GET_PAGE_CONVERSATION = [
    {"role": "user", "content": "get 'Arcade Notes'"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_92Vhl75I8KEKQfjihS7l53DL",
                "type": "function",
                "function": {
                    "name": "Notion_GetPageContentByTitle",
                    "arguments": '{"title":"Arcade Notes"}',
                },
            }
        ],
    },
    {
        "role": "tool",
        "content": "# Arcade Notes\nFirst, make sure you have these pre-requisites installed on your system:  \n- **Python 3.10**\xa0or higherVerify your Python version by running\xa0`python --version`\xa0or\xa0`python3 --version`\xa0in your terminal.  \n- **pip**: The Python package installer should be available. It's typically included with Python.  \n- **Arcade Account**: Sign up for an\xa0[Arcade account](https://api.arcade.dev/signup?utm_source=docs&utm_medium=page&utm_campaign=custom-tools)\xa0if you haven't already.  \nLet's set up Arcade and give it a try!  \n### **Obtain an API key**  \nInstall the Arcade CLI and SDK and log in. Your Arcade API key will be printed to the console as well as saved to\xa0`~/.arcade/credentials.yaml`.  \npip install arcade-aiarcade login\n### **Try\xa0**`arcade chat`  \nWith Arcade CLI installed, you can test outour API with the\xa0`arcade chat`\xa0command:  \narcade chat\nThis launches a chat with the Arcade Cloud Engine (hosted at\xa0`api.arcade.dev`). All pre-built Arcade tools are available to use.  \nFor example, try asking:  \nstar the ArcadeAI/arcade-ai repo on Github\nArcade will ask you to authorize with GitHub, and then the AI assistant will star the\xa0[ArcadeAI/arcade-ai](https://github.com/ArcadeAI/arcade-ai)\xa0repo on your behalf.  \nYou'll see output similar to this:  \nAssistant (gpt-4o):I starred the ArcadeAI/arcade-ai repo on Github for you!\nYou can use Ctrl-C to exit the chat at any time.  \n### **Try more tools**  \nTry prompting the AI with different requests:  \n- Search the web to find when The Winds of Winter will be released  \n- Summarize my emails from today  \n- What's playing on my Spotify right now?  \nTo see all tools available in the Cloud, run:  \narcade show\nGreat job! 🎉 You've set up Arcade and used your first tool.  \n### **Next steps**  \n- [Learn about tools](https://docs.arcade.dev/home/use-tools/tools-overview)\xa0andhow they work  \n- Learn how to\xa0[call tools with models](https://docs.arcade.dev/home/use-tools/call-tools-with-models)  \n- Or, jump ahead to building your own\xa0[custom tools](https://docs.arcade.dev/home/build-tools/create-a-toolkit)  \n",  # noqa: E501
        "tool_call_id": "call_92Vhl75I8KEKQfjihS7l53DL",
        "name": "Notion_GetPageContentByTitle",
    },
    {
        "role": "assistant",
        "content": "Here are the notes on setting up and using Arcade:\n\n### Pre-requisites\nMake sure you have the following installed on your system:\n-**Python 3.10 or higher**: Verify using `python --version` or `python3 --version` in your terminal.\n- **pip**: The Python package installer, typically included with Python.\n- **Arcade Account**: Sign up for an [Arcade account](https://api.arcade.dev/signup?utm_source=docs&utm_medium=page&utm_campaign=custom-tools) if you haven't already.\n\n### Setting up Arcade\n\n#### Obtain an API key\n1. Install the Arcade CLI and SDK.\n2. Log in to Arcade: Run the command `arcade login`.\n3. Your Arcade API key will be printed to the console and saved in `~/.arcade/credentials.yaml`.\n\n#### Try `arcade chat`\n- With Arcade CLI installed, you can test the API using `arcade chat`.\n- This command launches a chat with the Arcade Cloud Engine (hosted at `api.arcade.dev`), giving you access to all pre-built Arcade tools.\n  \nExample prompt:  \n- Ask to star the `ArcadeAI/arcade-ai` repo on GitHub. The AI assistant will star the repo for you after authorization.\n\nEvent example output:\n```\nAssistant (gpt-4o): I starred the ArcadeAI/arcade-ai repo on Github for you!\n```\n\nUse `Ctrl-C` to exit the chat anytime.\n\n### Explore More Tools\n- Try different requests like searching the web, summarizing emails, or checking your current Spotify play.\n- Run `arcade show` to see all available tools in the Cloud.\n\n### Next Steps\n- [Learn about tools](https://docs.arcade.dev/home/use-tools/tools-overview) and how they function.\n- Understand how to [call tools with models](https://docs.arcade.dev/home/use-tools/call-tools-with-models).\n- Begin building your own [custom tools](https://docs.arcade.dev/home/build-tools/create-a-toolkit).\n\nCongratulations on setting up Arcade and trying your first tool! 🎉",  # noqa: E501
    },
]


@tool_eval()
def create_page_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools creating a Notion page"""
    suite = EvalSuite(
        name="Notion Create Page Evaluation",
        system_message=(
            "You are an AI assistant that has access to the user's Notion workspace. "
            "You can take actions on the user's Notion workspace on behalf of the user."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Easy case
    suite.add_case(
        name="Create page easy difficulty",
        user_message=(
            "Create a page with the title '07/11/2027' and content '* drank a slurpie' "
            "under the parent page 'Daily Standup'."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_page,
                args={
                    "parent_title": "Daily Standup",
                    "title": "07/11/2027",
                    "content": "* drank a slurpie",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="parent_title", weight=0.34),
            SimilarityCritic(critic_field="title", weight=0.33, similarity_threshold=0.95),
            SimilarityCritic(critic_field="content", weight=0.33, similarity_threshold=0.95),
        ],
    )

    # Medium case
    suite.add_case(
        name="Create page medium difficulty",
        user_message=(
            f"Create a page with the title 'Why Use Arcade?' and content {PAGE_CONTENT}"
            "under the parent page 'Arcade Notes'."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_page,
                args={
                    "parent_title": "Arcade Notes",
                    "title": "Why Use Arcade?",
                    "content": PAGE_CONTENT,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="parent_title", weight=0.34),
            SimilarityCritic(critic_field="title", weight=0.33, similarity_threshold=0.95),
            SimilarityCritic(critic_field="content", weight=0.33, similarity_threshold=0.95),
        ],
    )

    # Hard case
    suite.add_case(
        name="Create page hard difficulty",
        user_message=(f"Add {PAGE_CONTENT} as a subpage. Name it 'Why Use Arcade?'"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_page,
                args={
                    "parent_title": "Arcade Notes",
                    "title": "Why Use Arcade?",
                    "content": PAGE_CONTENT,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="parent_title", weight=0.34),
            SimilarityCritic(critic_field="title", weight=0.33, similarity_threshold=0.95),
            SimilarityCritic(critic_field="content", weight=0.33, similarity_threshold=0.95),
        ],
        additional_messages=GET_PAGE_CONVERSATION,
    )
    return suite


@tool_eval()
def get_page_content_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools getting the content of a Notion page"""
    suite = EvalSuite(
        name="Notion Get Page Content By ID Evaluation",
        system_message=(
            "You are an AI assistant that has access to the user's Notion workspace. "
            "You can take actions on the user's Notion workspace on behalf of the user."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Easy case
    suite.add_case(
        name="Get page content by id easy difficulty",
        user_message="Get the content of the page with id 1b37a62b04d48079a902ce69ed7e7240",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_page_content_by_id,
                args={
                    "page_id": "1b37a62b04d48079a902ce69ed7e7240",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="page_id", weight=1),
        ],
    )

    # Medium case
    suite.add_case(
        name="Get page content medium difficulty",
        user_message=(
            "Summarize the main points in 1b37a62b04d48079a902ce69ed7e7240. "
            "Also, does 'Tool Calling with Arcade' actually talk about tools?"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_page_content_by_id,
                args={
                    "page_id": "1b37a62b04d48079a902ce69ed7e7240",
                },
            ),
            ExpectedToolCall(
                func=get_page_content_by_title,
                args={
                    "title": "Tool Calling with Arcade",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="page_id", weight=0.5),
            BinaryCritic(critic_field="title", weight=0.5),
        ],
    )

    # Hard case
    suite.add_case(
        name="Get page content hard difficulty",
        user_message=(
            "Compare it's main points against 'Tool Calling with Arcade' and "
            "'Tool Execution with Arcade'"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_page_content_by_title,
                args={
                    "title": "Tool Calling with Arcade",
                },
            ),
            ExpectedToolCall(
                func=get_page_content_by_title,
                args={
                    "title": "Tool Execution with Arcade",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="title", weight=1),
        ],
        additional_messages=GET_PAGE_CONVERSATION,
    )

    return suite
