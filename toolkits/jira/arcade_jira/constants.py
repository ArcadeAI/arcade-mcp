import os

JIRA_BASE_URL = "https://api.atlassian.com/ex/jira"
JIRA_API_VERSION = "3"

try:
    JIRA_MAX_CONCURRENT_REQUESTS = int(os.getenv("JIRA_MAX_CONCURRENT_REQUESTS", 3))
except Exception:
    JIRA_MAX_CONCURRENT_REQUESTS = 3
