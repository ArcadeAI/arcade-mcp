from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

from arcade_microsoft.outlook_calendar import get_event
from evals.outlook_calendar.additional_messages import get_event_additional_messages

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_tool(get_event, "Microsoft")


@tool_eval()
def outlook_calendar_get_event_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Outlook Calendar get event tool."""
    suite = EvalSuite(
        name="Outlook Calendar Get Event Evaluation",
        system_message=(
            "You are an AI that has access to tools to view and manage calendar events. "
            "The current time date and time is April 25, 2025, 5:18 PM PST."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get event by id after listing events",
        user_message="tell me more about the first event",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_event,
                args={
                    "event_id": "AAMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoARgAAAyXxSd3UxTpCkDpGouEg0JMBAFuxokOLZRtDncM4",  # noqa: E501
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="event_id", weight=1.0),
        ],
        additional_messages=get_event_additional_messages,
    )

    return suite
