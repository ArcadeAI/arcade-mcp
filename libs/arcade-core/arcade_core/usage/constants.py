# Base (common) Property Names
PROP_RUNTIME_LANGUAGE = "runtime_language"
PROP_RUNTIME_VERSION = "runtime_version"
PROP_OS_TYPE = "os_type"
PROP_OS_RELEASE = "os_release"
PROP_DURATION_MS = "duration_ms"
PROP_ERROR_MESSAGE = "error_message"
PROP_DEVICE_MONOTONIC_START = "device_start_timestamp"
PROP_DEVICE_MONOTONIC_END = "device_end_timestamp"
PROP_DEVICE_TIMESTAMP = "device_timestamp"
# Only used for anonymous usage
PROP_PROCESS_PERSON_PROFILE = "$process_person_profile"

# Identity Keys
KEY_ANON_ID = "anon_id"
KEY_LINKED_PRINCIPAL_ID = "linked_principal_id"

# File Names
USAGE_FILE_NAME = "usage.json"

# Environment Variables
# how props are passed to the usage tracking subprocess
ARCADE_USAGE_EVENT_DATA = "ARCADE_USAGE_EVENT_DATA"
# whether usage tracking is enabled. 1 is enabled, 0 is disabled.
ARCADE_USAGE_TRACKING = "ARCADE_USAGE_TRACKING"

# Timeouts and Limits (in seconds)
TIMEOUT_POSTHOG_ALIAS = 2
TIMEOUT_POSTHOG_CAPTURE = 5
TIMEOUT_ARCADE_API = 2.0
TIMEOUT_SUBPROCESS_EXIT = 10.0

# Retry Configuration
MAX_RETRIES_POSTHOG = 1
