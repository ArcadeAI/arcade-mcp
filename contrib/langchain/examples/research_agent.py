#!/usr/bin/env python3
"""
Industry Research Agent with DeepAgents + Arcade

An AI agent that researches topics and creates Google Docs reports.

Features:
- Uses Arcade's Google and Gmail tools
- Just-in-time OAuth authorization flow
- Creates Google Docs with research findings
- Can send reports via email

Requirements:
    pip install langchain-arcade[dev]

Environment Variables (create a .env file or export):
    ARCADE_API_KEY: Your Arcade API key (https://arcade.dev)
    OPENAI_API_KEY: Your OpenAI API key (or ANTHROPIC_API_KEY)
    USER_EMAIL: Your email for Arcade authorization

Usage:
    # Interactive mode
    python research_agent.py
    
    # Single query mode
    python research_agent.py --query "Create a Google Doc about AI trends"
"""

import os
import sys
from pathlib import Path

# Load environment from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ Loaded environment from {env_path}")
except ImportError:
    pass

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver

from langchain_arcade import ToolManager


SYSTEM_PROMPT_TEMPLATE = """You are a research assistant. When given a topic, do these steps IN ORDER:

STEP 1: Search the web using Search_SearchGoogle tool to find real, current information about the topic.
        Do 2-3 searches with different queries to get comprehensive results.

STEP 2: Create a Google Doc using Google_CreateDocumentFromText with:
        - title: "[Topic] Research Report"
        - text_content: A detailed report based on the ACTUAL search results. Include:
          * Executive Summary
          * Key Findings (cite sources from search results)
          * Details and Analysis
          * Conclusion

STEP 3: Send the document link via email using Google_SendEmail:
        - recipient: {recipient_email}
        - subject: "Research Report: [Topic]"
        - body: "Here is your research report on [Topic]: [document URL]"

IMPORTANT: 
- Use REAL data from web searches, not made-up content
- Execute tools directly, do NOT delegate
- The recipient email is: {recipient_email}"""


def create_agent(manager: ToolManager, recipient_email: str):
    """Create the research agent with tools and model."""
    tools = manager.to_langchain()
    
    # Format system prompt with recipient email
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(recipient_email=recipient_email)
    
    # Select model based on available API key
    if os.environ.get("OPENAI_API_KEY"):
        model = init_chat_model("openai:gpt-4o")
        print("✓ Using OpenAI GPT-4o")
    elif os.environ.get("ANTHROPIC_API_KEY"):
        model = init_chat_model("anthropic:claude-sonnet-4-20250514")
        print("✓ Using Anthropic Claude")
    else:
        raise ValueError("No LLM API key found (OPENAI_API_KEY or ANTHROPIC_API_KEY)")
    
    return create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=MemorySaver(),
    )


def handle_authorization(manager: ToolManager, tool_name: str, user_id: str) -> bool:
    """Handle OAuth authorization for a tool. Returns True if authorized."""
    if not manager.requires_auth(tool_name):
        return True
    
    print(f"\n🔐 Authorization required for: {tool_name}")
    
    auth_response = manager.authorize(tool_name, user_id)
    
    if auth_response.status == "completed":
        print("   ✓ Already authorized!")
        return True
    
    print(f"\n   Please authorize by visiting:")
    print(f"   🔗 {auth_response.url}")
    print(f"\n   Waiting for authorization...")
    
    try:
        manager.wait_for_auth(auth_response.id)
        print("   ✓ Authorization completed!")
        return True
    except KeyboardInterrupt:
        print("\n   ✗ Authorization cancelled")
        return False


def pre_authorize_tools(manager: ToolManager, user_id: str) -> None:
    """Pre-authorize key tools before starting the agent."""
    # These are the main tools the research agent uses
    key_tools = [
        "Search_SearchGoogle",            # Web search for research
        "Google_CreateDocumentFromText",  # Create research reports
        "Google_SendEmail",               # Email the reports
    ]
    
    print("\n📋 Checking tool authorizations...")
    
    for tool_name in key_tools:
        if tool_name in manager.tools:
            if not handle_authorization(manager, tool_name, user_id):
                print(f"   ⚠️  Skipping {tool_name} - not authorized")
        else:
            print(f"   ⚠️  Tool {tool_name} not available")


