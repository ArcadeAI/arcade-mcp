from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_teams
from arcade_teams.constants import TeamMembershipType
from arcade_teams.tools.teams import list_teams

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def list_teams_eval_suite() -> EvalSuite:
    """Create an evaluation suite for listing teams tool in MS Teams."""
    suite = EvalSuite(
        name="Listing Teams Tool Evaluation",
        system_message=(
            "You are an AI assistant that can interact with Teams to "
            "send messages and get information from chats, channels, users, etc."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="List teams I'm a member of",
        user_message="To which teams am I a member of?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_teams,
                args={
                    "membership_type": TeamMembershipType.DIRECT_MEMBER,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="membership_type", weight=1.0),
        ],
    )

    suite.add_case(
        name="List teams I'm associated through a shared channel",
        user_message="To which external teams am I associated with?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_teams,
                args={
                    "membership_type": TeamMembershipType.MEMBER_OF_SHARED_CHANNEL,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="membership_type", weight=1.0),
        ],
    )

    suite.add_case(
        name="List teams I'm associated through a shared channel",
        user_message="Am I associated with any external team through a shared channel?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_teams,
                args={
                    "membership_type": TeamMembershipType.MEMBER_OF_SHARED_CHANNEL,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="membership_type", weight=1.0),
        ],
    )

    return suite
