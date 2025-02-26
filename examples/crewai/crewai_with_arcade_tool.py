"""

This is an example of how to use Arcade with CrewAI.
The ArcadeToolManager allows you to handle both authorization and tool execution in a custom way.
This example demonstrates how to implement a custom auth handler and a custom tool execute handler.

The example assumes the following:
1. You have an Arcade API key and have set the ARCADE_API_KEY environment variable.
2. You have an OpenAI API key and have set the OPENAI_API_KEY environment variable.
3. You have installed the necessary dependencies in the requirements.txt file: `pip install -r requirements.txt`

"""

from typing import Any

from crewai import Agent, Crew, Task
from crewai.crews import CrewOutput
from crewai.llm import LLM
from crewai_arcade import ArcadeToolManager

USER_ID = "user@example.com"


def custom_auth_flow(
    manager: ArcadeToolManager, tool_name: str, **tool_input: dict[str, Any]
) -> Any:
    """Custom auth flow for the ArcadeToolManager

    This function is called when CrewAI needs to call a tool that requires authorization.
    Authorization is handled before executing the tool.
    This function overrides the ArcadeToolManager's default auth flow performed by ArcadeToolManager.authorize_tool
    """
    # Get authorization status
    auth_response = manager.authorize(tool_name, USER_ID)

    # If the user is not authorized for the tool,
    # then we need to handle the authorization before executing the tool
    if not manager.is_authorized(auth_response.id):
        print(f"Authorization required for tool: '{tool_name}' with inputs:")
        for input_name, input_value in tool_input.items():
            print(f"  {input_name}: {input_value}")
        # Handle authorization
        print(f"\nTo authorize, visit: {auth_response.url}")
        # Block until the user has completed the authorization
        auth_response = manager.wait_for_auth(auth_response)

        # Ensure authorization completed successfully
        if not manager.is_authorized(auth_response.id):
            raise ValueError(f"Authorization failed for {tool_name}. URL: {auth_response.url}")
    else:
        print(f"Authorization already granted for tool: '{tool_name}' with inputs:")
        for input_name, input_value in tool_input.items():
            print(f"  {input_name}: {input_value}")


def custom_execute_flow(
    manager: ArcadeToolManager, tool_name: str, **tool_input: dict[str, Any]
) -> Any:
    """Custom tool execution flow for the ArcadeToolManager

    This function is called when CrewAI needs to execute a tool after any authorization has been handled.
    This function overrides the ArcadeToolManager's default tool execution flow performed by ArcadeToolManager.execute_tool
    """
    print(f"Executing tool: '{tool_name}' with inputs:")
    for input_name, input_value in tool_input.items():
        print(f"  {input_name}: {input_value}")

    # Execute the tool
    response = manager._client.tools.execute(
        tool_name=tool_name,
        input=tool_input,
        user_id=USER_ID,
    )

    # Handle the tool error if it exists
    tool_error = response.output.error if response.output else None
    if tool_error:
        return str(tool_error)

    # Return the tool output if the tool was executed successfully
    if response.success:
        return response.output.value  # type: ignore[union-attr]

    # Return a failure message if the tool was not executed successfully
    return "Failed to call " + tool_name


def custom_tool_executor(
    manager: ArcadeToolManager, tool_name: str, **tool_input: dict[str, Any]
) -> Any:
    """Custom tool executor for the ArcadeToolManager

    ArcadeToolManager's default executor handles authorization and tool execution.
    This function overrides the default executor to handle authorization and tool execution in a custom way.
    """
    custom_auth_flow(manager, tool_name, **tool_input)
    return custom_execute_flow(manager, tool_name, **tool_input)


def main() -> CrewOutput:
    manager = ArcadeToolManager(
        executor=custom_tool_executor,
    )
    tools = manager.get_tools(tools=["Google.ListEmails"])

    crew_agent = Agent(
        role="Main Agent",
        backstory="You are a helpful assistant",
        goal="Help the user with their requests",
        tools=tools,
        allow_delegation=False,
        verbose=True,
        llm=LLM(model="gpt-4o"),
    )

    task = Task(
        description="Get the 5 most recent emails from the user's inbox and summarize them and recommend a response for each.",
        expected_output="A bulleted list with a one sentence summary of each email and a recommended response to the email.",
        agent=crew_agent,
        tools=crew_agent.tools,
    )

    crew = Crew(
        agents=[crew_agent],
        tasks=[task],
        verbose=True,
        memory=True,
    )

    result = crew.kickoff()
    return result


if __name__ == "__main__":
    result = main()
    print("\n\n\n ------------ Result ------------ \n\n\n")
    print(result)
