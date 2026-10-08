from arcade_core import ToolCatalog
from arcade_evals import (
    CompletenessCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    IntentionCritic,
    SemanticSimilarityCritic,
    tool_eval,
)

import server_with_evaluations
from server_with_evaluations.tools import create_email_subject, write_product_description

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)

catalog = ToolCatalog()

# Add all of the tools in the server_with_evaluations module to the catalog
catalog.add_module(server_with_evaluations)


@tool_eval()
def server_with_evaluations_jev_eval_suite() -> EvalSuite:
    """
    Create an evaluation suite for text tools using Jev judge critics.

    Unlike SimilarityCritic (TF-IDF lexical overlap), these critics ask a
    judge for semantic verdicts:

    - SemanticSimilarityCritic: same meaning / paraphrase (Jev Score).
    - IntentionCritic: the argument fulfills a declared intent, e.g. tone
      or purpose (Jev Noul).
    - CompletenessCritic: every required item in expected appears in actual
      (Jev Score). Catches omissions that paraphrase-level similarity passes.

    Each critic explicitly selects provider="jev". Live judgment requires
    JEV_API_KEY or TYPESAFE_API_KEY. Missing credentials or an unavailable
    judge withhold judgment; no fallback is enabled. Running the suite also
    requires the model provider that generates the tool calls being evaluated.
    """
    suite = EvalSuite(
        name="Jev Judge Tools Evaluation",
        catalog=catalog,
        system_message="You are a helpful assistant for text analysis and summarization.",
        rubric=rubric,
    )

    # Paraphrase is fine; wrong tone is not.
    suite.add_case(
        name="Create email subject",
        user_message="Create an email subject using the tools accessible to you for trees in west coast content",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_email_subject,
                args={
                    "email_content": "Trees in the West Coast",
                    "tone": "professional",
                },
            )
        ],
        critics=[
            SemanticSimilarityCritic(
                critic_field="email_content",
                weight=0.6,
                provider="jev",
                match_threshold=0.7,
            ),
            IntentionCritic(
                critic_field="tone",
                weight=0.4,
                provider="jev",
                intent="Professional tone for a business email",
                match_threshold=0.7,
            ),
        ],
    )

    # Dropped features must fail even when the rest reads like a paraphrase.
    suite.add_case(
        name="Write product description for fitness tracker",
        user_message="Write a product description for a fitness tracker. The key features are heart rate monitoring and GPS tracking. Target audience is outdoor enthusiasts.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=write_product_description,
                args={
                    "main_features": "heart rate monitoring and GPS tracking",
                    "target_audience": "outdoor enthusiasts",
                },
            )
        ],
        critics=[
            CompletenessCritic(
                critic_field="main_features",
                weight=0.6,
                provider="jev",
                match_threshold=0.7,
            ),
            SemanticSimilarityCritic(
                critic_field="target_audience",
                weight=0.4,
                provider="jev",
                match_threshold=0.7,
            ),
        ],
    )

    return suite
