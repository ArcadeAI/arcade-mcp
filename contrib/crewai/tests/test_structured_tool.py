import pytest
from crewai import Agent, Crew, Task
from crewai_arcade.structured import StructuredTool
from pydantic import BaseModel


class CalculatorInput(BaseModel):
    x: float
    y: float


def add_numbers(x: float, y: float) -> float:
    """Add two numbers together."""
    return x + y


def unnamed_function(x: float, y: float) -> float:
    return x + y


def test_structured_tool_basic():
    # Test basic functionality with explicit name and description
    calculator_tool = StructuredTool.from_function(
        func=add_numbers,
        args_schema=CalculatorInput,
        name="Calculator",
        description="A tool that adds two numbers together",
    )

    expected_description = (
        "Tool Name: Calculator\n"
        "Tool Arguments: {'x': {'description': None, 'type': 'float'}, 'y': {'description': None, 'type': 'float'}}\n"
        "Tool Description: A tool that adds two numbers together"
    )
    assert calculator_tool.description == expected_description
    assert calculator_tool.func(2, 3) == 5


def test_structured_tool_auto_name_description():
    # Test automatic name and description generation from function
    calculator_tool = StructuredTool.from_function(func=add_numbers, args_schema=CalculatorInput)

    expected_description = (
        "Tool Name: add_numbers\n"
        "Tool Arguments: {'x': {'description': None, 'type': 'float'}, 'y': {'description': None, 'type': 'float'}}\n"
        "Tool Description: Add two numbers together."
    )
    assert calculator_tool.description == expected_description


def test_structured_tool_validation_errors():
    # Test missing docstring
    with pytest.raises(
        ValueError, match=r"Function must have a docstring if description not provided\."
    ):
        StructuredTool.from_function(func=unnamed_function, args_schema=CalculatorInput)


def test_structured_tool_in_crew():
    calculator_tool = StructuredTool.from_function(
        func=add_numbers,
        args_schema=CalculatorInput,
    )

    calculator_agent = Agent(
        role="Math Expert",
        goal="Perform mathematical calculations accurately",
        backstory="An expert mathematician who specializes in calculations",
        tools=[calculator_tool],
        verbose=True,
        cache=False,
    )

    addition_task = Task(
        description="Add the numbers 5 and 3 together",
        expected_output="The sum of 5 and 3 is 8",
        agent=calculator_agent,
    )

    crew = Crew(
        agents=[calculator_agent],
        tasks=[addition_task],
    )

    # Assert crew structure
    assert len(crew.agents) == 1
    assert len(crew.tasks) == 1
    assert crew.agents[0] == calculator_agent
    assert crew.tasks[0] == addition_task
    assert crew.tasks[0].agent == calculator_agent
    assert len(crew.agents[0].tools) == 1
    assert isinstance(crew.agents[0].tools[0], StructuredTool)
