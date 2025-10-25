"""Request Body Schemas for API Tools

DO NOT EDIT THIS MODULE DIRECTLY.

THIS MODULE WAS AUTO-GENERATED AND CONTAINS OpenAPI REQUEST BODY SCHEMAS
FOR TOOLS WITH COMPLEX REQUEST BODIES. ANY CHANGES TO THIS MODULE WILL
BE OVERWRITTEN BY THE TRANSPILER.
"""

from typing import Any

REQUEST_BODY_SCHEMAS: dict[str, Any] = {
    "CREATEROLEWITHPERMISSIONS_REQUEST_BODY_SCHEMA": {
        "properties": {
            "name": {"description": "The name (ID) of the role.", "type": "string"},
            "permissions": {
                "items": {
                    "description": "Permissions attached to a role.",
                    "properties": {
                        "action": {
                            "description": "Allowed actions in weaviate.",
                            "enum": [
                                "manage_backups",
                                "read_cluster",
                                "create_data",
                                "read_data",
                                "update_data",
                                "delete_data",
                                "read_nodes",
                                "create_roles",
                                "read_roles",
                                "update_roles",
                                "delete_roles",
                                "create_collections",
                                "read_collections",
                                "update_collections",
                                "delete_collections",
                                "assign_and_revoke_users",
                                "create_users",
                                "read_users",
                                "update_users",
                                "delete_users",
                                "create_tenants",
                                "read_tenants",
                                "update_tenants",
                                "delete_tenants",
                                "create_replicate",
                                "read_replicate",
                                "update_replicate",
                                "delete_replicate",
                                "create_aliases",
                                "read_aliases",
                                "update_aliases",
                                "delete_aliases",
                                "assign_and_revoke_groups",
                                "read_groups",
                            ],
                            "type": "string",
                        },
                        "aliases": {
                            "description": "Resource "
                            "definition "
                            "for "
                            "alias-related "
                            "actions "
                            "and "
                            "permissions. "
                            "Used "
                            "to "
                            "specify "
                            "which "
                            "aliases "
                            "and "
                            "collections "
                            "can "
                            "be "
                            "accessed "
                            "or "
                            "modified.",
                            "properties": {
                                "alias": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "aliases "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "alias "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "aliases.",
                                    "type": "string",
                                },
                                "collection": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "collections "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "collection "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "collections.",
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "backups": {
                            "description": "Resources applicable for backup actions.",
                            "properties": {
                                "collection": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "collections "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "collection "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "collections.",
                                    "type": "string",
                                }
                            },
                            "type": "object",
                        },
                        "collections": {
                            "description": "Resources "
                            "applicable "
                            "for "
                            "collection "
                            "and/or "
                            "tenant "
                            "actions.",
                            "properties": {
                                "collection": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "collections "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "collection "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "collections.",
                                    "type": "string",
                                }
                            },
                            "type": "object",
                        },
                        "data": {
                            "description": "Resources applicable for data actions.",
                            "properties": {
                                "collection": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "collections "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "collection "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "collections.",
                                    "type": "string",
                                },
                                "object": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "objects "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "object "
                                    "ID "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "objects.",
                                    "type": "string",
                                },
                                "tenant": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "tenants "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "tenant "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "tenants.",
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "groups": {
                            "description": "Resources applicable for group actions.",
                            "properties": {
                                "group": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "groups "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "group "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "groups.",
                                    "type": "string",
                                },
                                "groupType": {
                                    "description": "If the group contains OIDC or database users.",
                                    "enum": ["oidc"],
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "nodes": {
                            "description": "Resources applicable for cluster actions.",
                            "properties": {
                                "collection": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "collections "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "collection "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "collections.",
                                    "type": "string",
                                },
                                "verbosity": {
                                    "default": "minimal",
                                    "description": "Whether "
                                    "to "
                                    "allow "
                                    "(verbose) "
                                    "returning "
                                    "shards "
                                    "and "
                                    "stats "
                                    "data "
                                    "in "
                                    "the "
                                    "response.",
                                    "enum": ["verbose", "minimal"],
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "replicate": {
                            "description": "resources applicable for replicate actions",
                            "properties": {
                                "collection": {
                                    "default": "*",
                                    "description": "string "
                                    "or "
                                    "regex. "
                                    "if "
                                    "a "
                                    "specific "
                                    "collection "
                                    "name, "
                                    "if "
                                    "left "
                                    "empty "
                                    "it "
                                    "will "
                                    "be "
                                    "ALL "
                                    "or "
                                    "*",
                                    "type": "string",
                                },
                                "shard": {
                                    "default": "*",
                                    "description": "string "
                                    "or "
                                    "regex. "
                                    "if "
                                    "a "
                                    "specific "
                                    "shard "
                                    "name, "
                                    "if "
                                    "left "
                                    "empty "
                                    "it "
                                    "will "
                                    "be "
                                    "ALL "
                                    "or "
                                    "*",
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "roles": {
                            "description": "Resources applicable for role actions.",
                            "properties": {
                                "role": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "roles "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "role "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "roles.",
                                    "type": "string",
                                },
                                "scope": {
                                    "default": "match",
                                    "description": "Set the scope for the manage role permission.",
                                    "enum": ["all", "match"],
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "tenants": {
                            "description": "Resources applicable for tenant actions.",
                            "properties": {
                                "collection": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "collections "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "collection "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "collections.",
                                    "type": "string",
                                },
                                "tenant": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "tenants "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "tenant "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "tenants.",
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "users": {
                            "description": "Resources applicable for user actions.",
                            "properties": {
                                "users": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "users "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "user "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "users.",
                                    "type": "string",
                                }
                            },
                            "type": "object",
                        },
                    },
                    "required": ["action"],
                    "type": "object",
                },
                "type": "array",
            },
        },
        "required": ["name", "permissions"],
        "type": "object",
    },
    "ADDPERMISSIONSTOROLE_REQUEST_BODY_SCHEMA": {
        "properties": {
            "permissions": {
                "description": "Permissions to be added to the role.",
                "items": {
                    "description": "Permissions attached to a role.",
                    "properties": {
                        "action": {
                            "description": "Allowed actions in weaviate.",
                            "enum": [
                                "manage_backups",
                                "read_cluster",
                                "create_data",
                                "read_data",
                                "update_data",
                                "delete_data",
                                "read_nodes",
                                "create_roles",
                                "read_roles",
                                "update_roles",
                                "delete_roles",
                                "create_collections",
                                "read_collections",
                                "update_collections",
                                "delete_collections",
                                "assign_and_revoke_users",
                                "create_users",
                                "read_users",
                                "update_users",
                                "delete_users",
                                "create_tenants",
                                "read_tenants",
                                "update_tenants",
                                "delete_tenants",
                                "create_replicate",
                                "read_replicate",
                                "update_replicate",
                                "delete_replicate",
                                "create_aliases",
                                "read_aliases",
                                "update_aliases",
                                "delete_aliases",
                                "assign_and_revoke_groups",
                                "read_groups",
                            ],
                            "type": "string",
                        },
                        "aliases": {
                            "description": "Resource "
                            "definition "
                            "for "
                            "alias-related "
                            "actions "
                            "and "
                            "permissions. "
                            "Used "
                            "to "
                            "specify "
                            "which "
                            "aliases "
                            "and "
                            "collections "
                            "can "
                            "be "
                            "accessed "
                            "or "
                            "modified.",
                            "properties": {
                                "alias": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "aliases "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "alias "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "aliases.",
                                    "type": "string",
                                },
                                "collection": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "collections "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "collection "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "collections.",
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "backups": {
                            "description": "Resources applicable for backup actions.",
                            "properties": {
                                "collection": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "collections "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "collection "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "collections.",
                                    "type": "string",
                                }
                            },
                            "type": "object",
                        },
                        "collections": {
                            "description": "Resources "
                            "applicable "
                            "for "
                            "collection "
                            "and/or "
                            "tenant "
                            "actions.",
                            "properties": {
                                "collection": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "collections "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "collection "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "collections.",
                                    "type": "string",
                                }
                            },
                            "type": "object",
                        },
                        "data": {
                            "description": "Resources applicable for data actions.",
                            "properties": {
                                "collection": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "collections "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "collection "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "collections.",
                                    "type": "string",
                                },
                                "object": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "objects "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "object "
                                    "ID "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "objects.",
                                    "type": "string",
                                },
                                "tenant": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "tenants "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "tenant "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "tenants.",
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "groups": {
                            "description": "Resources applicable for group actions.",
                            "properties": {
                                "group": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "groups "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "group "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "groups.",
                                    "type": "string",
                                },
                                "groupType": {
                                    "description": "If the group contains OIDC or database users.",
                                    "enum": ["oidc"],
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "nodes": {
                            "description": "Resources applicable for cluster actions.",
                            "properties": {
                                "collection": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "collections "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "collection "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "collections.",
                                    "type": "string",
                                },
                                "verbosity": {
                                    "default": "minimal",
                                    "description": "Whether "
                                    "to "
                                    "allow "
                                    "(verbose) "
                                    "returning "
                                    "shards "
                                    "and "
                                    "stats "
                                    "data "
                                    "in "
                                    "the "
                                    "response.",
                                    "enum": ["verbose", "minimal"],
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "replicate": {
                            "description": "resources applicable for replicate actions",
                            "properties": {
                                "collection": {
                                    "default": "*",
                                    "description": "string "
                                    "or "
                                    "regex. "
                                    "if "
                                    "a "
                                    "specific "
                                    "collection "
                                    "name, "
                                    "if "
                                    "left "
                                    "empty "
                                    "it "
                                    "will "
                                    "be "
                                    "ALL "
                                    "or "
                                    "*",
                                    "type": "string",
                                },
                                "shard": {
                                    "default": "*",
                                    "description": "string "
                                    "or "
                                    "regex. "
                                    "if "
                                    "a "
                                    "specific "
                                    "shard "
                                    "name, "
                                    "if "
                                    "left "
                                    "empty "
                                    "it "
                                    "will "
                                    "be "
                                    "ALL "
                                    "or "
                                    "*",
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "roles": {
                            "description": "Resources applicable for role actions.",
                            "properties": {
                                "role": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "roles "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "role "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "roles.",
                                    "type": "string",
                                },
                                "scope": {
                                    "default": "match",
                                    "description": "Set the scope for the manage role permission.",
                                    "enum": ["all", "match"],
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "tenants": {
                            "description": "Resources applicable for tenant actions.",
                            "properties": {
                                "collection": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "collections "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "collection "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "collections.",
                                    "type": "string",
                                },
                                "tenant": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "tenants "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "tenant "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "tenants.",
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "users": {
                            "description": "Resources applicable for user actions.",
                            "properties": {
                                "users": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "users "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "user "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "users.",
                                    "type": "string",
                                }
                            },
                            "type": "object",
                        },
                    },
                    "required": ["action"],
                    "type": "object",
                },
                "type": "array",
            }
        },
        "required": ["permissions"],
        "type": "object",
    },
    "REVOKEROLEPERMISSIONS_REQUEST_BODY_SCHEMA": {
        "properties": {
            "permissions": {
                "description": "Permissions to remove from the role.",
                "items": {
                    "description": "Permissions attached to a role.",
                    "properties": {
                        "action": {
                            "description": "Allowed actions in weaviate.",
                            "enum": [
                                "manage_backups",
                                "read_cluster",
                                "create_data",
                                "read_data",
                                "update_data",
                                "delete_data",
                                "read_nodes",
                                "create_roles",
                                "read_roles",
                                "update_roles",
                                "delete_roles",
                                "create_collections",
                                "read_collections",
                                "update_collections",
                                "delete_collections",
                                "assign_and_revoke_users",
                                "create_users",
                                "read_users",
                                "update_users",
                                "delete_users",
                                "create_tenants",
                                "read_tenants",
                                "update_tenants",
                                "delete_tenants",
                                "create_replicate",
                                "read_replicate",
                                "update_replicate",
                                "delete_replicate",
                                "create_aliases",
                                "read_aliases",
                                "update_aliases",
                                "delete_aliases",
                                "assign_and_revoke_groups",
                                "read_groups",
                            ],
                            "type": "string",
                        },
                        "aliases": {
                            "description": "Resource "
                            "definition "
                            "for "
                            "alias-related "
                            "actions "
                            "and "
                            "permissions. "
                            "Used "
                            "to "
                            "specify "
                            "which "
                            "aliases "
                            "and "
                            "collections "
                            "can "
                            "be "
                            "accessed "
                            "or "
                            "modified.",
                            "properties": {
                                "alias": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "aliases "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "alias "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "aliases.",
                                    "type": "string",
                                },
                                "collection": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "collections "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "collection "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "collections.",
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "backups": {
                            "description": "Resources applicable for backup actions.",
                            "properties": {
                                "collection": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "collections "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "collection "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "collections.",
                                    "type": "string",
                                }
                            },
                            "type": "object",
                        },
                        "collections": {
                            "description": "Resources "
                            "applicable "
                            "for "
                            "collection "
                            "and/or "
                            "tenant "
                            "actions.",
                            "properties": {
                                "collection": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "collections "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "collection "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "collections.",
                                    "type": "string",
                                }
                            },
                            "type": "object",
                        },
                        "data": {
                            "description": "Resources applicable for data actions.",
                            "properties": {
                                "collection": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "collections "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "collection "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "collections.",
                                    "type": "string",
                                },
                                "object": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "objects "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "object "
                                    "ID "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "objects.",
                                    "type": "string",
                                },
                                "tenant": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "tenants "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "tenant "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "tenants.",
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "groups": {
                            "description": "Resources applicable for group actions.",
                            "properties": {
                                "group": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "groups "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "group "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "groups.",
                                    "type": "string",
                                },
                                "groupType": {
                                    "description": "If the group contains OIDC or database users.",
                                    "enum": ["oidc"],
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "nodes": {
                            "description": "Resources applicable for cluster actions.",
                            "properties": {
                                "collection": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "collections "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "collection "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "collections.",
                                    "type": "string",
                                },
                                "verbosity": {
                                    "default": "minimal",
                                    "description": "Whether "
                                    "to "
                                    "allow "
                                    "(verbose) "
                                    "returning "
                                    "shards "
                                    "and "
                                    "stats "
                                    "data "
                                    "in "
                                    "the "
                                    "response.",
                                    "enum": ["verbose", "minimal"],
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "replicate": {
                            "description": "resources applicable for replicate actions",
                            "properties": {
                                "collection": {
                                    "default": "*",
                                    "description": "string "
                                    "or "
                                    "regex. "
                                    "if "
                                    "a "
                                    "specific "
                                    "collection "
                                    "name, "
                                    "if "
                                    "left "
                                    "empty "
                                    "it "
                                    "will "
                                    "be "
                                    "ALL "
                                    "or "
                                    "*",
                                    "type": "string",
                                },
                                "shard": {
                                    "default": "*",
                                    "description": "string "
                                    "or "
                                    "regex. "
                                    "if "
                                    "a "
                                    "specific "
                                    "shard "
                                    "name, "
                                    "if "
                                    "left "
                                    "empty "
                                    "it "
                                    "will "
                                    "be "
                                    "ALL "
                                    "or "
                                    "*",
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "roles": {
                            "description": "Resources applicable for role actions.",
                            "properties": {
                                "role": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "roles "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "role "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "roles.",
                                    "type": "string",
                                },
                                "scope": {
                                    "default": "match",
                                    "description": "Set the scope for the manage role permission.",
                                    "enum": ["all", "match"],
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "tenants": {
                            "description": "Resources applicable for tenant actions.",
                            "properties": {
                                "collection": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "collections "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "collection "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "collections.",
                                    "type": "string",
                                },
                                "tenant": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "tenants "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "tenant "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "tenants.",
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "users": {
                            "description": "Resources applicable for user actions.",
                            "properties": {
                                "users": {
                                    "default": "*",
                                    "description": "A "
                                    "string "
                                    "that "
                                    "specifies "
                                    "which "
                                    "users "
                                    "this "
                                    "permission "
                                    "applies "
                                    "to. "
                                    "Can "
                                    "be "
                                    "an "
                                    "exact "
                                    "user "
                                    "name "
                                    "or "
                                    "a "
                                    "regex "
                                    "pattern. "
                                    "The "
                                    "default "
                                    "value "
                                    "`*` "
                                    "applies "
                                    "the "
                                    "permission "
                                    "to "
                                    "all "
                                    "users.",
                                    "type": "string",
                                }
                            },
                            "type": "object",
                        },
                    },
                    "required": ["action"],
                    "type": "object",
                },
                "type": "array",
            }
        },
        "required": ["permissions"],
        "type": "object",
    },
    "CHECKROLEPERMISSION_REQUEST_BODY_SCHEMA": {
        "description": "Permissions attached to a role.",
        "properties": {
            "action": {
                "description": "Allowed actions in weaviate.",
                "enum": [
                    "manage_backups",
                    "read_cluster",
                    "create_data",
                    "read_data",
                    "update_data",
                    "delete_data",
                    "read_nodes",
                    "create_roles",
                    "read_roles",
                    "update_roles",
                    "delete_roles",
                    "create_collections",
                    "read_collections",
                    "update_collections",
                    "delete_collections",
                    "assign_and_revoke_users",
                    "create_users",
                    "read_users",
                    "update_users",
                    "delete_users",
                    "create_tenants",
                    "read_tenants",
                    "update_tenants",
                    "delete_tenants",
                    "create_replicate",
                    "read_replicate",
                    "update_replicate",
                    "delete_replicate",
                    "create_aliases",
                    "read_aliases",
                    "update_aliases",
                    "delete_aliases",
                    "assign_and_revoke_groups",
                    "read_groups",
                ],
                "type": "string",
            },
            "aliases": {
                "description": "Resource definition for alias-related "
                "actions and permissions. Used to specify "
                "which aliases and collections can be "
                "accessed or modified.",
                "properties": {
                    "alias": {
                        "default": "*",
                        "description": "A string that "
                        "specifies which "
                        "aliases this "
                        "permission "
                        "applies to. Can "
                        "be an exact alias "
                        "name or a regex "
                        "pattern. The "
                        "default value `*` "
                        "applies the "
                        "permission to all "
                        "aliases.",
                        "type": "string",
                    },
                    "collection": {
                        "default": "*",
                        "description": "A string "
                        "that "
                        "specifies "
                        "which "
                        "collections "
                        "this "
                        "permission "
                        "applies to. "
                        "Can be an "
                        "exact "
                        "collection "
                        "name or a "
                        "regex "
                        "pattern. The "
                        "default "
                        "value `*` "
                        "applies the "
                        "permission "
                        "to all "
                        "collections.",
                        "type": "string",
                    },
                },
                "type": "object",
            },
            "backups": {
                "description": "Resources applicable for backup actions.",
                "properties": {
                    "collection": {
                        "default": "*",
                        "description": "A string "
                        "that "
                        "specifies "
                        "which "
                        "collections "
                        "this "
                        "permission "
                        "applies to. "
                        "Can be an "
                        "exact "
                        "collection "
                        "name or a "
                        "regex "
                        "pattern. The "
                        "default "
                        "value `*` "
                        "applies the "
                        "permission "
                        "to all "
                        "collections.",
                        "type": "string",
                    }
                },
                "type": "object",
            },
            "collections": {
                "description": "Resources applicable for collection and/or tenant actions.",
                "properties": {
                    "collection": {
                        "default": "*",
                        "description": "A string "
                        "that "
                        "specifies "
                        "which "
                        "collections "
                        "this "
                        "permission "
                        "applies "
                        "to. Can "
                        "be an "
                        "exact "
                        "collection "
                        "name or "
                        "a regex "
                        "pattern. "
                        "The "
                        "default "
                        "value "
                        "`*` "
                        "applies "
                        "the "
                        "permission "
                        "to all "
                        "collections.",
                        "type": "string",
                    }
                },
                "type": "object",
            },
            "data": {
                "description": "Resources applicable for data actions.",
                "properties": {
                    "collection": {
                        "default": "*",
                        "description": "A string that "
                        "specifies which "
                        "collections "
                        "this permission "
                        "applies to. Can "
                        "be an exact "
                        "collection name "
                        "or a regex "
                        "pattern. The "
                        "default value "
                        "`*` applies the "
                        "permission to "
                        "all "
                        "collections.",
                        "type": "string",
                    },
                    "object": {
                        "default": "*",
                        "description": "A string that "
                        "specifies which "
                        "objects this "
                        "permission applies "
                        "to. Can be an exact "
                        "object ID or a "
                        "regex pattern. The "
                        "default value `*` "
                        "applies the "
                        "permission to all "
                        "objects.",
                        "type": "string",
                    },
                    "tenant": {
                        "default": "*",
                        "description": "A string that "
                        "specifies which "
                        "tenants this "
                        "permission applies "
                        "to. Can be an exact "
                        "tenant name or a "
                        "regex pattern. The "
                        "default value `*` "
                        "applies the "
                        "permission to all "
                        "tenants.",
                        "type": "string",
                    },
                },
                "type": "object",
            },
            "groups": {
                "description": "Resources applicable for group actions.",
                "properties": {
                    "group": {
                        "default": "*",
                        "description": "A string that "
                        "specifies which "
                        "groups this "
                        "permission applies "
                        "to. Can be an "
                        "exact group name "
                        "or a regex "
                        "pattern. The "
                        "default value `*` "
                        "applies the "
                        "permission to all "
                        "groups.",
                        "type": "string",
                    },
                    "groupType": {
                        "description": "If the group contains OIDC or database users.",
                        "enum": ["oidc"],
                        "type": "string",
                    },
                },
                "type": "object",
            },
            "nodes": {
                "description": "Resources applicable for cluster actions.",
                "properties": {
                    "collection": {
                        "default": "*",
                        "description": "A string that "
                        "specifies "
                        "which "
                        "collections "
                        "this "
                        "permission "
                        "applies to. "
                        "Can be an "
                        "exact "
                        "collection "
                        "name or a "
                        "regex pattern. "
                        "The default "
                        "value `*` "
                        "applies the "
                        "permission to "
                        "all "
                        "collections.",
                        "type": "string",
                    },
                    "verbosity": {
                        "default": "minimal",
                        "description": "Whether to "
                        "allow (verbose) "
                        "returning "
                        "shards and "
                        "stats data in "
                        "the response.",
                        "enum": ["verbose", "minimal"],
                        "type": "string",
                    },
                },
                "type": "object",
            },
            "replicate": {
                "description": "resources applicable for replicate actions",
                "properties": {
                    "collection": {
                        "default": "*",
                        "description": "string or "
                        "regex. if "
                        "a specific "
                        "collection "
                        "name, if "
                        "left empty "
                        "it will be "
                        "ALL or *",
                        "type": "string",
                    },
                    "shard": {
                        "default": "*",
                        "description": "string or "
                        "regex. if a "
                        "specific shard "
                        "name, if left "
                        "empty it will "
                        "be ALL or *",
                        "type": "string",
                    },
                },
                "type": "object",
            },
            "roles": {
                "description": "Resources applicable for role actions.",
                "properties": {
                    "role": {
                        "default": "*",
                        "description": "A string that "
                        "specifies which "
                        "roles this "
                        "permission applies "
                        "to. Can be an exact "
                        "role name or a regex "
                        "pattern. The default "
                        "value `*` applies "
                        "the permission to "
                        "all roles.",
                        "type": "string",
                    },
                    "scope": {
                        "default": "match",
                        "description": "Set the scope for the manage role permission.",
                        "enum": ["all", "match"],
                        "type": "string",
                    },
                },
                "type": "object",
            },
            "tenants": {
                "description": "Resources applicable for tenant actions.",
                "properties": {
                    "collection": {
                        "default": "*",
                        "description": "A string "
                        "that "
                        "specifies "
                        "which "
                        "collections "
                        "this "
                        "permission "
                        "applies to. "
                        "Can be an "
                        "exact "
                        "collection "
                        "name or a "
                        "regex "
                        "pattern. The "
                        "default "
                        "value `*` "
                        "applies the "
                        "permission "
                        "to all "
                        "collections.",
                        "type": "string",
                    },
                    "tenant": {
                        "default": "*",
                        "description": "A string that "
                        "specifies which "
                        "tenants this "
                        "permission "
                        "applies to. Can "
                        "be an exact "
                        "tenant name or a "
                        "regex pattern. "
                        "The default "
                        "value `*` "
                        "applies the "
                        "permission to "
                        "all tenants.",
                        "type": "string",
                    },
                },
                "type": "object",
            },
            "users": {
                "description": "Resources applicable for user actions.",
                "properties": {
                    "users": {
                        "default": "*",
                        "description": "A string that "
                        "specifies which "
                        "users this "
                        "permission applies "
                        "to. Can be an exact "
                        "user name or a "
                        "regex pattern. The "
                        "default value `*` "
                        "applies the "
                        "permission to all "
                        "users.",
                        "type": "string",
                    }
                },
                "type": "object",
            },
        },
        "required": ["action"],
        "type": "object",
    },
    "CREATEOBJECTINWEAVIATE_REQUEST_BODY_SCHEMA": {
        "properties": {
            "additional": {
                "additionalProperties": {"properties": {}, "type": "object"},
                "description": "(Response only) Additional meta information about a single object.",
                "type": "object",
            },
            "class": {
                "description": "Name of the collection (class) the object belongs to.",
                "type": "string",
            },
            "creationTimeUnix": {
                "description": "(Response only) Timestamp of "
                "creation of this object in "
                "milliseconds since epoch UTC.",
                "format": "int64",
                "type": "integer",
            },
            "id": {"description": "The UUID of the object.", "format": "uuid", "type": "string"},
            "lastUpdateTimeUnix": {
                "description": "(Response only) Timestamp of "
                "the last object update in "
                "milliseconds since epoch UTC.",
                "format": "int64",
                "type": "integer",
            },
            "properties": {
                "description": "Names and values of an individual "
                "property. A returned response may also "
                "contain additional metadata, such as "
                "from classification or feature "
                "projection.",
                "type": "object",
            },
            "tenant": {
                "description": "The name of the tenant the object belongs to.",
                "type": "string",
            },
            "vector": {
                "description": "A vector representation of the object in "
                "the Contextionary. If provided at object "
                "creation, this wil take precedence over any "
                "vectorizer setting.",
                "items": {"format": "float", "type": "number"},
                "type": "array",
            },
            "vectorWeights": {
                "description": "Allow custom overrides of vector "
                "weights as math expressions. E.g. "
                "`pancake`: `7` will set the weight "
                "for the word pancake to 7 in the "
                "vectorization, whereas `w * 3` would "
                "triple the originally calculated "
                "word. This is an open object, with "
                "OpenAPI Specification 3.0 this will "
                "be more detailed. See Weaviate docs "
                "for more info. In the future this "
                "will become a key/value "
                "(string/string) object.",
                "type": "object",
            },
            "vectors": {
                "additionalProperties": {
                    "description": "A vector "
                    "representation of "
                    "the object. If "
                    "provided at "
                    "object creation, "
                    "this wil take "
                    "precedence over "
                    "any vectorizer "
                    "setting.",
                    "type": "object",
                },
                "description": "A map of named vectors for multi-vector representations.",
                "type": "object",
            },
        },
        "type": "object",
    },
    "UPDATEOBJECTPROPERTIES_REQUEST_BODY_SCHEMA": {
        "properties": {
            "additional": {
                "additionalProperties": {"properties": {}, "type": "object"},
                "description": "(Response only) Additional meta information about a single object.",
                "type": "object",
            },
            "class": {
                "description": "Name of the collection (class) the object belongs to.",
                "type": "string",
            },
            "creationTimeUnix": {
                "description": "(Response only) Timestamp of "
                "creation of this object in "
                "milliseconds since epoch UTC.",
                "format": "int64",
                "type": "integer",
            },
            "id": {"description": "The UUID of the object.", "format": "uuid", "type": "string"},
            "lastUpdateTimeUnix": {
                "description": "(Response only) Timestamp of "
                "the last object update in "
                "milliseconds since epoch UTC.",
                "format": "int64",
                "type": "integer",
            },
            "properties": {
                "description": "Names and values of an individual "
                "property. A returned response may also "
                "contain additional metadata, such as "
                "from classification or feature "
                "projection.",
                "type": "object",
            },
            "tenant": {
                "description": "The name of the tenant the object belongs to.",
                "type": "string",
            },
            "vector": {
                "description": "A vector representation of the object in "
                "the Contextionary. If provided at object "
                "creation, this wil take precedence over any "
                "vectorizer setting.",
                "items": {"format": "float", "type": "number"},
                "type": "array",
            },
            "vectorWeights": {
                "description": "Allow custom overrides of vector "
                "weights as math expressions. E.g. "
                "`pancake`: `7` will set the weight "
                "for the word pancake to 7 in the "
                "vectorization, whereas `w * 3` would "
                "triple the originally calculated "
                "word. This is an open object, with "
                "OpenAPI Specification 3.0 this will "
                "be more detailed. See Weaviate docs "
                "for more info. In the future this "
                "will become a key/value "
                "(string/string) object.",
                "type": "object",
            },
            "vectors": {
                "additionalProperties": {
                    "description": "A vector "
                    "representation of "
                    "the object. If "
                    "provided at "
                    "object creation, "
                    "this wil take "
                    "precedence over "
                    "any vectorizer "
                    "setting.",
                    "type": "object",
                },
                "description": "A map of named vectors for multi-vector representations.",
                "type": "object",
            },
        },
        "type": "object",
    },
    "UPDATEDATAOBJECT_REQUEST_BODY_SCHEMA": {
        "properties": {
            "additional": {
                "additionalProperties": {"properties": {}, "type": "object"},
                "description": "(Response only) Additional meta information about a single object.",
                "type": "object",
            },
            "class": {
                "description": "Name of the collection (class) the object belongs to.",
                "type": "string",
            },
            "creationTimeUnix": {
                "description": "(Response only) Timestamp of "
                "creation of this object in "
                "milliseconds since epoch UTC.",
                "format": "int64",
                "type": "integer",
            },
            "id": {"description": "The UUID of the object.", "format": "uuid", "type": "string"},
            "lastUpdateTimeUnix": {
                "description": "(Response only) Timestamp of "
                "the last object update in "
                "milliseconds since epoch UTC.",
                "format": "int64",
                "type": "integer",
            },
            "properties": {
                "description": "Names and values of an individual "
                "property. A returned response may also "
                "contain additional metadata, such as "
                "from classification or feature "
                "projection.",
                "type": "object",
            },
            "tenant": {
                "description": "The name of the tenant the object belongs to.",
                "type": "string",
            },
            "vector": {
                "description": "A vector representation of the object in "
                "the Contextionary. If provided at object "
                "creation, this wil take precedence over any "
                "vectorizer setting.",
                "items": {"format": "float", "type": "number"},
                "type": "array",
            },
            "vectorWeights": {
                "description": "Allow custom overrides of vector "
                "weights as math expressions. E.g. "
                "`pancake`: `7` will set the weight "
                "for the word pancake to 7 in the "
                "vectorization, whereas `w * 3` would "
                "triple the originally calculated "
                "word. This is an open object, with "
                "OpenAPI Specification 3.0 this will "
                "be more detailed. See Weaviate docs "
                "for more info. In the future this "
                "will become a key/value "
                "(string/string) object.",
                "type": "object",
            },
            "vectors": {
                "additionalProperties": {
                    "description": "A vector "
                    "representation of "
                    "the object. If "
                    "provided at "
                    "object creation, "
                    "this wil take "
                    "precedence over "
                    "any vectorizer "
                    "setting.",
                    "type": "object",
                },
                "description": "A map of named vectors for multi-vector representations.",
                "type": "object",
            },
        },
        "type": "object",
    },
    "REPLACEOBJECTREFERENCES_REQUEST_BODY_SCHEMA": {
        "description": "Multiple instances of references to other objects.",
        "items": {
            "description": "Either set beacon (direct reference) or set collection "
            "(class) and schema (concept reference)",
            "properties": {
                "beacon": {
                    "description": "If using a direct reference, "
                    "specify the URI to point to the "
                    "cross-reference here. Should be "
                    "in the form of "
                    "weaviate://localhost/<uuid> for "
                    "the example of a local "
                    "cross-reference to an object",
                    "format": "uri",
                    "type": "string",
                },
                "class": {
                    "description": "If using a concept reference "
                    "(rather than a direct reference), "
                    "specify the desired collection "
                    "(class) name here.",
                    "format": "uri",
                    "type": "string",
                },
                "classification": {
                    "description": "This meta field contains "
                    "additional info about the "
                    "classified reference "
                    "property",
                    "properties": {
                        "closestLosingDistance": {
                            "description": "The "
                            "lowest "
                            "distance "
                            "of "
                            "a "
                            "neighbor "
                            "in "
                            "the "
                            "losing "
                            "group. "
                            "Optional. "
                            "If "
                            "k "
                            "equals "
                            "the "
                            "size "
                            "of "
                            "the "
                            "winning "
                            "group, "
                            "there "
                            "is "
                            "no "
                            "losing "
                            "group",
                            "format": "float32",
                            "nullable": True,
                            "type": "number",
                        },
                        "closestOverallDistance": {
                            "description": "The "
                            "lowest "
                            "distance "
                            "of "
                            "any "
                            "neighbor, "
                            "regardless "
                            "of "
                            "whether "
                            "they "
                            "were "
                            "in "
                            "the "
                            "winning "
                            "or "
                            "losing "
                            "group",
                            "format": "float32",
                            "type": "number",
                        },
                        "closestWinningDistance": {
                            "description": "Closest distance of a neighbor from the winning group",
                            "format": "float32",
                            "type": "number",
                        },
                        "losingCount": {
                            "description": "size "
                            "of "
                            "the "
                            "losing "
                            "group, "
                            "can "
                            "be "
                            "0 "
                            "if "
                            "the "
                            "winning "
                            "group "
                            "size "
                            "equals "
                            "k",
                            "format": "int64",
                            "type": "number",
                        },
                        "losingDistance": {
                            "description": "deprecated - do not use, to be removed in 0.23.0",
                            "format": "float32",
                            "nullable": True,
                            "type": "number",
                        },
                        "meanLosingDistance": {
                            "description": "Mean "
                            "distance "
                            "of "
                            "all "
                            "neighbors "
                            "from "
                            "the "
                            "losing "
                            "group. "
                            "Optional. "
                            "If "
                            "k "
                            "equals "
                            "the "
                            "size "
                            "of "
                            "the "
                            "winning "
                            "group, "
                            "there "
                            "is "
                            "no "
                            "losing "
                            "group.",
                            "format": "float32",
                            "nullable": True,
                            "type": "number",
                        },
                        "meanWinningDistance": {
                            "description": "Mean distance of all neighbors from the winning group",
                            "format": "float32",
                            "type": "number",
                        },
                        "overallCount": {
                            "description": "overall "
                            "neighbors "
                            "checked "
                            "as "
                            "part "
                            "of "
                            "the "
                            "classification. "
                            "In "
                            "most "
                            "cases "
                            "this "
                            "will "
                            "equal "
                            "k, "
                            "but "
                            "could "
                            "be "
                            "lower "
                            "than "
                            "k "
                            "- "
                            "for "
                            "example "
                            "if "
                            "not "
                            "enough "
                            "data "
                            "was "
                            "present",
                            "format": "int64",
                            "type": "number",
                        },
                        "winningCount": {
                            "description": "size of the winning group, a number between 1..k",
                            "format": "int64",
                            "type": "number",
                        },
                        "winningDistance": {
                            "description": "deprecated - do not use, to be removed in 0.23.0",
                            "format": "float32",
                            "type": "number",
                        },
                    },
                    "type": "object",
                },
                "href": {
                    "description": "If using a direct reference, this "
                    "read-only fields provides a link to "
                    "the referenced resource. If "
                    "'origin' is globally configured, an "
                    "absolute URI is shown - a relative "
                    "URI otherwise.",
                    "format": "uri",
                    "type": "string",
                },
                "schema": {
                    "description": "Names and values of an individual "
                    "property. A returned response may "
                    "also contain additional metadata, "
                    "such as from classification or "
                    "feature projection.",
                    "type": "object",
                },
            },
            "type": "object",
        },
        "type": "array",
    },
    "ADDREFERENCETOOBJECT_REQUEST_BODY_SCHEMA": {
        "description": "Either set beacon (direct reference) or set collection (class) and "
        "schema (concept reference)",
        "properties": {
            "beacon": {
                "description": "If using a direct reference, specify the "
                "URI to point to the cross-reference here. "
                "Should be in the form of "
                "weaviate://localhost/<uuid> for the example "
                "of a local cross-reference to an object",
                "format": "uri",
                "type": "string",
            },
            "class": {
                "description": "If using a concept reference (rather than a "
                "direct reference), specify the desired "
                "collection (class) name here.",
                "format": "uri",
                "type": "string",
            },
            "classification": {
                "description": "This meta field contains additional "
                "info about the classified reference "
                "property",
                "properties": {
                    "closestLosingDistance": {
                        "description": "The "
                        "lowest "
                        "distance "
                        "of "
                        "a "
                        "neighbor "
                        "in "
                        "the "
                        "losing "
                        "group. "
                        "Optional. "
                        "If "
                        "k "
                        "equals "
                        "the "
                        "size "
                        "of "
                        "the "
                        "winning "
                        "group, "
                        "there "
                        "is "
                        "no "
                        "losing "
                        "group",
                        "format": "float32",
                        "nullable": True,
                        "type": "number",
                    },
                    "closestOverallDistance": {
                        "description": "The "
                        "lowest "
                        "distance "
                        "of "
                        "any "
                        "neighbor, "
                        "regardless "
                        "of "
                        "whether "
                        "they "
                        "were "
                        "in "
                        "the "
                        "winning "
                        "or "
                        "losing "
                        "group",
                        "format": "float32",
                        "type": "number",
                    },
                    "closestWinningDistance": {
                        "description": "Closest distance of a neighbor from the winning group",
                        "format": "float32",
                        "type": "number",
                    },
                    "losingCount": {
                        "description": "size "
                        "of "
                        "the "
                        "losing "
                        "group, "
                        "can "
                        "be 0 "
                        "if "
                        "the "
                        "winning "
                        "group "
                        "size "
                        "equals "
                        "k",
                        "format": "int64",
                        "type": "number",
                    },
                    "losingDistance": {
                        "description": "deprecated - do not use, to be removed in 0.23.0",
                        "format": "float32",
                        "nullable": True,
                        "type": "number",
                    },
                    "meanLosingDistance": {
                        "description": "Mean "
                        "distance "
                        "of "
                        "all "
                        "neighbors "
                        "from "
                        "the "
                        "losing "
                        "group. "
                        "Optional. "
                        "If "
                        "k "
                        "equals "
                        "the "
                        "size "
                        "of "
                        "the "
                        "winning "
                        "group, "
                        "there "
                        "is "
                        "no "
                        "losing "
                        "group.",
                        "format": "float32",
                        "nullable": True,
                        "type": "number",
                    },
                    "meanWinningDistance": {
                        "description": "Mean distance of all neighbors from the winning group",
                        "format": "float32",
                        "type": "number",
                    },
                    "overallCount": {
                        "description": "overall "
                        "neighbors "
                        "checked "
                        "as "
                        "part "
                        "of "
                        "the "
                        "classification. "
                        "In "
                        "most "
                        "cases "
                        "this "
                        "will "
                        "equal "
                        "k, "
                        "but "
                        "could "
                        "be "
                        "lower "
                        "than "
                        "k - "
                        "for "
                        "example "
                        "if "
                        "not "
                        "enough "
                        "data "
                        "was "
                        "present",
                        "format": "int64",
                        "type": "number",
                    },
                    "winningCount": {
                        "description": "size of the winning group, a number between 1..k",
                        "format": "int64",
                        "type": "number",
                    },
                    "winningDistance": {
                        "description": "deprecated - do not use, to be removed in 0.23.0",
                        "format": "float32",
                        "type": "number",
                    },
                },
                "type": "object",
            },
            "href": {
                "description": "If using a direct reference, this read-only "
                "fields provides a link to the referenced "
                "resource. If 'origin' is globally configured, "
                "an absolute URI is shown - a relative URI "
                "otherwise.",
                "format": "uri",
                "type": "string",
            },
            "schema": {
                "description": "Names and values of an individual property. "
                "A returned response may also contain "
                "additional metadata, such as from "
                "classification or feature projection.",
                "type": "object",
            },
        },
        "type": "object",
    },
    "DELETEREFERENCEFROMOBJECT_REQUEST_BODY_SCHEMA": {
        "description": "Either set beacon (direct reference) or set collection (class) and "
        "schema (concept reference)",
        "properties": {
            "beacon": {
                "description": "If using a direct reference, specify the "
                "URI to point to the cross-reference here. "
                "Should be in the form of "
                "weaviate://localhost/<uuid> for the example "
                "of a local cross-reference to an object",
                "format": "uri",
                "type": "string",
            },
            "class": {
                "description": "If using a concept reference (rather than a "
                "direct reference), specify the desired "
                "collection (class) name here.",
                "format": "uri",
                "type": "string",
            },
            "classification": {
                "description": "This meta field contains additional "
                "info about the classified reference "
                "property",
                "properties": {
                    "closestLosingDistance": {
                        "description": "The "
                        "lowest "
                        "distance "
                        "of "
                        "a "
                        "neighbor "
                        "in "
                        "the "
                        "losing "
                        "group. "
                        "Optional. "
                        "If "
                        "k "
                        "equals "
                        "the "
                        "size "
                        "of "
                        "the "
                        "winning "
                        "group, "
                        "there "
                        "is "
                        "no "
                        "losing "
                        "group",
                        "format": "float32",
                        "nullable": True,
                        "type": "number",
                    },
                    "closestOverallDistance": {
                        "description": "The "
                        "lowest "
                        "distance "
                        "of "
                        "any "
                        "neighbor, "
                        "regardless "
                        "of "
                        "whether "
                        "they "
                        "were "
                        "in "
                        "the "
                        "winning "
                        "or "
                        "losing "
                        "group",
                        "format": "float32",
                        "type": "number",
                    },
                    "closestWinningDistance": {
                        "description": "Closest distance of a neighbor from the winning group",
                        "format": "float32",
                        "type": "number",
                    },
                    "losingCount": {
                        "description": "size "
                        "of "
                        "the "
                        "losing "
                        "group, "
                        "can "
                        "be 0 "
                        "if "
                        "the "
                        "winning "
                        "group "
                        "size "
                        "equals "
                        "k",
                        "format": "int64",
                        "type": "number",
                    },
                    "losingDistance": {
                        "description": "deprecated - do not use, to be removed in 0.23.0",
                        "format": "float32",
                        "nullable": True,
                        "type": "number",
                    },
                    "meanLosingDistance": {
                        "description": "Mean "
                        "distance "
                        "of "
                        "all "
                        "neighbors "
                        "from "
                        "the "
                        "losing "
                        "group. "
                        "Optional. "
                        "If "
                        "k "
                        "equals "
                        "the "
                        "size "
                        "of "
                        "the "
                        "winning "
                        "group, "
                        "there "
                        "is "
                        "no "
                        "losing "
                        "group.",
                        "format": "float32",
                        "nullable": True,
                        "type": "number",
                    },
                    "meanWinningDistance": {
                        "description": "Mean distance of all neighbors from the winning group",
                        "format": "float32",
                        "type": "number",
                    },
                    "overallCount": {
                        "description": "overall "
                        "neighbors "
                        "checked "
                        "as "
                        "part "
                        "of "
                        "the "
                        "classification. "
                        "In "
                        "most "
                        "cases "
                        "this "
                        "will "
                        "equal "
                        "k, "
                        "but "
                        "could "
                        "be "
                        "lower "
                        "than "
                        "k - "
                        "for "
                        "example "
                        "if "
                        "not "
                        "enough "
                        "data "
                        "was "
                        "present",
                        "format": "int64",
                        "type": "number",
                    },
                    "winningCount": {
                        "description": "size of the winning group, a number between 1..k",
                        "format": "int64",
                        "type": "number",
                    },
                    "winningDistance": {
                        "description": "deprecated - do not use, to be removed in 0.23.0",
                        "format": "float32",
                        "type": "number",
                    },
                },
                "type": "object",
            },
            "href": {
                "description": "If using a direct reference, this read-only "
                "fields provides a link to the referenced "
                "resource. If 'origin' is globally configured, "
                "an absolute URI is shown - a relative URI "
                "otherwise.",
                "format": "uri",
                "type": "string",
            },
            "schema": {
                "description": "Names and values of an individual property. "
                "A returned response may also contain "
                "additional metadata, such as from "
                "classification or feature projection.",
                "type": "object",
            },
        },
        "type": "object",
    },
    "VALIDATEDATAOBJECTSTRUCTURE_REQUEST_BODY_SCHEMA": {
        "properties": {
            "additional": {
                "additionalProperties": {"properties": {}, "type": "object"},
                "description": "(Response only) Additional meta information about a single object.",
                "type": "object",
            },
            "class": {
                "description": "Name of the collection (class) the object belongs to.",
                "type": "string",
            },
            "creationTimeUnix": {
                "description": "(Response only) Timestamp of "
                "creation of this object in "
                "milliseconds since epoch UTC.",
                "format": "int64",
                "type": "integer",
            },
            "id": {"description": "The UUID of the object.", "format": "uuid", "type": "string"},
            "lastUpdateTimeUnix": {
                "description": "(Response only) Timestamp of "
                "the last object update in "
                "milliseconds since epoch UTC.",
                "format": "int64",
                "type": "integer",
            },
            "properties": {
                "description": "Names and values of an individual "
                "property. A returned response may also "
                "contain additional metadata, such as "
                "from classification or feature "
                "projection.",
                "type": "object",
            },
            "tenant": {
                "description": "The name of the tenant the object belongs to.",
                "type": "string",
            },
            "vector": {
                "description": "A vector representation of the object in "
                "the Contextionary. If provided at object "
                "creation, this wil take precedence over any "
                "vectorizer setting.",
                "items": {"format": "float", "type": "number"},
                "type": "array",
            },
            "vectorWeights": {
                "description": "Allow custom overrides of vector "
                "weights as math expressions. E.g. "
                "`pancake`: `7` will set the weight "
                "for the word pancake to 7 in the "
                "vectorization, whereas `w * 3` would "
                "triple the originally calculated "
                "word. This is an open object, with "
                "OpenAPI Specification 3.0 this will "
                "be more detailed. See Weaviate docs "
                "for more info. In the future this "
                "will become a key/value "
                "(string/string) object.",
                "type": "object",
            },
            "vectors": {
                "additionalProperties": {
                    "description": "A vector "
                    "representation of "
                    "the object. If "
                    "provided at "
                    "object creation, "
                    "this wil take "
                    "precedence over "
                    "any vectorizer "
                    "setting.",
                    "type": "object",
                },
                "description": "A map of named vectors for multi-vector representations.",
                "type": "object",
            },
        },
        "type": "object",
    },
    "BATCHREGISTEROBJECTS_REQUEST_BODY_SCHEMA": {
        "properties": {
            "fields": {
                "description": "Controls which fields are returned in the "
                "response for each object. Default is `ALL`.",
                "items": {
                    "default": "ALL",
                    "enum": ["ALL", "class", "schema", "id", "creationTimeUnix"],
                    "type": "string",
                },
                "type": "array",
            },
            "objects": {
                "description": "Array of objects to be created.",
                "items": {
                    "properties": {
                        "additional": {
                            "additionalProperties": {"properties": {}, "type": "object"},
                            "description": "(Response "
                            "only) "
                            "Additional "
                            "meta "
                            "information "
                            "about "
                            "a "
                            "single "
                            "object.",
                            "type": "object",
                        },
                        "class": {
                            "description": "Name of the collection (class) the object belongs to.",
                            "type": "string",
                        },
                        "creationTimeUnix": {
                            "description": "(Response "
                            "only) "
                            "Timestamp "
                            "of "
                            "creation "
                            "of "
                            "this "
                            "object "
                            "in "
                            "milliseconds "
                            "since "
                            "epoch "
                            "UTC.",
                            "format": "int64",
                            "type": "integer",
                        },
                        "id": {
                            "description": "The UUID of the object.",
                            "format": "uuid",
                            "type": "string",
                        },
                        "lastUpdateTimeUnix": {
                            "description": "(Response "
                            "only) "
                            "Timestamp "
                            "of "
                            "the "
                            "last "
                            "object "
                            "update "
                            "in "
                            "milliseconds "
                            "since "
                            "epoch "
                            "UTC.",
                            "format": "int64",
                            "type": "integer",
                        },
                        "properties": {
                            "description": "Names "
                            "and "
                            "values "
                            "of "
                            "an "
                            "individual "
                            "property. "
                            "A "
                            "returned "
                            "response "
                            "may "
                            "also "
                            "contain "
                            "additional "
                            "metadata, "
                            "such "
                            "as "
                            "from "
                            "classification "
                            "or "
                            "feature "
                            "projection.",
                            "type": "object",
                        },
                        "tenant": {
                            "description": "The name of the tenant the object belongs to.",
                            "type": "string",
                        },
                        "vector": {
                            "description": "A "
                            "vector "
                            "representation "
                            "of the "
                            "object "
                            "in the "
                            "Contextionary. "
                            "If "
                            "provided "
                            "at "
                            "object "
                            "creation, "
                            "this "
                            "wil "
                            "take "
                            "precedence "
                            "over "
                            "any "
                            "vectorizer "
                            "setting.",
                            "items": {"format": "float", "type": "number"},
                            "type": "array",
                        },
                        "vectorWeights": {
                            "description": "Allow "
                            "custom "
                            "overrides "
                            "of "
                            "vector "
                            "weights "
                            "as "
                            "math "
                            "expressions. "
                            "E.g. "
                            "`pancake`: "
                            "`7` "
                            "will "
                            "set "
                            "the "
                            "weight "
                            "for "
                            "the "
                            "word "
                            "pancake "
                            "to "
                            "7 "
                            "in "
                            "the "
                            "vectorization, "
                            "whereas "
                            "`w "
                            "* "
                            "3` "
                            "would "
                            "triple "
                            "the "
                            "originally "
                            "calculated "
                            "word. "
                            "This "
                            "is "
                            "an "
                            "open "
                            "object, "
                            "with "
                            "OpenAPI "
                            "Specification "
                            "3.0 "
                            "this "
                            "will "
                            "be "
                            "more "
                            "detailed. "
                            "See "
                            "Weaviate "
                            "docs "
                            "for "
                            "more "
                            "info. "
                            "In "
                            "the "
                            "future "
                            "this "
                            "will "
                            "become "
                            "a "
                            "key/value "
                            "(string/string) "
                            "object.",
                            "type": "object",
                        },
                        "vectors": {
                            "additionalProperties": {
                                "description": "A "
                                "vector "
                                "representation "
                                "of "
                                "the "
                                "object. "
                                "If "
                                "provided "
                                "at "
                                "object "
                                "creation, "
                                "this "
                                "wil "
                                "take "
                                "precedence "
                                "over "
                                "any "
                                "vectorizer "
                                "setting.",
                                "type": "object",
                            },
                            "description": "A map "
                            "of "
                            "named "
                            "vectors "
                            "for "
                            "multi-vector "
                            "representations.",
                            "type": "object",
                        },
                    },
                    "type": "object",
                },
                "type": "array",
            },
        },
        "type": "object",
    },
    "DELETEMULTIPLEOBJECTS_REQUEST_BODY_SCHEMA": {
        "properties": {
            "deletionTimeUnixMilli": {
                "description": "Timestamp of deletion in milliseconds since epoch UTC.",
                "format": "int64",
                "nullable": True,
                "type": "integer",
            },
            "dryRun": {
                "default": False,
                "description": "If true, the call will show which objects "
                "would be matched using the specified filter "
                "without deleting any objects. "
                "<br/><br/>Depending on the configured "
                "verbosity, you will either receive a count "
                "of affected objects, or a list of IDs.",
                "type": "boolean",
            },
            "match": {
                "description": "Outlines how to find the objects to be deleted.",
                "properties": {
                    "class": {
                        "description": "The name of the "
                        "collection (class) "
                        "from which to "
                        "delete objects.",
                        "example": "City",
                        "type": "string",
                    },
                    "where": {
                        "description": "Filter search results using a where filter.",
                        "properties": {
                            "operands": {
                                "description": "Combine "
                                "multiple "
                                "where "
                                "filters, "
                                "requires "
                                "'And' "
                                "or "
                                "'Or' "
                                "operator.",
                                "items": {
                                    "$ref": "#/components/schemas/WhereFilter",
                                    "has_circular_reference": True,
                                },
                                "type": "array",
                            },
                            "operator": {
                                "description": "Operator to use.",
                                "enum": [
                                    "And",
                                    "Or",
                                    "Equal",
                                    "Like",
                                    "NotEqual",
                                    "GreaterThan",
                                    "GreaterThanEqual",
                                    "LessThan",
                                    "LessThanEqual",
                                    "WithinGeoRange",
                                    "IsNull",
                                    "ContainsAny",
                                    "ContainsAll",
                                    "ContainsNone",
                                    "Not",
                                ],
                                "example": "GreaterThanEqual",
                                "type": "string",
                            },
                            "path": {
                                "description": "Path to the property currently being filtered.",
                                "example": ["inCity", "city", "name"],
                                "items": {"type": "string"},
                                "type": "array",
                            },
                            "valueBoolean": {
                                "description": "value as boolean",
                                "example": False,
                                "nullable": True,
                                "type": "boolean",
                            },
                            "valueBooleanArray": {
                                "description": "value as boolean",
                                "example": [True, False],
                                "items": {"type": "boolean"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueDate": {
                                "description": "value as date (as string)",
                                "example": "TODO",
                                "nullable": True,
                                "type": "string",
                            },
                            "valueDateArray": {
                                "description": "value as date (as string)",
                                "example": "TODO",
                                "items": {"type": "string"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueGeoRange": {
                                "description": "Filter within a distance of a georange.",
                                "properties": {
                                    "distance": {
                                        "properties": {
                                            "max": {"format": "float64", "type": "number"}
                                        },
                                        "type": "object",
                                    },
                                    "geoCoordinates": {
                                        "properties": {
                                            "latitude": {
                                                "description": "The "
                                                "latitude "
                                                "of "
                                                "the "
                                                "point "
                                                "on "
                                                "earth "
                                                "in "
                                                "decimal "
                                                "form.",
                                                "format": "float",
                                                "nullable": True,
                                                "type": "number",
                                            },
                                            "longitude": {
                                                "description": "The "
                                                "longitude "
                                                "of "
                                                "the "
                                                "point "
                                                "on "
                                                "earth "
                                                "in "
                                                "decimal "
                                                "form.",
                                                "format": "float",
                                                "nullable": True,
                                                "type": "number",
                                            },
                                        },
                                        "type": "object",
                                    },
                                },
                                "type": "object",
                            },
                            "valueInt": {
                                "description": "value as integer",
                                "example": 2000,
                                "format": "int64",
                                "nullable": True,
                                "type": "integer",
                            },
                            "valueIntArray": {
                                "description": "value as integer",
                                "example": "[100, 200]",
                                "items": {"format": "int64", "type": "integer"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueNumber": {
                                "description": "value as number/float",
                                "example": 3.14,
                                "format": "float64",
                                "nullable": True,
                                "type": "number",
                            },
                            "valueNumberArray": {
                                "description": "value as number/float",
                                "example": [3.14],
                                "items": {"format": "float64", "type": "number"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueString": {
                                "description": "value "
                                "as "
                                "text "
                                "(deprecated "
                                "as "
                                "of "
                                "v1.19; "
                                "alias "
                                "for "
                                "valueText)",
                                "example": "my search term",
                                "nullable": True,
                                "type": "string",
                            },
                            "valueStringArray": {
                                "description": "value "
                                "as "
                                "text "
                                "(deprecated "
                                "as "
                                "of "
                                "v1.19; "
                                "alias "
                                "for "
                                "valueText)",
                                "example": ["my search term"],
                                "items": {"type": "string"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueText": {
                                "description": "value as text",
                                "example": "my search term",
                                "nullable": True,
                                "type": "string",
                            },
                            "valueTextArray": {
                                "description": "value as text",
                                "example": ["my search term"],
                                "items": {"type": "string"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                        },
                        "type": "object",
                    },
                },
                "type": "object",
            },
            "output": {
                "default": "minimal",
                "description": "Controls the verbosity of the output, "
                "possible values are: `minimal`, `verbose`. "
                "Defaults to `minimal`.",
                "type": "string",
            },
        },
        "type": "object",
    },
    "BATCHCREATEREFERENCES_REQUEST_BODY_SCHEMA": {
        "items": {
            "properties": {
                "from": {
                    "description": "Long-form beacon-style URI to "
                    "identify the source of the "
                    "cross-reference, including the "
                    "property name. Should be in the "
                    "form of "
                    "`weaviate://localhost/objects/<uuid>/<className>/<propertyName>`, "
                    "where `<className>` and "
                    "`<propertyName>` must represent the "
                    "cross-reference property of the "
                    "source class to be used.",
                    "example": "weaviate://localhost/Zoo/a5d09582-4239-4702-81c9-92a6e0122bb4/hasAnimals",
                    "format": "uri",
                    "type": "string",
                },
                "tenant": {"description": "Name of the reference tenant.", "type": "string"},
                "to": {
                    "description": "Short-form URI to point to the "
                    "cross-reference. Should be in the "
                    "form of `weaviate://localhost/<uuid>` "
                    "for the example of a local "
                    "cross-reference to an object.",
                    "example": "weaviate://localhost/97525810-a9a5-4eb0-858a-71449aeb007f",
                    "format": "uri",
                    "type": "string",
                },
            },
            "type": "object",
        },
        "type": "array",
    },
    "EXECUTEGRAPHQLBATCHQUERIES_REQUEST_BODY_SCHEMA": {
        "description": "A list of GraphQL queries.",
        "items": {
            "description": "GraphQL query based on: http://facebook.github.io/graphql/.",
            "properties": {
                "operationName": {
                    "description": "The name of the operation if multiple exist in the query.",
                    "type": "string",
                },
                "query": {"description": "Query based on GraphQL syntax.", "type": "string"},
                "variables": {
                    "description": "Additional variables for the query.",
                    "properties": {},
                    "type": "object",
                },
            },
            "type": "object",
        },
        "type": "array",
    },
    "CREATESCHEMAOBJECT_REQUEST_BODY_SCHEMA": {
        "properties": {
            "class": {
                "description": "Name of the collection (formerly 'class') "
                "(required). Multiple words should be "
                "concatenated in CamelCase, e.g. "
                "`ArticleAuthor`.",
                "type": "string",
            },
            "description": {
                "description": "Description of the collection for metadata purposes.",
                "type": "string",
            },
            "invertedIndexConfig": {
                "description": "Configure the inverted index "
                "built into Weaviate. See "
                "[Reference: Inverted "
                "index](https://docs.weaviate.io/weaviate/config-refs/indexing/inverted-index#inverted-index-parameters) "
                "for details.",
                "properties": {
                    "bm25": {
                        "description": "Tuning parameters for the BM25 algorithm.",
                        "properties": {
                            "b": {
                                "description": "Calibrates "
                                "term-weight "
                                "scaling "
                                "based "
                                "on "
                                "the "
                                "document "
                                "length "
                                "(default: "
                                "0.75).",
                                "format": "float",
                                "type": "number",
                            },
                            "k1": {
                                "description": "Calibrates "
                                "term-weight "
                                "scaling "
                                "based "
                                "on "
                                "the "
                                "term "
                                "frequency "
                                "within "
                                "a "
                                "document "
                                "(default: "
                                "1.2).",
                                "format": "float",
                                "type": "number",
                            },
                        },
                        "type": "object",
                    },
                    "cleanupIntervalSeconds": {
                        "description": "Asynchronous "
                        "index "
                        "clean "
                        "up "
                        "happens "
                        "every "
                        "n "
                        "seconds "
                        "(default: "
                        "60).",
                        "format": "int",
                        "type": "number",
                    },
                    "indexNullState": {
                        "description": "Index each object with the null state (default: `false`).",
                        "type": "boolean",
                    },
                    "indexPropertyLength": {
                        "description": "Index length of properties (default: `false`).",
                        "type": "boolean",
                    },
                    "indexTimestamps": {
                        "description": "Index "
                        "each "
                        "object "
                        "by "
                        "its "
                        "internal "
                        "timestamps "
                        "(default: "
                        "`false`).",
                        "type": "boolean",
                    },
                    "stopwords": {
                        "description": "Fine-grained control over stopword list usage.",
                        "properties": {
                            "additions": {
                                "description": "Stopwords "
                                "to "
                                "be "
                                "considered "
                                "additionally "
                                "(default: "
                                "[]). "
                                "Can "
                                "be "
                                "any "
                                "array "
                                "of "
                                "custom "
                                "strings.",
                                "items": {"type": "string"},
                                "type": "array",
                            },
                            "preset": {
                                "description": "Pre-existing "
                                "list "
                                "of "
                                "common "
                                "words "
                                "by "
                                "language "
                                "(default: "
                                "`en`). "
                                "Options: "
                                "[`en`, "
                                "`none`].",
                                "type": "string",
                            },
                            "removals": {
                                "description": "Stopwords "
                                "to "
                                "be "
                                "removed "
                                "from "
                                "consideration "
                                "(default: "
                                "[]). "
                                "Can "
                                "be "
                                "any "
                                "array "
                                "of "
                                "custom "
                                "strings.",
                                "items": {"type": "string"},
                                "type": "array",
                            },
                        },
                        "type": "object",
                    },
                    "usingBlockMaxWAND": {
                        "description": "Using "
                        "BlockMax "
                        "WAND "
                        "for "
                        "query "
                        "execution "
                        "(default: "
                        "`false`, "
                        "will "
                        "be "
                        "`true` "
                        "for "
                        "new "
                        "collections "
                        "created "
                        "after "
                        "1.30).",
                        "type": "boolean",
                    },
                },
                "type": "object",
            },
            "moduleConfig": {
                "description": "Configuration specific to modules in a collection context.",
                "properties": {},
                "type": "object",
            },
            "multiTenancyConfig": {
                "description": "Configuration related to multi-tenancy within a collection (class)",
                "properties": {
                    "autoTenantActivation": {
                        "description": "Existing "
                        "tenants "
                        "should "
                        "(not) "
                        "be "
                        "turned "
                        "HOT "
                        "implicitly "
                        "when "
                        "they "
                        "are "
                        "accessed "
                        "and "
                        "in "
                        "another "
                        "activity "
                        "status "
                        "(default: "
                        "`false`).",
                        "type": "boolean",
                        "x-omitempty": False,
                    },
                    "autoTenantCreation": {
                        "description": "Nonexistent "
                        "tenants "
                        "should "
                        "(not) "
                        "be "
                        "created "
                        "implicitly "
                        "(default: "
                        "`false`).",
                        "type": "boolean",
                        "x-omitempty": False,
                    },
                    "enabled": {
                        "description": "Whether "
                        "or "
                        "not "
                        "multi-tenancy "
                        "is "
                        "enabled "
                        "for "
                        "this "
                        "collection "
                        "(class) "
                        "(default: "
                        "`false`).",
                        "type": "boolean",
                        "x-omitempty": False,
                    },
                },
                "type": "object",
            },
            "properties": {
                "description": "Define properties of the collection.",
                "items": {
                    "properties": {
                        "dataType": {
                            "description": "Data "
                            "type "
                            "of "
                            "the "
                            "property "
                            "(required). "
                            "If "
                            "it "
                            "starts "
                            "with "
                            "a "
                            "capital "
                            "(for "
                            "example "
                            "Person), "
                            "may "
                            "be "
                            "a "
                            "reference "
                            "to "
                            "another "
                            "type.",
                            "items": {"type": "string"},
                            "type": "array",
                        },
                        "description": {
                            "description": "Description of the property.",
                            "type": "string",
                        },
                        "indexFilterable": {
                            "description": "Whether "
                            "to "
                            "include "
                            "this "
                            "property "
                            "in "
                            "the "
                            "filterable, "
                            "Roaring "
                            "Bitmap "
                            "index. "
                            "If "
                            "`false`, "
                            "this "
                            "property "
                            "cannot "
                            "be "
                            "used "
                            "in "
                            "`where` "
                            "filters. "
                            "<br/><br/>Note: "
                            "Unrelated "
                            "to "
                            "vectorization "
                            "behavior.",
                            "nullable": True,
                            "type": "boolean",
                        },
                        "indexInverted": {
                            "description": "(Deprecated). "
                            "Whether "
                            "to "
                            "include "
                            "this "
                            "property "
                            "in "
                            "the "
                            "inverted "
                            "index. "
                            "If "
                            "`false`, "
                            "this "
                            "property "
                            "cannot "
                            "be "
                            "used "
                            "in "
                            "`where` "
                            "filters, "
                            "`bm25` "
                            "or "
                            "`hybrid` "
                            "search. "
                            "<br/><br/>Unrelated "
                            "to "
                            "vectorization "
                            "behavior "
                            "(deprecated "
                            "as "
                            "of "
                            "v1.19; "
                            "use "
                            "indexFilterable "
                            "or/and "
                            "indexSearchable "
                            "instead)",
                            "nullable": True,
                            "type": "boolean",
                        },
                        "indexRangeFilters": {
                            "description": "Whether "
                            "to "
                            "include "
                            "this "
                            "property "
                            "in "
                            "the "
                            "filterable, "
                            "range-based "
                            "Roaring "
                            "Bitmap "
                            "index. "
                            "Provides "
                            "better "
                            "performance "
                            "for "
                            "range "
                            "queries "
                            "compared "
                            "to "
                            "filterable "
                            "index "
                            "in "
                            "large "
                            "datasets. "
                            "Applicable "
                            "only "
                            "to "
                            "properties "
                            "of "
                            "data "
                            "type "
                            "int, "
                            "number, "
                            "date.",
                            "nullable": True,
                            "type": "boolean",
                        },
                        "indexSearchable": {
                            "description": "Optional. "
                            "Should "
                            "this "
                            "property "
                            "be "
                            "indexed "
                            "in "
                            "the "
                            "inverted "
                            "index. "
                            "Defaults "
                            "to "
                            "true. "
                            "Applicable "
                            "only "
                            "to "
                            "properties "
                            "of "
                            "data "
                            "type "
                            "text "
                            "and "
                            "text[]. "
                            "If "
                            "you "
                            "choose "
                            "false, "
                            "you "
                            "will "
                            "not "
                            "be "
                            "able "
                            "to "
                            "use "
                            "this "
                            "property "
                            "in "
                            "bm25 "
                            "or "
                            "hybrid "
                            "search. "
                            "This "
                            "property "
                            "has "
                            "no "
                            "affect "
                            "on "
                            "vectorization "
                            "decisions "
                            "done "
                            "by "
                            "modules",
                            "nullable": True,
                            "type": "boolean",
                        },
                        "moduleConfig": {
                            "description": "Configuration "
                            "specific "
                            "to "
                            "modules "
                            "in "
                            "a "
                            "collection "
                            "context.",
                            "properties": {},
                            "type": "object",
                        },
                        "name": {
                            "description": "The "
                            "name "
                            "of "
                            "the "
                            "property "
                            "(required). "
                            "Multiple "
                            "words "
                            "should "
                            "be "
                            "concatenated "
                            "in "
                            "camelCase, "
                            "e.g. "
                            "`nameOfAuthor`.",
                            "type": "string",
                        },
                        "nestedProperties": {
                            "description": "The "
                            "properties "
                            "of "
                            "the "
                            "nested "
                            "object(s). "
                            "Applies "
                            "to "
                            "object "
                            "and "
                            "object[] "
                            "data "
                            "types.",
                            "items": {
                                "properties": {
                                    "dataType": {"items": {"type": "string"}, "type": "array"},
                                    "description": {"type": "string"},
                                    "indexFilterable": {"nullable": True, "type": "boolean"},
                                    "indexRangeFilters": {"nullable": True, "type": "boolean"},
                                    "indexSearchable": {"nullable": True, "type": "boolean"},
                                    "name": {"type": "string"},
                                    "nestedProperties": {
                                        "description": "The "
                                        "properties "
                                        "of "
                                        "the "
                                        "nested "
                                        "object(s). "
                                        "Applies "
                                        "to "
                                        "object "
                                        "and "
                                        "object[] "
                                        "data "
                                        "types.",
                                        "items": {
                                            "$ref": "#/components/schemas/NestedProperty",
                                            "has_circular_reference": True,
                                        },
                                        "type": "array",
                                        "x-omitempty": True,
                                    },
                                    "tokenization": {
                                        "enum": [
                                            "word",
                                            "lowercase",
                                            "whitespace",
                                            "field",
                                            "trigram",
                                            "gse",
                                            "kagome_kr",
                                            "kagome_ja",
                                            "gse_ch",
                                        ],
                                        "type": "string",
                                    },
                                },
                                "type": "object",
                            },
                            "type": "array",
                            "x-omitempty": True,
                        },
                        "tokenization": {
                            "description": "Determines "
                            "how "
                            "a "
                            "property "
                            "is "
                            "indexed. "
                            "This "
                            "setting "
                            "applies "
                            "to "
                            "`text` "
                            "and "
                            "`text[]` "
                            "data "
                            "types. "
                            "The "
                            "following "
                            "tokenization "
                            "methods "
                            "are "
                            "available:<br/><br/>- "
                            "`word` "
                            "(default): "
                            "Splits "
                            "the "
                            "text "
                            "on "
                            "any "
                            "non-alphanumeric "
                            "characters "
                            "and "
                            "lowercases "
                            "the "
                            "tokens.<br/>- "
                            "`lowercase`: "
                            "Splits "
                            "the "
                            "text "
                            "on "
                            "whitespace "
                            "and "
                            "lowercases "
                            "the "
                            "tokens.<br/>- "
                            "`whitespace`: "
                            "Splits "
                            "the "
                            "text "
                            "on "
                            "whitespace. "
                            "This "
                            "tokenization "
                            "is "
                            "case-sensitive.<br/>- "
                            "`field`: "
                            "Indexes "
                            "the "
                            "entire "
                            "property "
                            "value "
                            "as "
                            "a "
                            "single "
                            "token "
                            "after "
                            "trimming "
                            "whitespace.<br/>- "
                            "`trigram`: "
                            "Splits "
                            "the "
                            "property "
                            "into "
                            "rolling "
                            "trigrams "
                            "(three-character "
                            "sequences).<br/>- "
                            "`gse`: "
                            "Uses "
                            "the "
                            "`gse` "
                            "tokenizer, "
                            "suitable "
                            "for "
                            "Chinese "
                            "language "
                            "text. "
                            "[See "
                            "`gse` "
                            "docs](https://pkg.go.dev/github.com/go-ego/gse#section-readme).<br/>- "
                            "`kagome_ja`: "
                            "Uses "
                            "the "
                            "`Kagome` "
                            "tokenizer "
                            "with "
                            "a "
                            "Japanese "
                            "(IPA) "
                            "dictionary. "
                            "[See "
                            "`kagome` "
                            "docs](https://github.com/ikawaha/kagome).<br/>- "
                            "`kagome_kr`: "
                            "Uses "
                            "the "
                            "`Kagome` "
                            "tokenizer "
                            "with "
                            "a "
                            "Korean "
                            "dictionary. "
                            "[See "
                            "`kagome` "
                            "docs](https://github.com/ikawaha/kagome).<br/><br/>See "
                            "[Reference: "
                            "Tokenization](https://docs.weaviate.io/weaviate/config-refs/collections#tokenization) "
                            "for "
                            "details.",
                            "enum": [
                                "word",
                                "lowercase",
                                "whitespace",
                                "field",
                                "trigram",
                                "gse",
                                "kagome_kr",
                                "kagome_ja",
                                "gse_ch",
                            ],
                            "type": "string",
                        },
                    },
                    "type": "object",
                },
                "type": "array",
            },
            "replicationConfig": {
                "description": "Configure how replication is executed in a cluster",
                "properties": {
                    "asyncEnabled": {
                        "description": "Enable asynchronous replication (default: `false`).",
                        "type": "boolean",
                        "x-omitempty": False,
                    },
                    "deletionStrategy": {
                        "description": "Conflict resolution strategy for deleted objects.",
                        "enum": [
                            "NoAutomatedResolution",
                            "DeleteOnConflict",
                            "TimeBasedResolution",
                        ],
                        "type": "string",
                        "x-omitempty": True,
                    },
                    "factor": {
                        "description": "Number "
                        "of "
                        "times "
                        "a "
                        "collection "
                        "(class) "
                        "is "
                        "replicated "
                        "(default: "
                        "1).",
                        "type": "integer",
                    },
                },
                "type": "object",
            },
            "shardingConfig": {
                "description": "Manage how the index should be "
                "sharded and distributed in the "
                "cluster",
                "properties": {},
                "type": "object",
            },
            "vectorConfig": {
                "additionalProperties": {
                    "properties": {
                        "vectorIndexConfig": {
                            "description": "Vector-index "
                            "config, "
                            "that "
                            "is "
                            "specific "
                            "to "
                            "the "
                            "type "
                            "of "
                            "index "
                            "selected "
                            "in "
                            "vectorIndexType",
                            "properties": {},
                            "type": "object",
                        },
                        "vectorIndexType": {
                            "description": "Name of the vector index to use, eg. (HNSW)",
                            "type": "string",
                        },
                        "vectorizer": {
                            "description": "Configuration "
                            "of "
                            "a "
                            "specific "
                            "vectorizer "
                            "used "
                            "by "
                            "this "
                            "vector",
                            "properties": {},
                            "type": "object",
                        },
                    },
                    "type": "object",
                },
                "description": "Configure named vectors. Either use "
                "this field or `vectorizer`, "
                "`vectorIndexType`, and "
                "`vectorIndexConfig` fields. Available "
                "from `v1.24.0`.",
                "type": "object",
            },
            "vectorIndexConfig": {
                "description": "Vector-index config, that is "
                "specific to the type of index "
                "selected in vectorIndexType",
                "properties": {},
                "type": "object",
            },
            "vectorIndexType": {
                "description": "Name of the vector index type to "
                "use for the collection (e.g. "
                "`hnsw` or `flat`).",
                "type": "string",
            },
            "vectorizer": {
                "description": "Specify how the vectors for this "
                "collection should be determined. The "
                "options are either `none` - this means "
                "you have to import a vector with each "
                "object yourself - or the name of a "
                "module that provides vectorization "
                "capabilities, such as "
                "`text2vec-weaviate`. If left empty, it "
                "will use the globally configured "
                "default "
                "([`DEFAULT_VECTORIZER_MODULE`](https://docs.weaviate.io/deploy/configuration/env-vars)) "
                "which can itself either be `none` or a "
                "specific module.",
                "type": "string",
            },
        },
        "type": "object",
    },
    "UPDATECOLLECTIONSETTINGS_REQUEST_BODY_SCHEMA": {
        "properties": {
            "class": {
                "description": "Name of the collection (formerly 'class') "
                "(required). Multiple words should be "
                "concatenated in CamelCase, e.g. "
                "`ArticleAuthor`.",
                "type": "string",
            },
            "description": {
                "description": "Description of the collection for metadata purposes.",
                "type": "string",
            },
            "invertedIndexConfig": {
                "description": "Configure the inverted index "
                "built into Weaviate. See "
                "[Reference: Inverted "
                "index](https://docs.weaviate.io/weaviate/config-refs/indexing/inverted-index#inverted-index-parameters) "
                "for details.",
                "properties": {
                    "bm25": {
                        "description": "Tuning parameters for the BM25 algorithm.",
                        "properties": {
                            "b": {
                                "description": "Calibrates "
                                "term-weight "
                                "scaling "
                                "based "
                                "on "
                                "the "
                                "document "
                                "length "
                                "(default: "
                                "0.75).",
                                "format": "float",
                                "type": "number",
                            },
                            "k1": {
                                "description": "Calibrates "
                                "term-weight "
                                "scaling "
                                "based "
                                "on "
                                "the "
                                "term "
                                "frequency "
                                "within "
                                "a "
                                "document "
                                "(default: "
                                "1.2).",
                                "format": "float",
                                "type": "number",
                            },
                        },
                        "type": "object",
                    },
                    "cleanupIntervalSeconds": {
                        "description": "Asynchronous "
                        "index "
                        "clean "
                        "up "
                        "happens "
                        "every "
                        "n "
                        "seconds "
                        "(default: "
                        "60).",
                        "format": "int",
                        "type": "number",
                    },
                    "indexNullState": {
                        "description": "Index each object with the null state (default: `false`).",
                        "type": "boolean",
                    },
                    "indexPropertyLength": {
                        "description": "Index length of properties (default: `false`).",
                        "type": "boolean",
                    },
                    "indexTimestamps": {
                        "description": "Index "
                        "each "
                        "object "
                        "by "
                        "its "
                        "internal "
                        "timestamps "
                        "(default: "
                        "`false`).",
                        "type": "boolean",
                    },
                    "stopwords": {
                        "description": "Fine-grained control over stopword list usage.",
                        "properties": {
                            "additions": {
                                "description": "Stopwords "
                                "to "
                                "be "
                                "considered "
                                "additionally "
                                "(default: "
                                "[]). "
                                "Can "
                                "be "
                                "any "
                                "array "
                                "of "
                                "custom "
                                "strings.",
                                "items": {"type": "string"},
                                "type": "array",
                            },
                            "preset": {
                                "description": "Pre-existing "
                                "list "
                                "of "
                                "common "
                                "words "
                                "by "
                                "language "
                                "(default: "
                                "`en`). "
                                "Options: "
                                "[`en`, "
                                "`none`].",
                                "type": "string",
                            },
                            "removals": {
                                "description": "Stopwords "
                                "to "
                                "be "
                                "removed "
                                "from "
                                "consideration "
                                "(default: "
                                "[]). "
                                "Can "
                                "be "
                                "any "
                                "array "
                                "of "
                                "custom "
                                "strings.",
                                "items": {"type": "string"},
                                "type": "array",
                            },
                        },
                        "type": "object",
                    },
                    "usingBlockMaxWAND": {
                        "description": "Using "
                        "BlockMax "
                        "WAND "
                        "for "
                        "query "
                        "execution "
                        "(default: "
                        "`false`, "
                        "will "
                        "be "
                        "`true` "
                        "for "
                        "new "
                        "collections "
                        "created "
                        "after "
                        "1.30).",
                        "type": "boolean",
                    },
                },
                "type": "object",
            },
            "moduleConfig": {
                "description": "Configuration specific to modules in a collection context.",
                "properties": {},
                "type": "object",
            },
            "multiTenancyConfig": {
                "description": "Configuration related to multi-tenancy within a collection (class)",
                "properties": {
                    "autoTenantActivation": {
                        "description": "Existing "
                        "tenants "
                        "should "
                        "(not) "
                        "be "
                        "turned "
                        "HOT "
                        "implicitly "
                        "when "
                        "they "
                        "are "
                        "accessed "
                        "and "
                        "in "
                        "another "
                        "activity "
                        "status "
                        "(default: "
                        "`false`).",
                        "type": "boolean",
                        "x-omitempty": False,
                    },
                    "autoTenantCreation": {
                        "description": "Nonexistent "
                        "tenants "
                        "should "
                        "(not) "
                        "be "
                        "created "
                        "implicitly "
                        "(default: "
                        "`false`).",
                        "type": "boolean",
                        "x-omitempty": False,
                    },
                    "enabled": {
                        "description": "Whether "
                        "or "
                        "not "
                        "multi-tenancy "
                        "is "
                        "enabled "
                        "for "
                        "this "
                        "collection "
                        "(class) "
                        "(default: "
                        "`false`).",
                        "type": "boolean",
                        "x-omitempty": False,
                    },
                },
                "type": "object",
            },
            "properties": {
                "description": "Define properties of the collection.",
                "items": {
                    "properties": {
                        "dataType": {
                            "description": "Data "
                            "type "
                            "of "
                            "the "
                            "property "
                            "(required). "
                            "If "
                            "it "
                            "starts "
                            "with "
                            "a "
                            "capital "
                            "(for "
                            "example "
                            "Person), "
                            "may "
                            "be "
                            "a "
                            "reference "
                            "to "
                            "another "
                            "type.",
                            "items": {"type": "string"},
                            "type": "array",
                        },
                        "description": {
                            "description": "Description of the property.",
                            "type": "string",
                        },
                        "indexFilterable": {
                            "description": "Whether "
                            "to "
                            "include "
                            "this "
                            "property "
                            "in "
                            "the "
                            "filterable, "
                            "Roaring "
                            "Bitmap "
                            "index. "
                            "If "
                            "`false`, "
                            "this "
                            "property "
                            "cannot "
                            "be "
                            "used "
                            "in "
                            "`where` "
                            "filters. "
                            "<br/><br/>Note: "
                            "Unrelated "
                            "to "
                            "vectorization "
                            "behavior.",
                            "nullable": True,
                            "type": "boolean",
                        },
                        "indexInverted": {
                            "description": "(Deprecated). "
                            "Whether "
                            "to "
                            "include "
                            "this "
                            "property "
                            "in "
                            "the "
                            "inverted "
                            "index. "
                            "If "
                            "`false`, "
                            "this "
                            "property "
                            "cannot "
                            "be "
                            "used "
                            "in "
                            "`where` "
                            "filters, "
                            "`bm25` "
                            "or "
                            "`hybrid` "
                            "search. "
                            "<br/><br/>Unrelated "
                            "to "
                            "vectorization "
                            "behavior "
                            "(deprecated "
                            "as "
                            "of "
                            "v1.19; "
                            "use "
                            "indexFilterable "
                            "or/and "
                            "indexSearchable "
                            "instead)",
                            "nullable": True,
                            "type": "boolean",
                        },
                        "indexRangeFilters": {
                            "description": "Whether "
                            "to "
                            "include "
                            "this "
                            "property "
                            "in "
                            "the "
                            "filterable, "
                            "range-based "
                            "Roaring "
                            "Bitmap "
                            "index. "
                            "Provides "
                            "better "
                            "performance "
                            "for "
                            "range "
                            "queries "
                            "compared "
                            "to "
                            "filterable "
                            "index "
                            "in "
                            "large "
                            "datasets. "
                            "Applicable "
                            "only "
                            "to "
                            "properties "
                            "of "
                            "data "
                            "type "
                            "int, "
                            "number, "
                            "date.",
                            "nullable": True,
                            "type": "boolean",
                        },
                        "indexSearchable": {
                            "description": "Optional. "
                            "Should "
                            "this "
                            "property "
                            "be "
                            "indexed "
                            "in "
                            "the "
                            "inverted "
                            "index. "
                            "Defaults "
                            "to "
                            "true. "
                            "Applicable "
                            "only "
                            "to "
                            "properties "
                            "of "
                            "data "
                            "type "
                            "text "
                            "and "
                            "text[]. "
                            "If "
                            "you "
                            "choose "
                            "false, "
                            "you "
                            "will "
                            "not "
                            "be "
                            "able "
                            "to "
                            "use "
                            "this "
                            "property "
                            "in "
                            "bm25 "
                            "or "
                            "hybrid "
                            "search. "
                            "This "
                            "property "
                            "has "
                            "no "
                            "affect "
                            "on "
                            "vectorization "
                            "decisions "
                            "done "
                            "by "
                            "modules",
                            "nullable": True,
                            "type": "boolean",
                        },
                        "moduleConfig": {
                            "description": "Configuration "
                            "specific "
                            "to "
                            "modules "
                            "in "
                            "a "
                            "collection "
                            "context.",
                            "properties": {},
                            "type": "object",
                        },
                        "name": {
                            "description": "The "
                            "name "
                            "of "
                            "the "
                            "property "
                            "(required). "
                            "Multiple "
                            "words "
                            "should "
                            "be "
                            "concatenated "
                            "in "
                            "camelCase, "
                            "e.g. "
                            "`nameOfAuthor`.",
                            "type": "string",
                        },
                        "nestedProperties": {
                            "description": "The "
                            "properties "
                            "of "
                            "the "
                            "nested "
                            "object(s). "
                            "Applies "
                            "to "
                            "object "
                            "and "
                            "object[] "
                            "data "
                            "types.",
                            "items": {
                                "properties": {
                                    "dataType": {"items": {"type": "string"}, "type": "array"},
                                    "description": {"type": "string"},
                                    "indexFilterable": {"nullable": True, "type": "boolean"},
                                    "indexRangeFilters": {"nullable": True, "type": "boolean"},
                                    "indexSearchable": {"nullable": True, "type": "boolean"},
                                    "name": {"type": "string"},
                                    "nestedProperties": {
                                        "description": "The "
                                        "properties "
                                        "of "
                                        "the "
                                        "nested "
                                        "object(s). "
                                        "Applies "
                                        "to "
                                        "object "
                                        "and "
                                        "object[] "
                                        "data "
                                        "types.",
                                        "items": {
                                            "$ref": "#/components/schemas/NestedProperty",
                                            "has_circular_reference": True,
                                        },
                                        "type": "array",
                                        "x-omitempty": True,
                                    },
                                    "tokenization": {
                                        "enum": [
                                            "word",
                                            "lowercase",
                                            "whitespace",
                                            "field",
                                            "trigram",
                                            "gse",
                                            "kagome_kr",
                                            "kagome_ja",
                                            "gse_ch",
                                        ],
                                        "type": "string",
                                    },
                                },
                                "type": "object",
                            },
                            "type": "array",
                            "x-omitempty": True,
                        },
                        "tokenization": {
                            "description": "Determines "
                            "how "
                            "a "
                            "property "
                            "is "
                            "indexed. "
                            "This "
                            "setting "
                            "applies "
                            "to "
                            "`text` "
                            "and "
                            "`text[]` "
                            "data "
                            "types. "
                            "The "
                            "following "
                            "tokenization "
                            "methods "
                            "are "
                            "available:<br/><br/>- "
                            "`word` "
                            "(default): "
                            "Splits "
                            "the "
                            "text "
                            "on "
                            "any "
                            "non-alphanumeric "
                            "characters "
                            "and "
                            "lowercases "
                            "the "
                            "tokens.<br/>- "
                            "`lowercase`: "
                            "Splits "
                            "the "
                            "text "
                            "on "
                            "whitespace "
                            "and "
                            "lowercases "
                            "the "
                            "tokens.<br/>- "
                            "`whitespace`: "
                            "Splits "
                            "the "
                            "text "
                            "on "
                            "whitespace. "
                            "This "
                            "tokenization "
                            "is "
                            "case-sensitive.<br/>- "
                            "`field`: "
                            "Indexes "
                            "the "
                            "entire "
                            "property "
                            "value "
                            "as "
                            "a "
                            "single "
                            "token "
                            "after "
                            "trimming "
                            "whitespace.<br/>- "
                            "`trigram`: "
                            "Splits "
                            "the "
                            "property "
                            "into "
                            "rolling "
                            "trigrams "
                            "(three-character "
                            "sequences).<br/>- "
                            "`gse`: "
                            "Uses "
                            "the "
                            "`gse` "
                            "tokenizer, "
                            "suitable "
                            "for "
                            "Chinese "
                            "language "
                            "text. "
                            "[See "
                            "`gse` "
                            "docs](https://pkg.go.dev/github.com/go-ego/gse#section-readme).<br/>- "
                            "`kagome_ja`: "
                            "Uses "
                            "the "
                            "`Kagome` "
                            "tokenizer "
                            "with "
                            "a "
                            "Japanese "
                            "(IPA) "
                            "dictionary. "
                            "[See "
                            "`kagome` "
                            "docs](https://github.com/ikawaha/kagome).<br/>- "
                            "`kagome_kr`: "
                            "Uses "
                            "the "
                            "`Kagome` "
                            "tokenizer "
                            "with "
                            "a "
                            "Korean "
                            "dictionary. "
                            "[See "
                            "`kagome` "
                            "docs](https://github.com/ikawaha/kagome).<br/><br/>See "
                            "[Reference: "
                            "Tokenization](https://docs.weaviate.io/weaviate/config-refs/collections#tokenization) "
                            "for "
                            "details.",
                            "enum": [
                                "word",
                                "lowercase",
                                "whitespace",
                                "field",
                                "trigram",
                                "gse",
                                "kagome_kr",
                                "kagome_ja",
                                "gse_ch",
                            ],
                            "type": "string",
                        },
                    },
                    "type": "object",
                },
                "type": "array",
            },
            "replicationConfig": {
                "description": "Configure how replication is executed in a cluster",
                "properties": {
                    "asyncEnabled": {
                        "description": "Enable asynchronous replication (default: `false`).",
                        "type": "boolean",
                        "x-omitempty": False,
                    },
                    "deletionStrategy": {
                        "description": "Conflict resolution strategy for deleted objects.",
                        "enum": [
                            "NoAutomatedResolution",
                            "DeleteOnConflict",
                            "TimeBasedResolution",
                        ],
                        "type": "string",
                        "x-omitempty": True,
                    },
                    "factor": {
                        "description": "Number "
                        "of "
                        "times "
                        "a "
                        "collection "
                        "(class) "
                        "is "
                        "replicated "
                        "(default: "
                        "1).",
                        "type": "integer",
                    },
                },
                "type": "object",
            },
            "shardingConfig": {
                "description": "Manage how the index should be "
                "sharded and distributed in the "
                "cluster",
                "properties": {},
                "type": "object",
            },
            "vectorConfig": {
                "additionalProperties": {
                    "properties": {
                        "vectorIndexConfig": {
                            "description": "Vector-index "
                            "config, "
                            "that "
                            "is "
                            "specific "
                            "to "
                            "the "
                            "type "
                            "of "
                            "index "
                            "selected "
                            "in "
                            "vectorIndexType",
                            "properties": {},
                            "type": "object",
                        },
                        "vectorIndexType": {
                            "description": "Name of the vector index to use, eg. (HNSW)",
                            "type": "string",
                        },
                        "vectorizer": {
                            "description": "Configuration "
                            "of "
                            "a "
                            "specific "
                            "vectorizer "
                            "used "
                            "by "
                            "this "
                            "vector",
                            "properties": {},
                            "type": "object",
                        },
                    },
                    "type": "object",
                },
                "description": "Configure named vectors. Either use "
                "this field or `vectorizer`, "
                "`vectorIndexType`, and "
                "`vectorIndexConfig` fields. Available "
                "from `v1.24.0`.",
                "type": "object",
            },
            "vectorIndexConfig": {
                "description": "Vector-index config, that is "
                "specific to the type of index "
                "selected in vectorIndexType",
                "properties": {},
                "type": "object",
            },
            "vectorIndexType": {
                "description": "Name of the vector index type to "
                "use for the collection (e.g. "
                "`hnsw` or `flat`).",
                "type": "string",
            },
            "vectorizer": {
                "description": "Specify how the vectors for this "
                "collection should be determined. The "
                "options are either `none` - this means "
                "you have to import a vector with each "
                "object yourself - or the name of a "
                "module that provides vectorization "
                "capabilities, such as "
                "`text2vec-weaviate`. If left empty, it "
                "will use the globally configured "
                "default "
                "([`DEFAULT_VECTORIZER_MODULE`](https://docs.weaviate.io/deploy/configuration/env-vars)) "
                "which can itself either be `none` or a "
                "specific module.",
                "type": "string",
            },
        },
        "type": "object",
    },
    "ADDPROPERTYTOCOLLECTION_REQUEST_BODY_SCHEMA": {
        "properties": {
            "dataType": {
                "description": "Data type of the property (required). If "
                "it starts with a capital (for example "
                "Person), may be a reference to another "
                "type.",
                "items": {"type": "string"},
                "type": "array",
            },
            "description": {"description": "Description of the property.", "type": "string"},
            "indexFilterable": {
                "description": "Whether to include this property "
                "in the filterable, Roaring Bitmap "
                "index. If `false`, this property "
                "cannot be used in `where` filters. "
                "<br/><br/>Note: Unrelated to "
                "vectorization behavior.",
                "nullable": True,
                "type": "boolean",
            },
            "indexInverted": {
                "description": "(Deprecated). Whether to include "
                "this property in the inverted index. "
                "If `false`, this property cannot be "
                "used in `where` filters, `bm25` or "
                "`hybrid` search. <br/><br/>Unrelated "
                "to vectorization behavior "
                "(deprecated as of v1.19; use "
                "indexFilterable or/and "
                "indexSearchable instead)",
                "nullable": True,
                "type": "boolean",
            },
            "indexRangeFilters": {
                "description": "Whether to include this property "
                "in the filterable, range-based "
                "Roaring Bitmap index. Provides "
                "better performance for range "
                "queries compared to filterable "
                "index in large datasets. "
                "Applicable only to properties of "
                "data type int, number, date.",
                "nullable": True,
                "type": "boolean",
            },
            "indexSearchable": {
                "description": "Optional. Should this property be "
                "indexed in the inverted index. "
                "Defaults to true. Applicable only "
                "to properties of data type text "
                "and text[]. If you choose false, "
                "you will not be able to use this "
                "property in bm25 or hybrid search. "
                "This property has no affect on "
                "vectorization decisions done by "
                "modules",
                "nullable": True,
                "type": "boolean",
            },
            "moduleConfig": {
                "description": "Configuration specific to modules in a collection context.",
                "properties": {},
                "type": "object",
            },
            "name": {
                "description": "The name of the property (required). Multiple "
                "words should be concatenated in camelCase, "
                "e.g. `nameOfAuthor`.",
                "type": "string",
            },
            "nestedProperties": {
                "description": "The properties of the nested "
                "object(s). Applies to object and "
                "object[] data types.",
                "items": {
                    "properties": {
                        "dataType": {"items": {"type": "string"}, "type": "array"},
                        "description": {"type": "string"},
                        "indexFilterable": {"nullable": True, "type": "boolean"},
                        "indexRangeFilters": {"nullable": True, "type": "boolean"},
                        "indexSearchable": {"nullable": True, "type": "boolean"},
                        "name": {"type": "string"},
                        "nestedProperties": {
                            "description": "The "
                            "properties "
                            "of "
                            "the "
                            "nested "
                            "object(s). "
                            "Applies "
                            "to "
                            "object "
                            "and "
                            "object[] "
                            "data "
                            "types.",
                            "items": {
                                "$ref": "#/components/schemas/NestedProperty",
                                "has_circular_reference": True,
                            },
                            "type": "array",
                            "x-omitempty": True,
                        },
                        "tokenization": {
                            "enum": [
                                "word",
                                "lowercase",
                                "whitespace",
                                "field",
                                "trigram",
                                "gse",
                                "kagome_kr",
                                "kagome_ja",
                                "gse_ch",
                            ],
                            "type": "string",
                        },
                    },
                    "type": "object",
                },
                "type": "array",
                "x-omitempty": True,
            },
            "tokenization": {
                "description": "Determines how a property is indexed. "
                "This setting applies to `text` and "
                "`text[]` data types. The following "
                "tokenization methods are "
                "available:<br/><br/>- `word` "
                "(default): Splits the text on any "
                "non-alphanumeric characters and "
                "lowercases the tokens.<br/>- "
                "`lowercase`: Splits the text on "
                "whitespace and lowercases the "
                "tokens.<br/>- `whitespace`: Splits "
                "the text on whitespace. This "
                "tokenization is case-sensitive.<br/>- "
                "`field`: Indexes the entire property "
                "value as a single token after "
                "trimming whitespace.<br/>- `trigram`: "
                "Splits the property into rolling "
                "trigrams (three-character "
                "sequences).<br/>- `gse`: Uses the "
                "`gse` tokenizer, suitable for Chinese "
                "language text. [See `gse` "
                "docs](https://pkg.go.dev/github.com/go-ego/gse#section-readme).<br/>- "
                "`kagome_ja`: Uses the `Kagome` "
                "tokenizer with a Japanese (IPA) "
                "dictionary. [See `kagome` "
                "docs](https://github.com/ikawaha/kagome).<br/>- "
                "`kagome_kr`: Uses the `Kagome` "
                "tokenizer with a Korean dictionary. "
                "[See `kagome` "
                "docs](https://github.com/ikawaha/kagome).<br/><br/>See "
                "[Reference: "
                "Tokenization](https://docs.weaviate.io/weaviate/config-refs/collections#tokenization) "
                "for details.",
                "enum": [
                    "word",
                    "lowercase",
                    "whitespace",
                    "field",
                    "trigram",
                    "gse",
                    "kagome_kr",
                    "kagome_ja",
                    "gse_ch",
                ],
                "type": "string",
            },
        },
        "type": "object",
    },
    "UPDATETENANTSTATUS_REQUEST_BODY_SCHEMA": {
        "items": {
            "description": "Attributes representing a single tenant within Weaviate.",
            "properties": {
                "activityStatus": {
                    "description": "The activity status of "
                    "the tenant, which "
                    "determines if it is "
                    "queryable and where its "
                    "data is "
                    "stored.<br/><br/><b>Available "
                    "Statuses:</b><br/>- "
                    "`ACTIVE`: The tenant is "
                    "fully operational and "
                    "ready for queries. Data "
                    "is stored on local, hot "
                    "storage.<br/>- "
                    "`INACTIVE`: The tenant is "
                    "not queryable. Data is "
                    "stored locally.<br/>- "
                    "`OFFLOADED`: The tenant "
                    "is inactive and its data "
                    "is stored in a remote "
                    "cloud "
                    "backend.<br/><br/><b>Usage "
                    "Rules:</b><br/>- <b>On "
                    "Create:</b> This field is "
                    "optional and defaults to "
                    "`ACTIVE`. Allowed values "
                    "are `ACTIVE` and "
                    "`INACTIVE`.<br/>- <b>On "
                    "Update:</b> This field is "
                    "required. Allowed values "
                    "are `ACTIVE`, `INACTIVE`, "
                    "and "
                    "`OFFLOADED`.<br/><br/><b>Read-Only "
                    "Statuses:</b><br/>The "
                    "following statuses are "
                    "set by the server and "
                    "indicate a tenant is "
                    "transitioning between "
                    "states:<br/>- "
                    "`OFFLOADING`<br/>- "
                    "`ONLOADING`<br/><br/><b>Note "
                    "on Deprecated "
                    "Names:</b><br/>For "
                    "backward compatibility, "
                    "deprecated names are "
                    "still accepted and are "
                    "mapped to their modern "
                    "equivalents: `HOT` (now "
                    "`ACTIVE`), `COLD` (now "
                    "`INACTIVE`), `FROZEN` "
                    "(now `OFFLOADED`), "
                    "`FREEZING` (now "
                    "`OFFLOADING`), "
                    "`UNFREEZING` (now "
                    "`ONLOADING`).",
                    "enum": [
                        "ACTIVE",
                        "INACTIVE",
                        "OFFLOADED",
                        "OFFLOADING",
                        "ONLOADING",
                        "HOT",
                        "COLD",
                        "FROZEN",
                        "FREEZING",
                        "UNFREEZING",
                    ],
                    "type": "string",
                },
                "name": {"description": "The name of the tenant (required).", "type": "string"},
            },
            "type": "object",
        },
        "type": "array",
    },
    "CREATETENANTS_REQUEST_BODY_SCHEMA": {
        "items": {
            "description": "Attributes representing a single tenant within Weaviate.",
            "properties": {
                "activityStatus": {
                    "description": "The activity status of "
                    "the tenant, which "
                    "determines if it is "
                    "queryable and where its "
                    "data is "
                    "stored.<br/><br/><b>Available "
                    "Statuses:</b><br/>- "
                    "`ACTIVE`: The tenant is "
                    "fully operational and "
                    "ready for queries. Data "
                    "is stored on local, hot "
                    "storage.<br/>- "
                    "`INACTIVE`: The tenant is "
                    "not queryable. Data is "
                    "stored locally.<br/>- "
                    "`OFFLOADED`: The tenant "
                    "is inactive and its data "
                    "is stored in a remote "
                    "cloud "
                    "backend.<br/><br/><b>Usage "
                    "Rules:</b><br/>- <b>On "
                    "Create:</b> This field is "
                    "optional and defaults to "
                    "`ACTIVE`. Allowed values "
                    "are `ACTIVE` and "
                    "`INACTIVE`.<br/>- <b>On "
                    "Update:</b> This field is "
                    "required. Allowed values "
                    "are `ACTIVE`, `INACTIVE`, "
                    "and "
                    "`OFFLOADED`.<br/><br/><b>Read-Only "
                    "Statuses:</b><br/>The "
                    "following statuses are "
                    "set by the server and "
                    "indicate a tenant is "
                    "transitioning between "
                    "states:<br/>- "
                    "`OFFLOADING`<br/>- "
                    "`ONLOADING`<br/><br/><b>Note "
                    "on Deprecated "
                    "Names:</b><br/>For "
                    "backward compatibility, "
                    "deprecated names are "
                    "still accepted and are "
                    "mapped to their modern "
                    "equivalents: `HOT` (now "
                    "`ACTIVE`), `COLD` (now "
                    "`INACTIVE`), `FROZEN` "
                    "(now `OFFLOADED`), "
                    "`FREEZING` (now "
                    "`OFFLOADING`), "
                    "`UNFREEZING` (now "
                    "`ONLOADING`).",
                    "enum": [
                        "ACTIVE",
                        "INACTIVE",
                        "OFFLOADED",
                        "OFFLOADING",
                        "ONLOADING",
                        "HOT",
                        "COLD",
                        "FROZEN",
                        "FREEZING",
                        "UNFREEZING",
                    ],
                    "type": "string",
                },
                "name": {"description": "The name of the tenant (required).", "type": "string"},
            },
            "type": "object",
        },
        "type": "array",
    },
    "RESTOREBACKUP_REQUEST_BODY_SCHEMA": {
        "description": "Request body for restoring a backup for a set of collections (classes).",
        "properties": {
            "config": {
                "description": "Backup custom configuration",
                "properties": {
                    "Bucket": {
                        "description": "Name of the bucket, container, volume, etc",
                        "type": "string",
                    },
                    "CPUPercentage": {
                        "description": "Desired CPU core utilization ranging from 1%-80%",
                        "maximum": 80,
                        "minimum": 1,
                        "nullable": False,
                        "type": "integer",
                    },
                    "Endpoint": {
                        "description": "name of the endpoint, e.g. s3.amazonaws.com",
                        "type": "string",
                    },
                    "Path": {"description": "Path within the bucket", "type": "string"},
                    "rolesOptions": {
                        "default": "noRestore",
                        "description": "How roles should be restored",
                        "enum": ["noRestore", "all"],
                        "type": "string",
                    },
                    "usersOptions": {
                        "default": "noRestore",
                        "description": "How users should be restored",
                        "enum": ["noRestore", "all"],
                        "type": "string",
                    },
                },
                "type": "object",
            },
            "exclude": {
                "description": "List of collections (classes) to exclude "
                "from the backup restoration process.",
                "items": {"type": "string"},
                "type": "array",
            },
            "include": {
                "description": "List of collections (classes) to include "
                "in the backup restoration process.",
                "items": {"type": "string"},
                "type": "array",
            },
            "node_mapping": {
                "additionalProperties": {"type": "string"},
                "description": "Allows overriding the node names "
                "stored in the backup with different "
                "ones. Useful when restoring backups "
                "to a different environment.",
                "type": "object",
            },
            "overwriteAlias": {
                "description": "Allows ovewriting the collection alias if there is a conflict",
                "type": "boolean",
            },
        },
        "type": "object",
    },
    "INITIATECLASSIFICATIONTASK_REQUEST_BODY_SCHEMA": {
        "description": "Manage classifications, trigger them and view status of past "
        "classifications.",
        "properties": {
            "basedOnProperties": {
                "description": "Base the text-based classification on these fields (of type text).",
                "example": ["description"],
                "items": {"type": "string"},
                "type": "array",
            },
            "class": {
                "description": "The name of the collection (class) which is "
                "used in this classification.",
                "example": "City",
                "type": "string",
            },
            "classifyProperties": {
                "description": "Which ref-property to set as part of the classification.",
                "example": ["inCountry"],
                "items": {"type": "string"},
                "type": "array",
            },
            "error": {
                "default": "",
                "description": "Error message if status == failed.",
                "example": "classify xzy: something went wrong",
                "type": "string",
            },
            "filters": {
                "properties": {
                    "sourceWhere": {
                        "description": "Filter search results using a where filter.",
                        "properties": {
                            "operands": {
                                "description": "Combine "
                                "multiple "
                                "where "
                                "filters, "
                                "requires "
                                "'And' "
                                "or "
                                "'Or' "
                                "operator.",
                                "items": {
                                    "$ref": "#/components/schemas/WhereFilter",
                                    "has_circular_reference": True,
                                },
                                "type": "array",
                            },
                            "operator": {
                                "description": "Operator to use.",
                                "enum": [
                                    "And",
                                    "Or",
                                    "Equal",
                                    "Like",
                                    "NotEqual",
                                    "GreaterThan",
                                    "GreaterThanEqual",
                                    "LessThan",
                                    "LessThanEqual",
                                    "WithinGeoRange",
                                    "IsNull",
                                    "ContainsAny",
                                    "ContainsAll",
                                    "ContainsNone",
                                    "Not",
                                ],
                                "example": "GreaterThanEqual",
                                "type": "string",
                            },
                            "path": {
                                "description": "Path to the property currently being filtered.",
                                "example": ["inCity", "city", "name"],
                                "items": {"type": "string"},
                                "type": "array",
                            },
                            "valueBoolean": {
                                "description": "value as boolean",
                                "example": False,
                                "nullable": True,
                                "type": "boolean",
                            },
                            "valueBooleanArray": {
                                "description": "value as boolean",
                                "example": [True, False],
                                "items": {"type": "boolean"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueDate": {
                                "description": "value as date (as string)",
                                "example": "TODO",
                                "nullable": True,
                                "type": "string",
                            },
                            "valueDateArray": {
                                "description": "value as date (as string)",
                                "example": "TODO",
                                "items": {"type": "string"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueGeoRange": {
                                "description": "Filter within a distance of a georange.",
                                "properties": {
                                    "distance": {
                                        "properties": {
                                            "max": {"format": "float64", "type": "number"}
                                        },
                                        "type": "object",
                                    },
                                    "geoCoordinates": {
                                        "properties": {
                                            "latitude": {
                                                "description": "The "
                                                "latitude "
                                                "of "
                                                "the "
                                                "point "
                                                "on "
                                                "earth "
                                                "in "
                                                "decimal "
                                                "form.",
                                                "format": "float",
                                                "nullable": True,
                                                "type": "number",
                                            },
                                            "longitude": {
                                                "description": "The "
                                                "longitude "
                                                "of "
                                                "the "
                                                "point "
                                                "on "
                                                "earth "
                                                "in "
                                                "decimal "
                                                "form.",
                                                "format": "float",
                                                "nullable": True,
                                                "type": "number",
                                            },
                                        },
                                        "type": "object",
                                    },
                                },
                                "type": "object",
                            },
                            "valueInt": {
                                "description": "value as integer",
                                "example": 2000,
                                "format": "int64",
                                "nullable": True,
                                "type": "integer",
                            },
                            "valueIntArray": {
                                "description": "value as integer",
                                "example": "[100, 200]",
                                "items": {"format": "int64", "type": "integer"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueNumber": {
                                "description": "value as number/float",
                                "example": 3.14,
                                "format": "float64",
                                "nullable": True,
                                "type": "number",
                            },
                            "valueNumberArray": {
                                "description": "value as number/float",
                                "example": [3.14],
                                "items": {"format": "float64", "type": "number"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueString": {
                                "description": "value "
                                "as "
                                "text "
                                "(deprecated "
                                "as "
                                "of "
                                "v1.19; "
                                "alias "
                                "for "
                                "valueText)",
                                "example": "my search term",
                                "nullable": True,
                                "type": "string",
                            },
                            "valueStringArray": {
                                "description": "value "
                                "as "
                                "text "
                                "(deprecated "
                                "as "
                                "of "
                                "v1.19; "
                                "alias "
                                "for "
                                "valueText)",
                                "example": ["my search term"],
                                "items": {"type": "string"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueText": {
                                "description": "value as text",
                                "example": "my search term",
                                "nullable": True,
                                "type": "string",
                            },
                            "valueTextArray": {
                                "description": "value as text",
                                "example": ["my search term"],
                                "items": {"type": "string"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                        },
                        "type": "object",
                    },
                    "targetWhere": {
                        "description": "Filter search results using a where filter.",
                        "properties": {
                            "operands": {
                                "description": "Combine "
                                "multiple "
                                "where "
                                "filters, "
                                "requires "
                                "'And' "
                                "or "
                                "'Or' "
                                "operator.",
                                "items": {
                                    "$ref": "#/components/schemas/WhereFilter",
                                    "has_circular_reference": True,
                                },
                                "type": "array",
                            },
                            "operator": {
                                "description": "Operator to use.",
                                "enum": [
                                    "And",
                                    "Or",
                                    "Equal",
                                    "Like",
                                    "NotEqual",
                                    "GreaterThan",
                                    "GreaterThanEqual",
                                    "LessThan",
                                    "LessThanEqual",
                                    "WithinGeoRange",
                                    "IsNull",
                                    "ContainsAny",
                                    "ContainsAll",
                                    "ContainsNone",
                                    "Not",
                                ],
                                "example": "GreaterThanEqual",
                                "type": "string",
                            },
                            "path": {
                                "description": "Path to the property currently being filtered.",
                                "example": ["inCity", "city", "name"],
                                "items": {"type": "string"},
                                "type": "array",
                            },
                            "valueBoolean": {
                                "description": "value as boolean",
                                "example": False,
                                "nullable": True,
                                "type": "boolean",
                            },
                            "valueBooleanArray": {
                                "description": "value as boolean",
                                "example": [True, False],
                                "items": {"type": "boolean"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueDate": {
                                "description": "value as date (as string)",
                                "example": "TODO",
                                "nullable": True,
                                "type": "string",
                            },
                            "valueDateArray": {
                                "description": "value as date (as string)",
                                "example": "TODO",
                                "items": {"type": "string"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueGeoRange": {
                                "description": "Filter within a distance of a georange.",
                                "properties": {
                                    "distance": {
                                        "properties": {
                                            "max": {"format": "float64", "type": "number"}
                                        },
                                        "type": "object",
                                    },
                                    "geoCoordinates": {
                                        "properties": {
                                            "latitude": {
                                                "description": "The "
                                                "latitude "
                                                "of "
                                                "the "
                                                "point "
                                                "on "
                                                "earth "
                                                "in "
                                                "decimal "
                                                "form.",
                                                "format": "float",
                                                "nullable": True,
                                                "type": "number",
                                            },
                                            "longitude": {
                                                "description": "The "
                                                "longitude "
                                                "of "
                                                "the "
                                                "point "
                                                "on "
                                                "earth "
                                                "in "
                                                "decimal "
                                                "form.",
                                                "format": "float",
                                                "nullable": True,
                                                "type": "number",
                                            },
                                        },
                                        "type": "object",
                                    },
                                },
                                "type": "object",
                            },
                            "valueInt": {
                                "description": "value as integer",
                                "example": 2000,
                                "format": "int64",
                                "nullable": True,
                                "type": "integer",
                            },
                            "valueIntArray": {
                                "description": "value as integer",
                                "example": "[100, 200]",
                                "items": {"format": "int64", "type": "integer"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueNumber": {
                                "description": "value as number/float",
                                "example": 3.14,
                                "format": "float64",
                                "nullable": True,
                                "type": "number",
                            },
                            "valueNumberArray": {
                                "description": "value as number/float",
                                "example": [3.14],
                                "items": {"format": "float64", "type": "number"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueString": {
                                "description": "value "
                                "as "
                                "text "
                                "(deprecated "
                                "as "
                                "of "
                                "v1.19; "
                                "alias "
                                "for "
                                "valueText)",
                                "example": "my search term",
                                "nullable": True,
                                "type": "string",
                            },
                            "valueStringArray": {
                                "description": "value "
                                "as "
                                "text "
                                "(deprecated "
                                "as "
                                "of "
                                "v1.19; "
                                "alias "
                                "for "
                                "valueText)",
                                "example": ["my search term"],
                                "items": {"type": "string"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueText": {
                                "description": "value as text",
                                "example": "my search term",
                                "nullable": True,
                                "type": "string",
                            },
                            "valueTextArray": {
                                "description": "value as text",
                                "example": ["my search term"],
                                "items": {"type": "string"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                        },
                        "type": "object",
                    },
                    "trainingSetWhere": {
                        "description": "Filter search results using a where filter.",
                        "properties": {
                            "operands": {
                                "description": "Combine "
                                "multiple "
                                "where "
                                "filters, "
                                "requires "
                                "'And' "
                                "or "
                                "'Or' "
                                "operator.",
                                "items": {
                                    "$ref": "#/components/schemas/WhereFilter",
                                    "has_circular_reference": True,
                                },
                                "type": "array",
                            },
                            "operator": {
                                "description": "Operator to use.",
                                "enum": [
                                    "And",
                                    "Or",
                                    "Equal",
                                    "Like",
                                    "NotEqual",
                                    "GreaterThan",
                                    "GreaterThanEqual",
                                    "LessThan",
                                    "LessThanEqual",
                                    "WithinGeoRange",
                                    "IsNull",
                                    "ContainsAny",
                                    "ContainsAll",
                                    "ContainsNone",
                                    "Not",
                                ],
                                "example": "GreaterThanEqual",
                                "type": "string",
                            },
                            "path": {
                                "description": "Path to the property currently being filtered.",
                                "example": ["inCity", "city", "name"],
                                "items": {"type": "string"},
                                "type": "array",
                            },
                            "valueBoolean": {
                                "description": "value as boolean",
                                "example": False,
                                "nullable": True,
                                "type": "boolean",
                            },
                            "valueBooleanArray": {
                                "description": "value as boolean",
                                "example": [True, False],
                                "items": {"type": "boolean"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueDate": {
                                "description": "value as date (as string)",
                                "example": "TODO",
                                "nullable": True,
                                "type": "string",
                            },
                            "valueDateArray": {
                                "description": "value as date (as string)",
                                "example": "TODO",
                                "items": {"type": "string"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueGeoRange": {
                                "description": "Filter within a distance of a georange.",
                                "properties": {
                                    "distance": {
                                        "properties": {
                                            "max": {"format": "float64", "type": "number"}
                                        },
                                        "type": "object",
                                    },
                                    "geoCoordinates": {
                                        "properties": {
                                            "latitude": {
                                                "description": "The "
                                                "latitude "
                                                "of "
                                                "the "
                                                "point "
                                                "on "
                                                "earth "
                                                "in "
                                                "decimal "
                                                "form.",
                                                "format": "float",
                                                "nullable": True,
                                                "type": "number",
                                            },
                                            "longitude": {
                                                "description": "The "
                                                "longitude "
                                                "of "
                                                "the "
                                                "point "
                                                "on "
                                                "earth "
                                                "in "
                                                "decimal "
                                                "form.",
                                                "format": "float",
                                                "nullable": True,
                                                "type": "number",
                                            },
                                        },
                                        "type": "object",
                                    },
                                },
                                "type": "object",
                            },
                            "valueInt": {
                                "description": "value as integer",
                                "example": 2000,
                                "format": "int64",
                                "nullable": True,
                                "type": "integer",
                            },
                            "valueIntArray": {
                                "description": "value as integer",
                                "example": "[100, 200]",
                                "items": {"format": "int64", "type": "integer"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueNumber": {
                                "description": "value as number/float",
                                "example": 3.14,
                                "format": "float64",
                                "nullable": True,
                                "type": "number",
                            },
                            "valueNumberArray": {
                                "description": "value as number/float",
                                "example": [3.14],
                                "items": {"format": "float64", "type": "number"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueString": {
                                "description": "value "
                                "as "
                                "text "
                                "(deprecated "
                                "as "
                                "of "
                                "v1.19; "
                                "alias "
                                "for "
                                "valueText)",
                                "example": "my search term",
                                "nullable": True,
                                "type": "string",
                            },
                            "valueStringArray": {
                                "description": "value "
                                "as "
                                "text "
                                "(deprecated "
                                "as "
                                "of "
                                "v1.19; "
                                "alias "
                                "for "
                                "valueText)",
                                "example": ["my search term"],
                                "items": {"type": "string"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                            "valueText": {
                                "description": "value as text",
                                "example": "my search term",
                                "nullable": True,
                                "type": "string",
                            },
                            "valueTextArray": {
                                "description": "value as text",
                                "example": ["my search term"],
                                "items": {"type": "string"},
                                "nullable": True,
                                "type": "array",
                                "x-omitempty": True,
                            },
                        },
                        "type": "object",
                    },
                },
                "type": "object",
            },
            "id": {
                "description": "ID to uniquely identify this classification run.",
                "example": "ee722219-b8ec-4db1-8f8d-5150bb1a9e0c",
                "format": "uuid",
                "type": "string",
            },
            "meta": {
                "description": "Additional information to a specific classification.",
                "properties": {
                    "completed": {
                        "description": "Time when this classification finished.",
                        "example": "2017-07-21T17:32:28Z",
                        "format": "date-time",
                        "type": "string",
                    },
                    "count": {
                        "description": "Number of objects "
                        "which were taken "
                        "into consideration "
                        "for classification.",
                        "example": 147,
                        "type": "integer",
                    },
                    "countFailed": {
                        "description": "Number of "
                        "objects which "
                        "could not be "
                        "classified - "
                        "see error "
                        "message for "
                        "details.",
                        "example": 7,
                        "type": "integer",
                    },
                    "countSucceeded": {
                        "description": "Number of objects successfully classified.",
                        "example": 140,
                        "type": "integer",
                    },
                    "started": {
                        "description": "Time when this classification was started.",
                        "example": "2017-07-21T17:32:28Z",
                        "format": "date-time",
                        "type": "string",
                    },
                },
                "type": "object",
            },
            "settings": {
                "description": "Classification-type specific settings.",
                "properties": {},
                "type": "object",
            },
            "status": {
                "description": "Status of this classification.",
                "enum": ["running", "completed", "failed"],
                "example": "running",
                "type": "string",
            },
            "type": {
                "description": "Which algorithm to use for classifications.",
                "type": "string",
            },
        },
        "type": "object",
    },
}
