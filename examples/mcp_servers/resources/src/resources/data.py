"""In-memory data for the "Company Knowledge Base" demo."""

KB_ARTICLES: dict[str, dict[str, str]] = {
    "getting-started": {
        "title": "Getting Started",
        "category": "onboarding",
        "author": "docs-team",
        "body": "Welcome to the company knowledge base! Start here to learn the basics.",
    },
    "api-guidelines": {
        "title": "API Design Guidelines",
        "category": "engineering",
        "author": "platform-team",
        "body": "All APIs must follow REST conventions and use JSON payloads.",
    },
    "security-policy": {
        "title": "Security Policy",
        "category": "compliance",
        "author": "security-team",
        "body": "All employees must use MFA and rotate credentials every 90 days.",
    },
}

KB_CATEGORIES: dict[str, list[str]] = {
    "onboarding": ["getting-started"],
    "engineering": ["api-guidelines"],
    "compliance": ["security-policy"],
}
