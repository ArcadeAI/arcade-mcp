from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_code_sandbox
from arcade_code_sandbox.tools.e2b import create_static_matplotlib_chart, run_code
from arcade_code_sandbox.tools.models import E2BSupportedLanguage

merge_sort_code = """
def merge_sort(arr):
    if len(arr) <= 1:
        return arr

    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])

    return merge(left, right)

def merge(left, right):
    result = []
    i, j = 0, 0

    while i < len(left) and j < len(right):
        if left[i] < right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1

    result.extend(left[i:])
    result.extend(right[j:])

    return result

sample_list = ["banana", "apple", "cherry", "date", "elderberry"]

sorted_list = merge_sort(sample_list)
print("Sorted list:", sorted_list)
"""

matplotlib_chart_code = """
import matplotlib.pyplot as plt

labels = ['Apples', 'Bananas', 'Cherries', 'Dates']
sizes = [30, 25, 20, 25]
colors = ['red', 'yellow', 'purple', 'brown']

plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)

plt.axis('equal')

plt.title('Fruit Distribution')

plt.savefig('fruit_pie_chart.png')
"""

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_code_sandbox)


@tool_eval()
def code_sandbox_eval_suite():
    suite = EvalSuite(
        name="code_sandbox Tools Evaluation",
        system_message="You are an AI assistant with access to code_sandbox tools. Use them to help the user with their tasks.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Run code",
        user_message=f"Can you please run my merge sort algo?\n\n{merge_sort_code}",
        expected_tool_calls=[
            ExpectedToolCall(
                func=run_code,
                args={
                    "code": merge_sort_code,
                    "language": E2BSupportedLanguage.PYTHON,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="code", weight=0.8),
            BinaryCritic(critic_field="language", weight=0.2),
        ],
    )

    suite.add_case(
        name="Create static matplotlib chart",
        user_message=f"Run this code:\n\n{matplotlib_chart_code}",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_static_matplotlib_chart,
                args={
                    "code": matplotlib_chart_code,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="code", weight=1.0),
        ],
    )

    return suite
