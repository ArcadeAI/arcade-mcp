from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_teams
from arcade_teams.tools.channel import get_channel_message_replies

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def get_channel_message_replies_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools getting channel message replies in Teams."""
    suite = EvalSuite(
        name="Teams Channel Tools Evaluation",
        system_message=(
            "You are an AI assistant that can interact with Teams to "
            "send messages and get information from chats, channels, users, etc. "
            "Today is 2025-07-21."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get channel message replies",
        user_message=(
            "Get the replies to the message with id 3b07649f-79ff-4f5b-9b6d-e85dca4f18d7 "
            "in the general channel"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_channel_message_replies,
                args={
                    "message_id": "3b07649f-79ff-4f5b-9b6d-e85dca4f18d7",
                    "channel_id_or_name": "general",
                    "team_id_or_name": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="message_id", weight=0.4),
            BinaryCritic(critic_field="channel_id_or_name", weight=0.4),
            BinaryCritic(critic_field="team_id_or_name", weight=0.2),
        ],
    )

    suite.add_case(
        name="Get channel message replies in team",
        user_message=(
            "Get the replies to the message with id 3b07649f-79ff-4f5b-9b6d-e85dca4f18d7 "
            "in the general channel from the engineering team"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_channel_message_replies,
                args={
                    "message_id": "3b07649f-79ff-4f5b-9b6d-e85dca4f18d7",
                    "channel_id_or_name": "general",
                    "team_id_or_name": "engineering",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="message_id", weight=1 / 3),
            BinaryCritic(critic_field="channel_id_or_name", weight=1 / 3),
            BinaryCritic(critic_field="team_id_or_name", weight=1 / 3),
        ],
    )

    # suite.add_case(
    #     name="Get channel message replies with chat history",
    #     user_message="Get the replies to the last message",
    #     expected_tool_calls=[
    #         ExpectedToolCall(
    #             func=get_channel_message_replies,
    #             args={
    #                 "message_id": "3b07649f-79ff-4f5b-9b6d-e85dca4f18d7",
    #                 "channel_id_or_name": "general",
    #                 "team_id_or_name": None,
    #             },
    #         ),
    #     ],
    #     critics=[
    #         BinaryCritic(critic_field="message_id", weight=0.4),
    #         BinaryCritic(critic_field="channel_id_or_name", weight=0.4),
    #         BinaryCritic(critic_field="team_id_or_name", weight=0.2),
    #     ],
    #     additional_messages=[
    #         {
    #             "role": "user",
    #             "content": "get the last 2 messages from the 'project-acme' channel",
    #         },
    #         {
    #             "role": "assistant",
    #             "content": "",
    #             "tool_calls": [
    #                 {
    #                     "id": "call_1",
    #                     "type": "function",
    #                     "function": {
    #                         "name": "Teams_GetChannelMessages",
    #                         "arguments": json.dumps({
    #                             "channel_name": "project-acme",
    #                             "limit": 2,
    #                         }),
    #                     },
    #                 }
    #             ],
    #         },
    #         {
    #             "role": "tool",
    #             "content": json.dumps({
    #                 "count": 2,
    #                 "messages": [
    #                     {
    #                         "object_type": "message",
    #                         "id": "3b07649f-79ff-4f5b-9b6d-e85dca4f18d7",
    #                         "author": {"user_id": "user2", "user_name": "John Doe"},
    #                         "created_at": "2025-07-21T12:00:00",
    #                         "content": {
    #                             "text": "I'm currently blocked, can someone help me?",
    #                             "type": "text",
    #                         },
    #                     },
    #                     {
    #                         "object_type": "message",
    #                         "id": "68fd82d3-5b26-4028-b187-01fd9485eb6c",
    #                         "author": {"user_id": "user1", "user_name": "Jane Foo"},
    #                         "created_at": "2025-07-21T11:55:00",
    #                         "content": {
    #                             "text": "What's the status of the project?",
    #                             "type": "text",
    #                         },
    #                     },
    #                 ],
    #             }),
    #             "tool_call_id": "call_1",
    #             "name": "Teams_GetChannelMessages",
    #         },
    #         {
    #             "role": "assistant",
    #             "content": (
    #                 "Here are the last 2 messages from the 'project-acme' channel:\n\n"
    #                 "1. **Jane Foo** (2025-07-21 11:55:00): What's the status of the project?\n"
    #                 "2. **John Doe** (2025-07-21 12:00:00): I'm currently blocked, can someone "
    #                 "help me?\n\n"
    #                 "If you need more information or additional messages, feel free to ask!",
    #             ),
    #         },
    #     ],
    # )

    return suite
