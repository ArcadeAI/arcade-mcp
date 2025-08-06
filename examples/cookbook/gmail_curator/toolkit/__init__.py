# Gmail curator toolkit
from .gmail_tools import (
    analyze_inbox,
    create_smart_labels,
    find_unsubscribe_candidates,
    generate_filter_rules,
)

__all__ = [
    "analyze_inbox",
    "create_smart_labels",
    "find_unsubscribe_candidates",
    "generate_filter_rules",
]
