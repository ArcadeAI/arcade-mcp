from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    NumericCritic,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_web
from arcade_web.tools.firecrawl import (
    cancel_crawl,
    crawl_website,
    get_crawl_data,
    get_crawl_status,
    map_website,
    scrape_url,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
# Register the Firecrawl tools
catalog.add_module(arcade_web)


@tool_eval()
def firecrawl_eval_suite() -> EvalSuite:
    """Evaluation suite for Firecrawl tools."""
    suite = EvalSuite(
        name="Firecrawl Tools Evaluation Suite",
        system_message="You are an AI assistant that helps users interact with web scraping and crawling tools using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    # Scrape URL
    suite.add_case(
        name="Scrape a URL",
        user_message="Scrape https://foobar.com/malicious/malware/that/will/harm/you in markdown format please. Wait for 10 seconds before fetching the content.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=scrape_url,
                args={
                    "url": "https://foobar.com/malicious/malware/that/will/harm/you",
                    "formats": ["markdown"],
                    "wait_for": 10000,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="url", weight=0.4),
            BinaryCritic(critic_field="formats", weight=0.4),
            NumericCritic(critic_field="wait_for", weight=0.2, value_range=(9000, 11000)),
        ],
    )

    # Crawl Website
    suite.add_case(
        name="Crawl a website",
        user_message="Crawl the website at https://wikipedia.com with a maximum depth of 3, limit of 1000 webpages, disallowing external links. Updates should be sent to http://example.com/crawl-updates. Oh and do it in the background. THanks",
        expected_tool_calls=[
            ExpectedToolCall(
                func=crawl_website,
                args={
                    "url": "https://wikipedia.com",
                    "max_depth": 3,
                    "limit": 1000,
                    "allow_external_links": False,
                    "webhook": "http://example.com/crawl-updates",
                    "async_crawl": True,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="url", weight=0.2),
            BinaryCritic(critic_field="max_depth", weight=0.1),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="allow_external_links", weight=0.1),
            BinaryCritic(critic_field="webhook", weight=0.2),
            BinaryCritic(critic_field="async_crawl", weight=0.2),
        ],
    )

    # Get Crawl Status
    suite.add_case(
        name="Get crawl status",
        user_message="Check the status of my crawl",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_crawl_status,
                args={
                    "crawl_id": "2ee7ba77-4ba0-4a45-9e2f-1c9e9a56f29b",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="crawl_id", weight=1.0),
        ],
        additional_messages=[
            {"role": "user", "content": "crawl asynchronously https://www.google.com"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_QklpRSDmHdvM3ZZfzOqCKWRN",
                        "type": "function",
                        "function": {
                            "name": "Web_CrawlWebsite",
                            "arguments": '{"url":"https://www.google.com","async_crawl":true}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": '{"id":"2ee7ba77-4ba0-4a45-9e2f-1c9e9a56f29b","success":true,"url":"https://api.firecrawl.dev/v1/crawl/2ee7ba77-4ba0-4a45-9e2f-1c9e9a56f29b"}',
                "tool_call_id": "call_QklpRSDmHdvM3ZZfzOqCKWRN",
                "name": "Web_CrawlWebsite",
            },
            {
                "role": "assistant",
                "content": "The asynchronous web crawl request for [Google](https://www.google.com) has been successfully initiated. You can track the status or fetch the results using the following [link](https://api.firecrawl.dev/v1/crawl/2ee7ba77-4ba0-4a45-9e2f-1c9e9a56f29b).",
            },
        ],
    )

    # # Get Crawl Data
    suite.add_case(
        name="Get crawl status",
        user_message="Ok looks like the crawl is done, can I get the result please?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_crawl_data,
                args={
                    "crawl_id": "2ee7ba77-4ba0-4a45-9e2f-1c9e9a56f29b",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="crawl_id", weight=1.0),
        ],
        additional_messages=[
            {"role": "user", "content": "crawl asynchronously https://www.google.com"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_QklpRSDmHdvM3ZZfzOqCKWRN",
                        "type": "function",
                        "function": {
                            "name": "Web_CrawlWebsite",
                            "arguments": '{"url":"https://www.google.com","async_crawl":true}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": '{"id":"2ee7ba77-4ba0-4a45-9e2f-1c9e9a56f29b","success":true,"url":"https://api.firecrawl.dev/v1/crawl/2ee7ba77-4ba0-4a45-9e2f-1c9e9a56f29b"}',
                "tool_call_id": "call_QklpRSDmHdvM3ZZfzOqCKWRN",
                "name": "Web_CrawlWebsite",
            },
            {
                "role": "assistant",
                "content": "The asynchronous web crawl request for [Google](https://www.google.com) has been successfully initiated. You can track the status or fetch the results using the following [link](https://api.firecrawl.dev/v1/crawl/2ee7ba77-4ba0-4a45-9e2f-1c9e9a56f29b).",
            },
        ],
    )

    # Cancel Crawl
    suite.add_case(
        name="Get crawl status",
        user_message="Actually cancel it.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=cancel_crawl,
                args={
                    "crawl_id": "2ee7ba77-4ba0-4a45-9e2f-1c9e9a56f29b",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="crawl_id", weight=1.0),
        ],
        additional_messages=[
            {"role": "user", "content": "crawl asynchronously https://www.google.com"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_QklpRSDmHdvM3ZZfzOqCKWRN",
                        "type": "function",
                        "function": {
                            "name": "Web_CrawlWebsite",
                            "arguments": '{"url":"https://www.google.com","async_crawl":true}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": '{"id":"2ee7ba77-4ba0-4a45-9e2f-1c9e9a56f29b","success":true,"url":"https://api.firecrawl.dev/v1/crawl/2ee7ba77-4ba0-4a45-9e2f-1c9e9a56f29b"}',
                "tool_call_id": "call_QklpRSDmHdvM3ZZfzOqCKWRN",
                "name": "Web_CrawlWebsite",
            },
            {
                "role": "assistant",
                "content": "The asynchronous web crawl request for [Google](https://www.google.com) has been successfully initiated. You can track the status or fetch the results using the following [link](https://api.firecrawl.dev/v1/crawl/2ee7ba77-4ba0-4a45-9e2f-1c9e9a56f29b).",
            },
        ],
    )

    # Map Website
    suite.add_case(
        name="Map a website",
        user_message="Map the website at https://wikipedia.com with a limit of 100000 links. Only the links that are about the topic of AI",
        expected_tool_calls=[
            ExpectedToolCall(
                func=map_website,
                args={
                    "url": "https://wikipedia.com",
                    "search": "AI",
                    "limit": 100000,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="url", weight=0.4),
            SimilarityCritic(critic_field="search", weight=0.2),
            NumericCritic(critic_field="limit", weight=0.4, value_range=(90000, 110000)),
        ],
    )

    return suite
