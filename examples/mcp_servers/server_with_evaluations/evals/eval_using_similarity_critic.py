from arcade_core import ToolCatalog
from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
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
def server_with_evaluations_similarity_eval_suite() -> EvalSuite:
    """
    Create an evaluation suite for text tools using SimilarityCritic.

    SimilarityCritic evaluates the TEXT INPUTS/ARGUMENTS passed to tools,
    not the tool results. It's useful when:
    - The model needs to paraphrase or reword user requests as tool arguments
    - Content description varies in wording but carries the same meaning
    - Multiple valid ways exist to express the same concept
    - You want to check semantic similarity rather than exact text match

    Example: User says "email about trees on west coast" → model might call
    tool with "West Coast Trees" or "Trees of the Western Coast" - both valid!
    """
    suite = EvalSuite(
        name="Similarity Tools Evaluation",
        catalog=catalog,
        system_message="You are a helpful assistant for text analysis and summarization.",
        rubric=rubric,
    )

    # The model might rephrase "trees in the west coast" in various ways
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
            SimilarityCritic(
                critic_field="email_content",
                weight=1.0,
                similarity_threshold=0.75,  # Allow for paraphrasing
                metric="cosine",
            )
        ],
    )

    # Model might rephrase features in different ways while keeping the same meaning
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
            SimilarityCritic(
                critic_field="main_features",
                weight=0.6,
                similarity_threshold=0.7,  # Slightly lower threshold for feature lists
                metric="cosine",
            ),
            SimilarityCritic(
                critic_field="target_audience",
                weight=0.4,
                similarity_threshold=0.75,
                metric="cosine",
            ),
        ],
    )

    return suite
