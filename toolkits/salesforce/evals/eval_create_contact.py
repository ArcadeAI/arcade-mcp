from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_salesforce
from arcade_salesforce.tools import create_contact

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_salesforce)


@tool_eval()
def create_contact_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="create contact eval suite",
        system_message=(
            "You are an AI assistant with access to Salesforce tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Create contact",
        user_message="Create a contact for the account with ID 001gK000003DIn0QAG with name Jenifer Bear and email jenifer@acme.net.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_contact,
                args={
                    "account_id": "001gK000003DIn0QAG",
                    "last_name": "Bear",
                    "first_name": "Jenifer",
                    "email": "jenifer@acme.net",
                    "phone": None,
                    "mobile_phone": None,
                    "title": None,
                    "department": None,
                    "description": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="account_id", weight=0.2),
            BinaryCritic(critic_field="last_name", weight=0.1),
            BinaryCritic(critic_field="first_name", weight=0.1),
            BinaryCritic(critic_field="email", weight=0.1),
            BinaryCritic(critic_field="phone", weight=0.1),
            BinaryCritic(critic_field="mobile_phone", weight=0.1),
            BinaryCritic(critic_field="title", weight=0.1),
            BinaryCritic(critic_field="department", weight=0.1),
            BinaryCritic(critic_field="description", weight=0.1),
        ],
    )

    suite.add_case(
        name="Create contact with only last name",
        user_message="Create a contact for the account with ID 001gK000003DIn0QAG with name Doe and email doe@acme.net.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_contact,
                args={
                    "account_id": "001gK000003DIn0QAG",
                    "last_name": "Doe",
                    "first_name": None,
                    "email": "doe@acme.net",
                    "phone": None,
                    "mobile_phone": None,
                    "title": None,
                    "department": None,
                    "description": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="account_id", weight=0.2),
            BinaryCritic(critic_field="last_name", weight=0.1),
            BinaryCritic(critic_field="first_name", weight=0.1),
            BinaryCritic(critic_field="email", weight=0.1),
            BinaryCritic(critic_field="phone", weight=0.1),
            BinaryCritic(critic_field="mobile_phone", weight=0.1),
            BinaryCritic(critic_field="title", weight=0.1),
            BinaryCritic(critic_field="department", weight=0.1),
            BinaryCritic(critic_field="description", weight=0.1),
        ],
    )

    return suite
