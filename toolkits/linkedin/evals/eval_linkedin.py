from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_linkedin
from arcade_linkedin.tools.share import create_text_post

rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_linkedin)


@tool_eval()
def linkedin_eval_suite():
    suite = EvalSuite(
        name="LinkedIn Tools Evaluation",
        system_message="You are an AI assistant with access to LinkedIn tools. Use them to help the user with their tasks.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Run code",
        user_message="post this transcription to linkedin. there may be some things that you need to clean up since it was spoken.: 'It is with great pleasure that I announce that I am now a member of the LinkedIn community! I'd like to thank the LinkedIn team for their support and encouragement in my journey to success. hash tag Y2K'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_text_post,
                args={
                    "text": "It is with great pleasure that I announce that I am now a member of the LinkedIn community! I'd like to thank the LinkedIn team for their support and encouragement in my journey to success. #Y2K",
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="text", weight=1.0),
        ],
    )

    return suite
