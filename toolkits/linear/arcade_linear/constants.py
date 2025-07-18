import os

LINEAR_API_URL = "https://api.linear.app/graphql"

try:
    LINEAR_MAX_CONCURRENT_REQUESTS = int(os.getenv("LINEAR_MAX_CONCURRENT_REQUESTS", 3))
except ValueError:
    LINEAR_MAX_CONCURRENT_REQUESTS = 3

try:
    LINEAR_MAX_TIMEOUT_SECONDS = int(os.getenv("LINEAR_MAX_TIMEOUT_SECONDS", 30))
except ValueError:
    LINEAR_MAX_TIMEOUT_SECONDS = 30