def run_agent(manager: ToolManager, agent, user_id: str, query: str) -> None:
    """Run the agent with a query and display results."""
    config = {
        "configurable": {
            "thread_id": "research-session",
            "user_id": user_id,
        },
        "recursion_limit": 50,
    }
    
    print(f"\n{'─' * 60}")
    print(f"📝 Query: {query}")
    print(f"{'─' * 60}\n")
    
    try:
        for chunk in agent.stream(
            {"messages": [{"role": "user", "content": query}]},
            config=config,
            stream_mode="values",
        ):
            messages = chunk.get("messages", [])
            if not messages:
                continue
                
            last_msg = messages[-1]
            
            if last_msg.type == "tool":
                tool_name = getattr(last_msg, "name", "unknown")
                
                # Skip internal planning tools
                if tool_name in ("task", "delegate", "plan"):
                    continue
                
                # Simple status indicator
                content = str(getattr(last_msg, "content", ""))
                status = "⚠️" if "error" in content.lower() else "✓"
                print(f"   {status} {tool_name}")
            
            elif last_msg.type == "ai" and not getattr(last_msg, "tool_calls", None):
                content = getattr(last_msg, "content", "")
                if content:
                    print(f"\n🤖 Agent: {content}\n")
                    
    except Exception as e:
        if "authorization" in str(e).lower():
            print(f"\n🔐 Authorization needed. Please complete OAuth and retry.\n")
        else:
            print(f"\n❌ Error: {e}\n")


def interactive_mode(manager: ToolManager, agent, user_id: str, recipient_email: str) -> None:
    """Run the agent in interactive mode."""
    print(f"\n{'=' * 60}")
    print("🔬 Research Agent - Interactive Mode")
    print(f"{'=' * 60}")
    print(f"\n📧 User: {user_id}")
    print(f"📬 Reports sent to: {recipient_email}")
    print("\nExamples:")
    print("  • Research the latest trends in AI chips")
    print("  • Research power banks released in 2025")
    print("  • Research electric vehicle market in Europe")
    print("\nThe agent will create a Google Doc and email it to you.")
    print("Type 'quit' to exit.\n")
    
    while True:
        try:
            query = input("You: ").strip()
            
            if query.lower() in ("quit", "exit", "q"):
                print("\nGoodbye! 👋")
                break
            
            if not query:
                continue
            
            run_agent(manager, agent, user_id, query)
            
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break


def main() -> None:
    """Main entry point."""
    # Validate environment
    missing = []
    if not os.environ.get("ARCADE_API_KEY"):
        missing.append("ARCADE_API_KEY (get at https://arcade.dev)")
    if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
        missing.append("OPENAI_API_KEY or ANTHROPIC_API_KEY")
    
    if missing:
        print("❌ Missing required environment variables:")
        for var in missing:
            print(f"   • {var}")
        sys.exit(1)
    
    user_id = os.environ.get("USER_EMAIL", "user@example.com")
    recipient_email = os.environ.get("RECIPIENT_EMAIL", user_id)
    
    print(f"\n📧 User (OAuth): {user_id}")
    print(f"📬 Recipient: {recipient_email}")
    
    # Initialize tool manager and load tools
    print("\n🚀 Initializing Research Agent...")
    manager = ToolManager()
    # Search: web search, Google: Docs, Gmail: email
    manager.init_tools(toolkits=["Search", "Google", "Gmail"])
    print(f"✓ Loaded {len(manager.tools)} tools")
    
    # Pre-authorize key tools
    pre_authorize_tools(manager, user_id)
    
    # Create agent
    agent = create_agent(manager, recipient_email)
    print("✓ Agent ready!")
    print(f"✓ Reports will be sent to: {recipient_email}")
    
    # Run in appropriate mode
    if len(sys.argv) > 1 and sys.argv[1] == "--query":
        if len(sys.argv) > 2:
            query = " ".join(sys.argv[2:])
            run_agent(manager, agent, user_id, query)
        else:
            print("Usage: python research_agent.py --query 'Research topic here'")
            sys.exit(1)
    else:
        interactive_mode(manager, agent, user_id, recipient_email)


if __name__ == "__main__":
    main()
