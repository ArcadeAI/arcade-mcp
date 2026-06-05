from arcade_core import ToolCatalog
from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)

import servicenow
from servicenow.tools import (
    change_state,
    create_incident,
    search_incidents,
)

rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(servicenow)


@tool_eval()
def servicenow_incident_eval_suite() -> EvalSuite:
    """
    Evaluation suite for ServiceNow incident management tools.

    Covers three core workflows:
    - Creating incidents (text similarity for description, exact match for priority fields)
    - Searching incidents (exact match on structured filter fields)
    - Changing incident state (exact match on state and INC number)
    """
    suite = EvalSuite(
        name="ServiceNow Incident Management Evaluation",
        catalog=catalog,
        system_message=(
            "You are a helpful IT support assistant with access to ServiceNow. "
            "Use the available tools to manage incidents on behalf of the user."
        ),
        rubric=rubric,
    )

    # -------------------------------------------------------------------------
    # create_incident — SimilarityCritic for description text, BinaryCritic for
    # structured fields where exact correctness matters.
    # -------------------------------------------------------------------------
    suite.add_case(
        name="Create high-urgency incident for VPN outage",
        user_message=(
            "Please create a new incident. Users are unable to connect to the VPN "
            "which is blocking remote work. This is high urgency and high impact."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_incident,
                args={
                    "short_description": "Users unable to connect to VPN",
                    "urgency": "high",
                    "impact": "high",
                },
            )
        ],
        critics=[
            SimilarityCritic(
                critic_field="short_description",
                weight=0.5,
                similarity_threshold=0.7,
                metric="cosine",
            ),
            BinaryCritic(critic_field="urgency", weight=0.25),
            BinaryCritic(critic_field="impact", weight=0.25),
        ],
    )

    suite.add_case(
        name="Create a low-priority software request with category",
        user_message=(
            "Log an incident: a developer needs the Python extension installed in VS Code. "
            "It's low urgency. Category is software."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_incident,
                args={
                    "short_description": "Python extension needed in VS Code",
                    "urgency": "low",
                    "category": "software",
                },
            )
        ],
        critics=[
            SimilarityCritic(
                critic_field="short_description",
                weight=0.5,
                similarity_threshold=0.65,
                metric="cosine",
            ),
            BinaryCritic(critic_field="urgency", weight=0.3),
            BinaryCritic(critic_field="category", weight=0.2),
        ],
    )

    # -------------------------------------------------------------------------
    # search_incidents — BinaryCritic for structured enum/code fields.
    # -------------------------------------------------------------------------
    suite.add_case(
        name="Search for all critical new incidents",
        user_message="Show me all critical priority incidents that are new and haven't been picked up yet.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_incidents,
                args={
                    "priority": "critical",
                    "state": "new",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="priority", weight=0.6),
            BinaryCritic(critic_field="state", weight=0.4),
        ],
    )

    suite.add_case(
        name="Search for high priority incidents in progress",
        user_message="Find all high priority incidents that are currently being worked on (in progress).",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_incidents,
                args={
                    "priority": "high",
                    "state": "in_progress",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="priority", weight=0.6),
            BinaryCritic(critic_field="state", weight=0.4),
        ],
    )

    suite.add_case(
        name="Search incidents by keyword",
        user_message="Find incidents related to database connectivity issues.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_incidents,
                args={
                    "short_description_contains": "database connectivity",
                },
            )
        ],
        critics=[
            SimilarityCritic(
                critic_field="short_description_contains",
                weight=1.0,
                similarity_threshold=0.65,
                metric="cosine",
            ),
        ],
    )

    # -------------------------------------------------------------------------
    # change_state — BinaryCritic for state transition and INC number.
    # SimilarityCritic for free-text close notes.
    # -------------------------------------------------------------------------
    suite.add_case(
        name="Resolve incident INC0045678",
        user_message=(
            "Please resolve incident INC0045678. "
            "The issue was fixed by restarting the network switch."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=change_state,
                args={
                    "sys_id_or_number": "INC0045678",
                    "state": "resolved",
                    "close_notes": "Issue resolved by restarting the network switch.",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="sys_id_or_number", weight=0.4),
            BinaryCritic(critic_field="state", weight=0.3),
            SimilarityCritic(
                critic_field="close_notes",
                weight=0.3,
                similarity_threshold=0.7,
                metric="cosine",
            ),
        ],
    )

    return suite
