import os

SALESFORCE_API_VERSION = "v63.0"

DEFAULT_MAX_CONCURRENT_REQUESTS = 3
try:
    MAX_CONCURRENT_REQUESTS = int(
        os.getenv("ARCADE_SALESFORCE_MAX_CONCURRENT_REQUESTS", DEFAULT_MAX_CONCURRENT_REQUESTS)
    )
except ValueError:
    MAX_CONCURRENT_REQUESTS = DEFAULT_MAX_CONCURRENT_REQUESTS

ASSOCIATION_REFERENCE_FIELDS = [
    "AccountId",
    "OwnerId",
    "AssociatedToWhom",
    "ContactId",
]

GLOBALLY_IGNORED_FIELDS = [
    "attributes",
    "CleanStatus",
    "CreatedById",
    "CreatedDate",
    "IsDeleted",
    "LastModifiedById",
    "LastModifiedDate",
    "LastReferencedDate",
    "LastViewedDate",
    "PhotoUrl",
    "SystemModstamp",
    "WhatId",
]
