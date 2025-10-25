"""Request Body Schemas for API Tools

DO NOT EDIT THIS MODULE DIRECTLY.

THIS MODULE WAS AUTO-GENERATED AND CONTAINS OpenAPI REQUEST BODY SCHEMAS
FOR TOOLS WITH COMPLEX REQUEST BODIES. ANY CHANGES TO THIS MODULE WILL
BE OVERWRITTEN BY THE TRANSPILER.
"""

from typing import Any

REQUEST_BODY_SCHEMAS: dict[str, Any] = {
    "UPDATEACCESSGROUP_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "membersToAdd": {
                "description": "List of members to add to the access group.",
                "example": ["usr_1a2b3c4d5e6f7g8h9i0j", "usr_2b3c4d5e6f7g8h9i0j1k"],
                "items": {"type": "string"},
                "type": "array",
            },
            "membersToRemove": {
                "description": "List of members to remove from the access group.",
                "example": ["usr_1a2b3c4d5e6f7g8h9i0j", "usr_2b3c4d5e6f7g8h9i0j1k"],
                "items": {"type": "string"},
                "type": "array",
            },
            "name": {
                "description": "The name of the access group",
                "example": "My access group",
                "maxLength": 50,
                "pattern": "^[A-z0-9_ -]+$",
                "type": "string",
            },
            "projects": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "projectId": {
                            "description": "The ID of the project.",
                            "example": "prj_ndlgr43fadlPyCtREAqxxdyFK",
                            "maxLength": 256,
                            "type": "string",
                        },
                        "role": {
                            "description": "The "
                            "project "
                            "role "
                            "that "
                            "will be "
                            "added "
                            "to this "
                            "Access "
                            "Group. "
                            '\\"null\\" '
                            "will "
                            "remove "
                            "this "
                            "project "
                            "level "
                            "role.",
                            "enum": ["ADMIN", "PROJECT_VIEWER", "PROJECT_DEVELOPER", None],
                            "example": "ADMIN",
                            "nullable": True,
                            "type": "string",
                        },
                    },
                    "required": ["role", "projectId"],
                    "type": "object",
                },
                "type": "array",
            },
        },
        "type": "object",
    },
    "CREATEACCESSGROUP_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "membersToAdd": {
                "description": "List of members to add to the access group.",
                "example": ["usr_1a2b3c4d5e6f7g8h9i0j", "usr_2b3c4d5e6f7g8h9i0j1k"],
                "items": {"type": "string"},
                "type": "array",
            },
            "name": {
                "description": "The name of the access group",
                "example": "My access group",
                "maxLength": 50,
                "pattern": "^[A-z0-9_ -]+$",
                "type": "string",
            },
            "projects": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "projectId": {
                            "description": "The ID of the project.",
                            "example": "prj_ndlgr43fadlPyCtREAqxxdyFK",
                            "maxLength": 256,
                            "type": "string",
                        },
                        "role": {
                            "description": "The "
                            "project "
                            "role "
                            "that "
                            "will be "
                            "added "
                            "to this "
                            "Access "
                            "Group. "
                            '\\"null\\" '
                            "will "
                            "remove "
                            "this "
                            "project "
                            "level "
                            "role.",
                            "enum": ["ADMIN", "PROJECT_VIEWER", "PROJECT_DEVELOPER"],
                            "example": "ADMIN",
                            "nullable": True,
                            "type": "string",
                        },
                    },
                    "required": ["role", "projectId"],
                    "type": "object",
                },
                "type": "array",
            },
        },
        "required": ["name"],
        "type": "object",
    },
    "RECORDCACHEEVENTS_REQUEST_BODY_SCHEMA": {
        "items": {
            "additionalProperties": False,
            "properties": {
                "duration": {
                    "description": "The time taken to generate the "
                    "artifact. This should be sent "
                    "as a body parameter on `HIT` "
                    "events.",
                    "example": 400,
                    "type": "number",
                },
                "event": {
                    "description": "One of `HIT` or `MISS`. `HIT` "
                    "specifies that a cached artifact "
                    "for `hash` was found in the cache. "
                    "`MISS` specifies that a cached "
                    "artifact with `hash` was not "
                    "found.",
                    "enum": ["HIT", "MISS"],
                    "type": "string",
                },
                "hash": {
                    "description": "The artifact hash",
                    "example": "12HKQaOmR5t5Uy6vdcQsNIiZgHGB",
                    "type": "string",
                },
                "sessionId": {
                    "description": "A UUID (universally unique "
                    "identifer) for the session "
                    "that generated this event.",
                    "type": "string",
                },
                "source": {
                    "description": "One of `LOCAL` or `REMOTE`. "
                    "`LOCAL` specifies that the cache "
                    "event was from the user's "
                    "filesystem cache. `REMOTE` "
                    "specifies that the cache event is "
                    "from a remote cache.",
                    "enum": ["LOCAL", "REMOTE"],
                    "type": "string",
                },
            },
            "required": ["sessionId", "source", "hash", "event"],
            "type": "object",
        },
        "type": "array",
    },
    "UPDATEEXISTINGCHECK_REQUEST_BODY_SCHEMA": {
        "properties": {
            "conclusion": {
                "description": "The result of the check being run",
                "enum": ["canceled", "failed", "neutral", "succeeded", "skipped"],
            },
            "detailsUrl": {
                "description": "A URL a user may visit to see more information about the check",
                "example": "https://example.com/check/run/1234abc",
                "type": "string",
            },
            "externalId": {
                "description": "An identifier that can be used as an external reference",
                "example": "1234abc",
                "type": "string",
            },
            "name": {
                "description": "The name of the check being created",
                "example": "Performance Check",
                "maxLength": 100,
                "type": "string",
            },
            "output": {
                "description": "The results of the check Run",
                "properties": {
                    "metrics": {
                        "additionalProperties": False,
                        "description": "Metrics about the page",
                        "properties": {
                            "CLS": {
                                "properties": {
                                    "previousValue": {
                                        "description": "Previous "
                                        "Cumulative "
                                        "Layout "
                                        "Shift "
                                        "value "
                                        "to "
                                        "display "
                                        "a "
                                        "delta",
                                        "example": 2,
                                        "type": "number",
                                    },
                                    "source": {"enum": ["web-vitals"], "type": "string"},
                                    "value": {
                                        "description": "Cumulative Layout Shift value",
                                        "example": 4,
                                        "nullable": True,
                                        "type": "number",
                                    },
                                },
                                "required": ["value", "source"],
                                "type": "object",
                            },
                            "FCP": {
                                "properties": {
                                    "previousValue": {
                                        "description": "Previous "
                                        "First "
                                        "Contentful "
                                        "Paint "
                                        "value "
                                        "to "
                                        "display "
                                        "a "
                                        "delta",
                                        "example": 900,
                                        "type": "number",
                                    },
                                    "source": {"enum": ["web-vitals"], "type": "string"},
                                    "value": {
                                        "description": "First Contentful Paint value",
                                        "example": 1200,
                                        "nullable": True,
                                        "type": "number",
                                    },
                                },
                                "required": ["value", "source"],
                                "type": "object",
                            },
                            "LCP": {
                                "properties": {
                                    "previousValue": {
                                        "description": "Previous "
                                        "Largest "
                                        "Contentful "
                                        "Paint "
                                        "value "
                                        "to "
                                        "display "
                                        "a "
                                        "delta",
                                        "example": 1000,
                                        "type": "number",
                                    },
                                    "source": {"enum": ["web-vitals"], "type": "string"},
                                    "value": {
                                        "description": "Largest Contentful Paint value",
                                        "example": 1200,
                                        "nullable": True,
                                        "type": "number",
                                    },
                                },
                                "required": ["value", "source"],
                                "type": "object",
                            },
                            "TBT": {
                                "properties": {
                                    "previousValue": {
                                        "description": "Previous "
                                        "Total "
                                        "Blocking "
                                        "Time "
                                        "value "
                                        "to "
                                        "display "
                                        "a "
                                        "delta",
                                        "example": 3500,
                                        "type": "number",
                                    },
                                    "source": {"enum": ["web-vitals"]},
                                    "value": {
                                        "description": "Total Blocking Time value",
                                        "example": 3000,
                                        "nullable": True,
                                        "type": "number",
                                    },
                                },
                                "required": ["value", "source"],
                                "type": "object",
                            },
                            "virtualExperienceScore": {
                                "properties": {
                                    "previousValue": {
                                        "description": "A "
                                        "previous "
                                        "Virtual "
                                        "Experience "
                                        "Score "
                                        "value "
                                        "to "
                                        "display "
                                        "a "
                                        "delta, "
                                        "between "
                                        "0 "
                                        "and "
                                        "100",
                                        "example": 35,
                                        "maximum": 100,
                                        "minimum": 0,
                                        "type": "integer",
                                    },
                                    "source": {"enum": ["web-vitals"]},
                                    "value": {
                                        "description": "The "
                                        "calculated "
                                        "Virtual "
                                        "Experience "
                                        "Score "
                                        "value, "
                                        "between "
                                        "0 "
                                        "and "
                                        "100",
                                        "example": 30,
                                        "maximum": 100,
                                        "minimum": 0,
                                        "nullable": True,
                                        "type": "integer",
                                    },
                                },
                                "required": ["value", "source"],
                                "type": "object",
                            },
                        },
                        "required": ["FCP", "LCP", "CLS", "TBT"],
                        "type": "object",
                    }
                },
                "type": "object",
            },
            "path": {
                "description": "Path of the page that is being checked",
                "example": "/",
                "maxLength": 255,
                "type": "string",
            },
            "status": {
                "description": "The current status of the check",
                "enum": ["running", "completed"],
            },
        },
        "type": "object",
    },
    "UPDATEINTEGRATIONDEPLOYMENT_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "outcomes": {
                "items": {
                    "oneOf": [
                        {
                            "additionalProperties": False,
                            "properties": {
                                "kind": {"type": "string"},
                                "secrets": {
                                    "items": {
                                        "additionalProperties": False,
                                        "properties": {
                                            "name": {"type": "string"},
                                            "value": {"type": "string"},
                                        },
                                        "required": ["name", "value"],
                                        "type": "object",
                                    },
                                    "type": "array",
                                },
                            },
                            "required": ["kind", "secrets"],
                            "type": "object",
                        }
                    ]
                },
                "type": "array",
            },
            "status": {"enum": ["running", "succeeded", "failed"], "type": "string"},
            "statusText": {"type": "string"},
            "statusUrl": {"format": "uri", "pattern": "^https?://|^sso:", "type": "string"},
        },
        "type": "object",
    },
    "CREATEVERCELDEPLOYMENT_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "customEnvironmentSlugOrId": {
                "description": "Deploy to a custom "
                "environment, which will "
                "override the default "
                "environment",
                "type": "string",
            },
            "deploymentId": {
                "description": "An deployment id for an existing deployment to redeploy",
                "example": "dpl_2qn7PZrx89yxY34vEZPD31Y9XVj6",
                "type": "string",
            },
            "files": {
                "description": "A list of objects with the files to be deployed",
                "items": {
                    "oneOf": [
                        {
                            "additionalProperties": False,
                            "description": "Used in the case you "
                            "want to inline a file "
                            "inside the request",
                            "properties": {
                                "data": {
                                    "description": "The "
                                    "file "
                                    "content, "
                                    "it "
                                    "could "
                                    "be "
                                    "either "
                                    "a "
                                    "`base64` "
                                    "(useful "
                                    "for "
                                    "images, "
                                    "etc.) "
                                    "of "
                                    "the "
                                    "files "
                                    "or "
                                    "the "
                                    "plain "
                                    "content "
                                    "for "
                                    "source "
                                    "code",
                                    "type": "string",
                                },
                                "encoding": {
                                    "description": "The "
                                    "file "
                                    "content "
                                    "encoding, "
                                    "it "
                                    "could "
                                    "be "
                                    "either "
                                    "a "
                                    "base64 "
                                    "(useful "
                                    "for "
                                    "images, "
                                    "etc.) "
                                    "of "
                                    "the "
                                    "files "
                                    "or "
                                    "the "
                                    "plain "
                                    "text "
                                    "for "
                                    "source "
                                    "code.",
                                    "enum": ["base64", "utf-8"],
                                },
                                "file": {
                                    "description": "The file name including the whole path",
                                    "example": "folder/file.js",
                                    "type": "string",
                                },
                            },
                            "required": ["file", "data"],
                            "title": "InlinedFile",
                            "type": "object",
                        },
                        {
                            "additionalProperties": False,
                            "description": "Used in the case you "
                            "want to reference a "
                            "file that was already "
                            "uploaded",
                            "properties": {
                                "file": {
                                    "description": "The file path relative to the project root",
                                    "example": "folder/file.js",
                                    "type": "string",
                                },
                                "sha": {
                                    "description": "The "
                                    "file "
                                    "contents "
                                    "hashed "
                                    "with "
                                    "SHA1, "
                                    "used "
                                    "to "
                                    "check "
                                    "the "
                                    "integrity",
                                    "type": "string",
                                },
                                "size": {
                                    "description": "The file size in bytes",
                                    "type": "integer",
                                },
                            },
                            "required": ["file"],
                            "title": "UploadedFile",
                            "type": "object",
                        },
                    ]
                },
                "type": "array",
            },
            "gitMetadata": {
                "additionalProperties": False,
                "description": "Populates initial git metadata for different git providers.",
                "properties": {
                    "ci": {
                        "description": "True if process.env.CI was set when deploying",
                        "example": True,
                        "type": "boolean",
                    },
                    "ciGitProviderUsername": {
                        "description": "The "
                        "username "
                        "used "
                        "for "
                        "the "
                        "Git "
                        "Provider "
                        "(e.g. "
                        "GitHub) "
                        "if "
                        "their "
                        "CI "
                        "(e.g. "
                        "GitHub "
                        "Actions) "
                        "was "
                        "used, "
                        "if "
                        "available",
                        "example": "rauchg",
                        "type": "string",
                    },
                    "ciGitRepoVisibility": {
                        "description": "The "
                        "visibility "
                        "of "
                        "the "
                        "Git "
                        "repository "
                        "if "
                        "their "
                        "CI "
                        "(e.g. "
                        "GitHub "
                        "Actions) "
                        "was "
                        "used, "
                        "if "
                        "available",
                        "example": "private",
                        "type": "string",
                    },
                    "ciType": {
                        "description": "The type of CI system used",
                        "example": "github-actions",
                        "type": "string",
                    },
                    "commitAuthorEmail": {
                        "description": "The email of the author of the commit",
                        "example": "kyliau@example.com",
                        "type": "string",
                    },
                    "commitAuthorName": {
                        "description": "The name of the author of the commit",
                        "example": "kyliau",
                        "type": "string",
                    },
                    "commitMessage": {
                        "description": "The commit message",
                        "example": "add method to measure Interaction to Next Paint (INP) (#36490)",
                        "type": "string",
                    },
                    "commitRef": {
                        "description": "The branch on which the commit was made",
                        "example": "main",
                        "type": "string",
                    },
                    "commitSha": {
                        "description": "The hash of the commit",
                        "example": "dc36199b2234c6586ebe05ec94078a895c707e29",
                        "type": "string",
                    },
                    "dirty": {
                        "description": "Whether or "
                        "not there "
                        "have been "
                        "modifications "
                        "to the "
                        "working tree "
                        "since the "
                        "latest commit",
                        "example": True,
                        "type": "boolean",
                    },
                    "remoteUrl": {
                        "description": "The git repository's remote origin url",
                        "example": "https://github.com/vercel/next.js",
                        "type": "string",
                    },
                },
                "type": "object",
            },
            "gitSource": {
                "anyOf": [
                    {
                        "properties": {
                            "ref": {"example": "main", "type": "string"},
                            "repoId": {
                                "example": 123456789,
                                "oneOf": [{"type": "number"}, {"type": "string"}],
                            },
                            "sha": {
                                "example": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
                                "type": "string",
                            },
                            "type": {"enum": ["github"], "type": "string"},
                        },
                        "required": ["type", "ref", "repoId"],
                        "type": "object",
                    },
                    {
                        "properties": {
                            "org": {"example": "vercel", "type": "string"},
                            "ref": {"example": "main", "type": "string"},
                            "repo": {"example": "next.js", "type": "string"},
                            "sha": {
                                "example": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
                                "type": "string",
                            },
                            "type": {"enum": ["github"], "type": "string"},
                        },
                        "required": ["type", "ref", "org", "repo"],
                        "type": "object",
                    },
                    {
                        "properties": {
                            "ref": {"example": "main", "type": "string"},
                            "repoId": {
                                "example": 123456789,
                                "oneOf": [{"type": "number"}, {"type": "string"}],
                            },
                            "sha": {
                                "example": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
                                "type": "string",
                            },
                            "type": {"enum": ["github-limited"], "type": "string"},
                        },
                        "required": ["type", "ref", "repoId"],
                        "type": "object",
                    },
                    {
                        "properties": {
                            "org": {"example": "vercel", "type": "string"},
                            "ref": {"example": "main", "type": "string"},
                            "repo": {"example": "next.js", "type": "string"},
                            "sha": {
                                "example": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
                                "type": "string",
                            },
                            "type": {"enum": ["github-limited"], "type": "string"},
                        },
                        "required": ["type", "ref", "org", "repo"],
                        "type": "object",
                    },
                    {
                        "properties": {
                            "projectId": {
                                "example": 987654321,
                                "oneOf": [{"type": "number"}, {"type": "string"}],
                            },
                            "ref": {"example": "main", "type": "string"},
                            "sha": {
                                "example": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
                                "type": "string",
                            },
                            "type": {"enum": ["gitlab"], "type": "string"},
                        },
                        "required": ["type", "ref", "projectId"],
                        "type": "object",
                    },
                    {
                        "properties": {
                            "ref": {"example": "main", "type": "string"},
                            "repoUuid": {
                                "example": "123e4567-e89b-12d3-a456-426614174000",
                                "type": "string",
                            },
                            "sha": {
                                "example": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
                                "type": "string",
                            },
                            "type": {"enum": ["bitbucket"], "type": "string"},
                            "workspaceUuid": {
                                "example": "987e6543-e21b-12d3-a456-426614174000",
                                "type": "string",
                            },
                        },
                        "required": ["type", "ref", "repoUuid"],
                        "type": "object",
                    },
                    {
                        "properties": {
                            "owner": {"example": "bitbucket_user", "type": "string"},
                            "ref": {"example": "main", "type": "string"},
                            "sha": {
                                "example": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
                                "type": "string",
                            },
                            "slug": {"example": "my-awesome-project", "type": "string"},
                            "type": {"enum": ["bitbucket"], "type": "string"},
                        },
                        "required": ["type", "ref", "owner", "slug"],
                        "type": "object",
                    },
                ],
                "description": "Defines the Git Repository source to be "
                "deployed. This property can not be used "
                "in combination with `files`.",
            },
            "meta": {
                "additionalProperties": {"maxLength": 65536, "type": "string"},
                "description": "An object containing the deployment's "
                "metadata. Multiple key-value pairs can be "
                "attached to a deployment",
                "example": {"foo": "bar"},
                "maxProperties": 100,
                "type": "object",
            },
            "monorepoManager": {
                "description": "The monorepo manager that is being "
                "used for this deployment. When "
                "`null` is used no monorepo manager "
                "is selected",
                "nullable": True,
                "type": "string",
            },
            "name": {
                "description": "A string with the project name used in the deployment URL",
                "example": "my-instant-deployment",
                "type": "string",
            },
            "project": {
                "description": "The target project identifier in which the "
                "deployment will be created. When defined, "
                "this parameter overrides name",
                "example": "my-deployment-project",
                "type": "string",
            },
            "projectSettings": {
                "additionalProperties": False,
                "description": "Project settings that will be "
                "applied to the deployment. It is "
                "required for the first deployment "
                "of a project and will be saved for "
                "any following deployments",
                "properties": {
                    "buildCommand": {
                        "description": "The "
                        "build "
                        "command "
                        "for "
                        "this "
                        "project. "
                        "When "
                        "`null` "
                        "is "
                        "used "
                        "this "
                        "value "
                        "will "
                        "be "
                        "automatically "
                        "detected",
                        "example": "next build",
                        "maxLength": 256,
                        "nullable": True,
                        "type": "string",
                    },
                    "commandForIgnoringBuildStep": {
                        "maxLength": 256,
                        "nullable": True,
                        "type": "string",
                    },
                    "devCommand": {
                        "description": "The "
                        "dev "
                        "command "
                        "for "
                        "this "
                        "project. "
                        "When "
                        "`null` "
                        "is "
                        "used "
                        "this "
                        "value "
                        "will "
                        "be "
                        "automatically "
                        "detected",
                        "maxLength": 256,
                        "nullable": True,
                        "type": "string",
                    },
                    "framework": {
                        "description": "The "
                        "framework "
                        "that "
                        "is "
                        "being "
                        "used "
                        "for "
                        "this "
                        "project. "
                        "When "
                        "`null` "
                        "is "
                        "used "
                        "no "
                        "framework "
                        "is "
                        "selected",
                        "enum": [
                            None,
                            "blitzjs",
                            "nextjs",
                            "gatsby",
                            "remix",
                            "react-router",
                            "astro",
                            "hexo",
                            "eleventy",
                            "docusaurus-2",
                            "docusaurus",
                            "preact",
                            "solidstart-1",
                            "solidstart",
                            "dojo",
                            "ember",
                            "vue",
                            "scully",
                            "ionic-angular",
                            "angular",
                            "polymer",
                            "svelte",
                            "sveltekit",
                            "sveltekit-1",
                            "ionic-react",
                            "create-react-app",
                            "gridsome",
                            "umijs",
                            "sapper",
                            "saber",
                            "stencil",
                            "nuxtjs",
                            "redwoodjs",
                            "hugo",
                            "jekyll",
                            "brunch",
                            "middleman",
                            "zola",
                            "hydrogen",
                            "vite",
                            "vitepress",
                            "vuepress",
                            "parcel",
                            "fastapi",
                            "flask",
                            "fasthtml",
                            "sanity-v3",
                            "sanity",
                            "storybook",
                            "nitro",
                            "hono",
                            "express",
                            "h3",
                            "nestjs",
                            "xmcp",
                        ],
                        "nullable": True,
                        "type": "string",
                    },
                    "installCommand": {
                        "description": "The "
                        "install "
                        "command "
                        "for "
                        "this "
                        "project. "
                        "When "
                        "`null` "
                        "is "
                        "used "
                        "this "
                        "value "
                        "will "
                        "be "
                        "automatically "
                        "detected",
                        "example": "pnpm install",
                        "maxLength": 256,
                        "nullable": True,
                        "type": "string",
                    },
                    "nodeVersion": {
                        "description": "Override "
                        "the "
                        "Node.js "
                        "version "
                        "that "
                        "should "
                        "be "
                        "used "
                        "for "
                        "this "
                        "deployment",
                        "enum": ["22.x", "20.x", "18.x", "16.x", "14.x", "12.x", "10.x", "8.10.x"],
                        "type": "string",
                    },
                    "outputDirectory": {
                        "description": "The "
                        "output "
                        "directory "
                        "of "
                        "the "
                        "project. "
                        "When "
                        "`null` "
                        "is "
                        "used "
                        "this "
                        "value "
                        "will "
                        "be "
                        "automatically "
                        "detected",
                        "maxLength": 256,
                        "nullable": True,
                        "type": "string",
                    },
                    "rootDirectory": {
                        "description": "The "
                        "name "
                        "of "
                        "a "
                        "directory "
                        "or "
                        "relative "
                        "path "
                        "to "
                        "the "
                        "source "
                        "code "
                        "of "
                        "your "
                        "project. "
                        "When "
                        "`null` "
                        "is "
                        "used "
                        "it "
                        "will "
                        "default "
                        "to "
                        "the "
                        "project "
                        "root",
                        "maxLength": 256,
                        "nullable": True,
                        "type": "string",
                    },
                    "serverlessFunctionRegion": {
                        "description": "The region to deploy Serverless Functions in this project",
                        "maxLength": 4,
                        "nullable": True,
                        "type": "string",
                    },
                    "skipGitConnectDuringLink": {
                        "deprecated": True,
                        "description": "Opts-out "
                        "of "
                        "the "
                        "message "
                        "prompting "
                        "a "
                        "CLI "
                        "user "
                        "to "
                        "connect "
                        "a "
                        "Git "
                        "repository "
                        "in "
                        "`vercel "
                        "link`.",
                        "type": "boolean",
                    },
                    "sourceFilesOutsideRootDirectory": {
                        "description": "Indicates "
                        "if "
                        "there "
                        "are "
                        "source "
                        "files "
                        "outside "
                        "of "
                        "the "
                        "root "
                        "directory, "
                        "typically "
                        "used "
                        "for "
                        "monorepos",
                        "type": "boolean",
                    },
                },
                "type": "object",
            },
            "target": {
                "description": "Either not defined, `staging`, "
                "`production`, or a custom environment "
                "identifier. If `staging`, a staging alias "
                "in the format `<project>-<team>.vercel.app` "
                "will be assigned. If `production`, any "
                "aliases defined in `alias` will be "
                "assigned. If omitted, the target will be "
                "`preview`.",
                "example": "production",
                "type": "string",
            },
            "withLatestCommit": {
                "description": "When `true` and `deploymentId` is "
                "passed in, the sha from the "
                "previous deployment's `gitSource` "
                "is removed forcing the latest "
                "commit to be used.",
                "type": "boolean",
            },
        },
        "required": ["name"],
        "type": "object",
    },
    "PURCHASEDOMAIN_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "address1": {
                "description": "The street address of the domain registrant",
                "example": "340 S Lemon Ave Suite 4133",
                "type": "string",
            },
            "city": {
                "description": "The city of the domain registrant",
                "example": "San Francisco",
                "type": "string",
            },
            "country": {
                "description": "The country of the domain registrant",
                "example": "US",
                "type": "string",
            },
            "email": {
                "description": "The email of the domain registrant",
                "example": "jane.doe@someplace.com",
                "type": "string",
            },
            "expectedPrice": {
                "description": "The price you expect to be charged for the purchase.",
                "example": 10,
                "type": "number",
            },
            "firstName": {
                "description": "The first name of the domain registrant",
                "example": "Jane",
                "type": "string",
            },
            "lastName": {
                "description": "The last name of the domain registrant",
                "example": "Doe",
                "type": "string",
            },
            "name": {
                "description": "The domain name to purchase.",
                "example": "example.com",
                "type": "string",
            },
            "orgName": {
                "description": "The company name of the domain registrant",
                "example": "Acme Inc.",
                "type": "string",
            },
            "phone": {
                "description": "The phone number of the domain registrant",
                "example": "+1.4158551452",
                "type": "string",
            },
            "postalCode": {
                "description": "The postal code of the domain registrant",
                "example": "91789",
                "type": "string",
            },
            "renew": {
                "description": "Indicates whether the domain should be automatically renewed.",
                "example": True,
                "type": "boolean",
            },
            "state": {
                "description": "The state of the domain registrant",
                "example": "CA",
                "type": "string",
            },
        },
        "required": [
            "name",
            "country",
            "firstName",
            "lastName",
            "address1",
            "city",
            "state",
            "postalCode",
            "phone",
            "email",
        ],
        "type": "object",
    },
    "CREATEDNSRECORD_REQUEST_BODY_SCHEMA": {
        "anyOf": [
            {
                "additionalProperties": False,
                "properties": {
                    "comment": {
                        "description": "A comment to add context on what this DNS record is for",
                        "example": "used to verify ownership of domain",
                        "maxLength": 500,
                        "type": "string",
                    },
                    "name": {
                        "description": "A subdomain name or an empty string for the root domain.",
                        "example": "subdomain",
                        "type": "string",
                    },
                    "ttl": {
                        "description": "The TTL value. Must be a number "
                        "between 60 and 2147483647. Default "
                        "value is 60.",
                        "example": 60,
                        "maximum": 2147483647,
                        "minimum": 60,
                        "type": "number",
                    },
                    "type": {
                        "description": "Must be of type `A`.",
                        "enum": ["A"],
                        "type": "string",
                    },
                    "value": {
                        "description": "The record value must be a valid IPv4 address.",
                        "example": "192.0.2.42",
                        "format": "ipv4",
                        "type": "string",
                    },
                },
                "required": ["type", "value", "name"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "properties": {
                    "comment": {
                        "description": "A comment to add context on what this DNS record is for",
                        "example": "used to verify ownership of domain",
                        "maxLength": 500,
                        "type": "string",
                    },
                    "name": {
                        "description": "A subdomain name or an empty string for the root domain.",
                        "example": "subdomain",
                        "type": "string",
                    },
                    "ttl": {
                        "description": "The TTL value. Must be a number "
                        "between 60 and 2147483647. Default "
                        "value is 60.",
                        "example": 60,
                        "maximum": 2147483647,
                        "minimum": 60,
                        "type": "number",
                    },
                    "type": {
                        "description": "Must be of type `AAAA`.",
                        "enum": ["AAAA"],
                        "type": "string",
                    },
                    "value": {
                        "description": "An AAAA record pointing to an IPv6 address.",
                        "example": "2001:DB8::42",
                        "format": "ipv6",
                        "type": "string",
                    },
                },
                "required": ["type", "value", "name"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "properties": {
                    "comment": {
                        "description": "A comment to add context on what this DNS record is for",
                        "example": "used to verify ownership of domain",
                        "maxLength": 500,
                        "type": "string",
                    },
                    "name": {
                        "description": "A subdomain name or an empty string for the root domain.",
                        "example": "subdomain",
                        "type": "string",
                    },
                    "ttl": {
                        "description": "The TTL value. Must be a number "
                        "between 60 and 2147483647. Default "
                        "value is 60.",
                        "example": 60,
                        "maximum": 2147483647,
                        "minimum": 60,
                        "type": "number",
                    },
                    "type": {
                        "description": "Must be of type `ALIAS`.",
                        "enum": ["ALIAS"],
                        "type": "string",
                    },
                    "value": {
                        "description": "An ALIAS virtual record pointing "
                        "to a hostname resolved to an A "
                        "record on server side.",
                        "example": "cname.vercel-dns.com",
                        "type": "string",
                    },
                },
                "required": ["type", "value", "name"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "properties": {
                    "comment": {
                        "description": "A comment to add context on what this DNS record is for",
                        "example": "used to verify ownership of domain",
                        "maxLength": 500,
                        "type": "string",
                    },
                    "name": {
                        "description": "A subdomain name or an empty string for the root domain.",
                        "example": "subdomain",
                        "type": "string",
                    },
                    "ttl": {
                        "description": "The TTL value. Must be a number "
                        "between 60 and 2147483647. Default "
                        "value is 60.",
                        "example": 60,
                        "maximum": 2147483647,
                        "minimum": 60,
                        "type": "number",
                    },
                    "type": {
                        "description": "Must be of type `CAA`.",
                        "enum": ["CAA"],
                        "type": "string",
                    },
                    "value": {
                        "description": "A CAA record to specify which "
                        "Certificate Authorities (CAs) are "
                        "allowed to issue certificates for "
                        "the domain.",
                        "example": '0 issue \\"letsencrypt.org\\"',
                        "type": "string",
                    },
                },
                "required": ["type", "value", "name"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "properties": {
                    "comment": {
                        "description": "A comment to add context on what this DNS record is for",
                        "example": "used to verify ownership of domain",
                        "maxLength": 500,
                        "type": "string",
                    },
                    "name": {
                        "description": "A subdomain name or an empty string for the root domain.",
                        "example": "subdomain",
                        "type": "string",
                    },
                    "ttl": {
                        "description": "The TTL value. Must be a number "
                        "between 60 and 2147483647. Default "
                        "value is 60.",
                        "example": 60,
                        "maximum": 2147483647,
                        "minimum": 60,
                        "type": "number",
                    },
                    "type": {
                        "description": "Must be of type `CNAME`.",
                        "enum": ["CNAME"],
                        "type": "string",
                    },
                    "value": {
                        "description": "A CNAME record mapping to another domain name.",
                        "example": "cname.vercel-dns.com",
                        "type": "string",
                    },
                },
                "required": ["type", "name"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "properties": {
                    "comment": {
                        "description": "A comment to add context on what this DNS record is for",
                        "example": "used to verify ownership of domain",
                        "maxLength": 500,
                        "type": "string",
                    },
                    "mxPriority": {"example": 10, "maximum": 65535, "minimum": 0, "type": "number"},
                    "name": {
                        "description": "A subdomain name or an empty string for the root domain.",
                        "example": "subdomain",
                        "type": "string",
                    },
                    "ttl": {
                        "description": "The TTL value. Must be a number "
                        "between 60 and 2147483647. Default "
                        "value is 60.",
                        "example": 60,
                        "maximum": 2147483647,
                        "minimum": 60,
                        "type": "number",
                    },
                    "type": {
                        "description": "Must be of type `MX`.",
                        "enum": ["MX"],
                        "type": "string",
                    },
                    "value": {
                        "description": "An MX record specifying the mail "
                        "server responsible for accepting "
                        "messages on behalf of the domain "
                        "name.",
                        "example": "10 mail.example.com.",
                        "type": "string",
                    },
                },
                "required": ["type", "value", "name", "mxPriority"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "properties": {
                    "comment": {
                        "description": "A comment to add context on what this DNS record is for",
                        "example": "used to verify ownership of domain",
                        "maxLength": 500,
                        "type": "string",
                    },
                    "srv": {
                        "additionalProperties": False,
                        "properties": {
                            "port": {
                                "anyOf": [
                                    {
                                        "example": 5000,
                                        "maximum": 65535,
                                        "minimum": 0,
                                        "type": "number",
                                    }
                                ],
                                "nullable": True,
                            },
                            "priority": {
                                "anyOf": [
                                    {
                                        "example": 10,
                                        "maximum": 65535,
                                        "minimum": 0,
                                        "type": "number",
                                    }
                                ],
                                "nullable": True,
                            },
                            "target": {"example": "host.example.com", "type": "string"},
                            "weight": {
                                "anyOf": [
                                    {
                                        "example": 10,
                                        "maximum": 65535,
                                        "minimum": 0,
                                        "type": "number",
                                    }
                                ],
                                "nullable": True,
                            },
                        },
                        "required": ["weight", "port", "priority", "target"],
                        "type": "object",
                    },
                    "ttl": {
                        "description": "The TTL value. Must be a number "
                        "between 60 and 2147483647. Default "
                        "value is 60.",
                        "example": 60,
                        "maximum": 2147483647,
                        "minimum": 60,
                        "type": "number",
                    },
                    "type": {
                        "description": "Must be of type `SRV`.",
                        "enum": ["SRV"],
                        "type": "string",
                    },
                },
                "required": ["type", "name", "srv"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "properties": {
                    "comment": {
                        "description": "A comment to add context on what this DNS record is for",
                        "example": "used to verify ownership of domain",
                        "maxLength": 500,
                        "type": "string",
                    },
                    "ttl": {
                        "description": "The TTL value. Must be a number "
                        "between 60 and 2147483647. Default "
                        "value is 60.",
                        "example": 60,
                        "maximum": 2147483647,
                        "minimum": 60,
                        "type": "number",
                    },
                    "type": {
                        "description": "Must be of type `TXT`.",
                        "enum": ["TXT"],
                        "type": "string",
                    },
                    "value": {
                        "description": "A TXT record containing arbitrary text.",
                        "example": "hello",
                        "type": "string",
                    },
                },
                "required": ["type", "value", "name"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "properties": {
                    "comment": {
                        "description": "A comment to add context on what this DNS record is for",
                        "example": "used to verify ownership of domain",
                        "maxLength": 500,
                        "type": "string",
                    },
                    "name": {
                        "description": "A subdomain name.",
                        "example": "subdomain",
                        "type": "string",
                    },
                    "ttl": {
                        "description": "The TTL value. Must be a number "
                        "between 60 and 2147483647. Default "
                        "value is 60.",
                        "example": 60,
                        "maximum": 2147483647,
                        "minimum": 60,
                        "type": "number",
                    },
                    "type": {
                        "description": "Must be of type `NS`.",
                        "enum": ["NS"],
                        "type": "string",
                    },
                    "value": {
                        "description": "An NS domain value.",
                        "example": "ns1.example.com",
                        "type": "string",
                    },
                },
                "required": ["type", "name"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "properties": {
                    "comment": {
                        "description": "A comment to add context on what this DNS record is for",
                        "example": "used to verify ownership of domain",
                        "maxLength": 500,
                        "type": "string",
                    },
                    "https": {
                        "additionalProperties": False,
                        "properties": {
                            "params": {"example": "alpn=h2,h3", "type": "string"},
                            "priority": {
                                "anyOf": [
                                    {
                                        "example": 10,
                                        "maximum": 65535,
                                        "minimum": 0,
                                        "type": "number",
                                    }
                                ],
                                "nullable": True,
                            },
                            "target": {"example": "host.example.com", "type": "string"},
                        },
                        "required": ["priority", "target"],
                        "type": "object",
                    },
                    "ttl": {
                        "description": "The TTL value. Must be a number "
                        "between 60 and 2147483647. Default "
                        "value is 60.",
                        "example": 60,
                        "maximum": 2147483647,
                        "minimum": 60,
                        "type": "number",
                    },
                    "type": {
                        "description": "Must be of type `HTTPS`.",
                        "enum": ["HTTPS"],
                        "type": "string",
                    },
                },
                "required": ["type", "name", "https"],
                "type": "object",
            },
        ],
        "properties": {
            "type": {
                "description": "The type of record, it could be one of the valid DNS records.",
                "enum": ["A", "AAAA", "ALIAS", "CAA", "CNAME", "HTTPS", "MX", "SRV", "TXT", "NS"],
                "type": "string",
            }
        },
        "required": ["type"],
    },
    "UPDATEDNSRECORD_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "comment": {
                "description": "A comment to add context on what this DNS record is for",
                "example": "used to verify ownership of domain",
                "maxLength": 500,
                "type": "string",
            },
            "https": {
                "additionalProperties": False,
                "nullable": True,
                "properties": {
                    "params": {"description": "", "nullable": True, "type": "string"},
                    "priority": {"description": "", "nullable": True, "type": "integer"},
                    "target": {
                        "description": "",
                        "example": "example2.com.",
                        "maxLength": 255,
                        "nullable": True,
                        "type": "string",
                    },
                },
                "required": ["priority", "target"],
                "type": "object",
            },
            "mxPriority": {
                "description": "The MX priority value of the DNS record",
                "nullable": True,
                "type": "integer",
            },
            "name": {
                "description": "The name of the DNS record",
                "example": "example-1",
                "nullable": True,
                "type": "string",
            },
            "srv": {
                "additionalProperties": False,
                "nullable": True,
                "properties": {
                    "port": {"description": "", "nullable": True, "type": "integer"},
                    "priority": {"description": "", "nullable": True, "type": "integer"},
                    "target": {
                        "description": "",
                        "example": "example2.com.",
                        "maxLength": 255,
                        "nullable": True,
                        "type": "string",
                    },
                    "weight": {"description": "", "nullable": True, "type": "integer"},
                },
                "required": ["target", "weight", "port", "priority"],
                "type": "object",
            },
            "ttl": {
                "description": "The Time to live (TTL) value of the DNS record",
                "example": "60",
                "maximum": 2147483647,
                "minimum": 60,
                "nullable": True,
                "type": "integer",
            },
            "type": {
                "description": "The type of the DNS record",
                "enum": ["A", "AAAA", "ALIAS", "CAA", "CNAME", "HTTPS", "MX", "SRV", "TXT", "NS"],
                "example": "A",
                "maxLength": 255,
                "nullable": True,
                "type": "string",
            },
            "value": {
                "description": "The value of the DNS record",
                "example": "google.com",
                "nullable": True,
                "type": "string",
            },
        },
        "type": "object",
    },
    "PURCHASEDOMAINVERCEL_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "autoRenew": {
                "description": "Whether the domain should be "
                "auto-renewed before it expires. This can "
                "be configured later through the Vercel "
                "Dashboard or the [Update auto-renew for "
                "a "
                "domain](https://vercel.com/docs/rest-api/reference/endpoints/domains-registrar/update-auto-renew-for-a-domain) "
                "endpoint.",
                "type": "boolean",
            },
            "contactInformation": {
                "additionalProperties": False,
                "description": "The contact information for the "
                "domain. Some TLDs require "
                "additional contact information. "
                "Use the [Get contact info "
                "schema](https://vercel.com/docs/rest-api/reference/endpoints/domains-registrar/get-contact-info-schema) "
                "endpoint to retrieve the "
                "required fields.",
                "properties": {
                    "additional": {"properties": {}, "type": "object"},
                    "address1": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "address2": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "city": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "companyName": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "country": {
                        "description": "A valid ISO 3166-1 alpha-2 country code",
                        "minLength": 1,
                        "pattern": "^[A-Z]{2}$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "email": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "fax": {
                        "description": "A valid E.164 phone number",
                        "minLength": 1,
                        "pattern": "^(?=(?:\\D*\\d){7,15}$)\\+[1-9]\\d{0,2}\\.?\\d+$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "firstName": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "lastName": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "phone": {
                        "description": "A valid E.164 phone number",
                        "minLength": 1,
                        "pattern": "^(?=(?:\\D*\\d){7,15}$)\\+[1-9]\\d{0,2}\\.?\\d+$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "state": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "zip": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                },
                "required": [
                    "firstName",
                    "lastName",
                    "email",
                    "phone",
                    "address1",
                    "city",
                    "state",
                    "zip",
                    "country",
                ],
                "type": "object",
            },
            "expectedPrice": {
                "description": "The expected price for the domain. "
                "Use the [Get price data for a "
                "domain](https://vercel.com/docs/rest-api/reference/endpoints/domains-registrar/get-price-data-for-a-domain) "
                "endpoint to retrieve the price data "
                "for a domain.",
                "minimum": 0.01,
                "type": "number",
            },
            "years": {
                "description": "The number of years to purchase the domain for.",
                "type": "number",
            },
        },
        "required": ["autoRenew", "years", "expectedPrice", "contactInformation"],
        "type": "object",
    },
    "PURCHASEMULTIPLEDOMAINS_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "contactInformation": {
                "additionalProperties": False,
                "description": "The contact information for the "
                "domain. Some TLDs require "
                "additional contact information. "
                "Use the [Get contact info "
                "schema](https://vercel.com/docs/rest-api/reference/endpoints/domains-registrar/get-contact-info-schema) "
                "endpoint to retrieve the "
                "required fields.",
                "properties": {
                    "additional": {"properties": {}, "type": "object"},
                    "address1": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "address2": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "city": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "companyName": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "country": {
                        "description": "A valid ISO 3166-1 alpha-2 country code",
                        "minLength": 1,
                        "pattern": "^[A-Z]{2}$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "email": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "fax": {
                        "description": "A valid E.164 phone number",
                        "minLength": 1,
                        "pattern": "^(?=(?:\\D*\\d){7,15}$)\\+[1-9]\\d{0,2}\\.?\\d+$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "firstName": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "lastName": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "phone": {
                        "description": "A valid E.164 phone number",
                        "minLength": 1,
                        "pattern": "^(?=(?:\\D*\\d){7,15}$)\\+[1-9]\\d{0,2}\\.?\\d+$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "state": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "zip": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                },
                "required": [
                    "firstName",
                    "lastName",
                    "email",
                    "phone",
                    "address1",
                    "city",
                    "state",
                    "zip",
                    "country",
                ],
                "type": "object",
            },
            "domains": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "autoRenew": {
                            "description": "Whether "
                            "the "
                            "domain "
                            "should "
                            "be "
                            "auto-renewed "
                            "before "
                            "it "
                            "expires. "
                            "This "
                            "can "
                            "be "
                            "configured "
                            "later "
                            "through "
                            "the "
                            "Vercel "
                            "Dashboard "
                            "or "
                            "the "
                            "[Update "
                            "auto-renew "
                            "for "
                            "a "
                            "domain](https://vercel.com/docs/rest-api/reference/endpoints/domains-registrar/update-auto-renew-for-a-domain) "
                            "endpoint.",
                            "type": "boolean",
                        },
                        "domainName": {"type": "string"},
                        "expectedPrice": {
                            "description": "The "
                            "expected "
                            "price "
                            "for "
                            "the "
                            "domain. "
                            "Use "
                            "the "
                            "[Get "
                            "price "
                            "data "
                            "for "
                            "a "
                            "domain](https://vercel.com/docs/rest-api/reference/endpoints/domains-registrar/get-price-data-for-a-domain) "
                            "endpoint "
                            "to "
                            "retrieve "
                            "the "
                            "price "
                            "data "
                            "for "
                            "a "
                            "domain.",
                            "minimum": 0.01,
                            "type": "number",
                        },
                        "years": {
                            "description": "The number of years to purchase the domain for.",
                            "type": "number",
                        },
                    },
                    "required": ["domainName", "autoRenew", "years", "expectedPrice"],
                    "type": "object",
                },
                "minItems": 1,
                "type": "array",
            },
        },
        "required": ["domains", "contactInformation"],
        "type": "object",
    },
    "TRANSFERDOMAINTOVERCEL_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "authCode": {"type": "string"},
            "autoRenew": {
                "description": "Whether the domain should be "
                "auto-renewed before it expires. This can "
                "be configured later through the Vercel "
                "Dashboard or the [Update auto-renew for "
                "a "
                "domain](https://vercel.com/docs/rest-api/reference/endpoints/domains-registrar/update-auto-renew-for-a-domain) "
                "endpoint.",
                "type": "boolean",
            },
            "contactInformation": {
                "additionalProperties": False,
                "properties": {
                    "address1": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "address2": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "city": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "companyName": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "country": {
                        "description": "A valid ISO 3166-1 alpha-2 country code",
                        "minLength": 1,
                        "pattern": "^[A-Z]{2}$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "email": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "fax": {
                        "description": "A valid E.164 phone number",
                        "minLength": 1,
                        "pattern": "^(?=(?:\\D*\\d){7,15}$)\\+[1-9]\\d{0,2}\\.?\\d+$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "firstName": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "lastName": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "phone": {
                        "description": "A valid E.164 phone number",
                        "minLength": 1,
                        "pattern": "^(?=(?:\\D*\\d){7,15}$)\\+[1-9]\\d{0,2}\\.?\\d+$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "state": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "zip": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                },
                "required": [
                    "firstName",
                    "lastName",
                    "email",
                    "phone",
                    "address1",
                    "city",
                    "state",
                    "zip",
                    "country",
                ],
                "type": "object",
            },
            "expectedPrice": {
                "description": "The expected price for the domain. "
                "Use the [Get price data for a "
                "domain](https://vercel.com/docs/rest-api/reference/endpoints/domains-registrar/get-price-data-for-a-domain) "
                "endpoint to retrieve the price data "
                "for a domain.",
                "minimum": 0.01,
                "type": "number",
            },
            "years": {
                "description": "The number of years to renew the domain for "
                "once it is transferred in. This must be a "
                "valid number of transfer years for the TLD.",
                "type": "number",
            },
        },
        "required": ["authCode", "autoRenew", "years", "expectedPrice", "contactInformation"],
        "type": "object",
    },
    "RENEWDOMAIN_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "contactInformation": {
                "additionalProperties": False,
                "properties": {
                    "address1": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "address2": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "city": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "companyName": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "country": {
                        "description": "A valid ISO 3166-1 alpha-2 country code",
                        "minLength": 1,
                        "pattern": "^[A-Z]{2}$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "email": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "fax": {
                        "description": "A valid E.164 phone number",
                        "minLength": 1,
                        "pattern": "^(?=(?:\\D*\\d){7,15}$)\\+[1-9]\\d{0,2}\\.?\\d+$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "firstName": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "lastName": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "phone": {
                        "description": "A valid E.164 phone number",
                        "minLength": 1,
                        "pattern": "^(?=(?:\\D*\\d){7,15}$)\\+[1-9]\\d{0,2}\\.?\\d+$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "state": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                    "zip": {
                        "description": "a non empty string",
                        "minLength": 1,
                        "pattern": "^\\S[\\s\\S]*\\S$|^\\S$|^$",
                        "title": "nonEmptyString",
                        "type": "string",
                    },
                },
                "required": [
                    "firstName",
                    "lastName",
                    "email",
                    "phone",
                    "address1",
                    "city",
                    "state",
                    "zip",
                    "country",
                ],
                "type": "object",
            },
            "expectedPrice": {
                "description": "The expected price for the domain. "
                "Use the [Get price data for a "
                "domain](https://vercel.com/docs/rest-api/reference/endpoints/domains-registrar/get-price-data-for-a-domain) "
                "endpoint to retrieve the price data "
                "for a domain.",
                "minimum": 0.01,
                "type": "number",
            },
            "years": {
                "description": "The number of years to renew the domain for.",
                "type": "number",
            },
        },
        "required": ["years", "expectedPrice"],
        "type": "object",
    },
    "ADDNEWDOMAINVERCEL_REQUEST_BODY_SCHEMA": {
        "oneOf": [
            {
                "additionalProperties": False,
                "description": "add",
                "properties": {
                    "cdnEnabled": {
                        "description": "Whether the domain has the "
                        "Vercel Edge Network enabled "
                        "or not.",
                        "example": True,
                        "type": "boolean",
                    },
                    "method": {
                        "description": "The domain operation to perform.",
                        "example": "add",
                        "type": "string",
                    },
                    "name": {
                        "description": "The domain name you want to add.",
                        "example": "example.com",
                        "type": "string",
                    },
                    "zone": {"type": "boolean"},
                },
                "required": ["name"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "description": "move-in",
                "properties": {
                    "method": {
                        "description": "The domain operation to perform.",
                        "example": "move-in",
                        "type": "string",
                    },
                    "name": {
                        "description": "The domain name you want to add.",
                        "example": "example.com",
                        "type": "string",
                    },
                    "token": {
                        "description": "The move-in token from Move Requested email.",
                        "example": "fdhfr820ad#@FAdlj$$",
                        "type": "string",
                    },
                },
                "required": ["method", "name"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "deprecated": True,
                "description": "transfer-in",
                "properties": {
                    "authCode": {
                        "description": "The authorization code assigned to the domain.",
                        "example": "fdhfr820ad#@FAdlj$$",
                        "type": "string",
                    },
                    "expectedPrice": {
                        "description": "The price you expect to "
                        "be charged for the "
                        "required 1 year renewal.",
                        "example": 8,
                        "type": "number",
                    },
                    "method": {
                        "description": "The domain operation to perform.",
                        "example": "transfer-in",
                        "type": "string",
                    },
                    "name": {
                        "description": "The domain name you want to add.",
                        "example": "example.com",
                        "type": "string",
                    },
                },
                "required": ["method", "name"],
                "type": "object",
            },
        ],
        "properties": {
            "method": {
                "description": "The domain operation to perform. It can be "
                "either `add` or `move-in`.",
                "example": "add",
                "type": "string",
            }
        },
    },
    "UPDATEAPEXDOMAIN_REQUEST_BODY_SCHEMA": {
        "oneOf": [
            {
                "additionalProperties": False,
                "description": "update",
                "properties": {
                    "customNameservers": {
                        "deprecated": True,
                        "description": "This field is "
                        "deprecated. Please "
                        "use PATCH "
                        "/v1/registrar/domains/{domainName}/nameservers "
                        "instead.",
                        "items": {"type": "string"},
                        "maxItems": 4,
                        "minItems": 0,
                        "type": "array",
                        "uniqueItems": True,
                    },
                    "op": {"example": "update", "type": "string"},
                    "renew": {
                        "deprecated": True,
                        "description": "This field is deprecated. Please "
                        "use PATCH "
                        "/v1/registrar/domains/{domainName}/auto-renew "
                        "instead.",
                        "type": "boolean",
                    },
                    "zone": {
                        "description": "Specifies whether this is a DNS "
                        "zone that intends to use Vercel's "
                        "nameservers.",
                        "type": "boolean",
                    },
                },
                "type": "object",
            },
            {
                "additionalProperties": False,
                "description": "move-out",
                "properties": {
                    "destination": {
                        "description": "User or team to move domain to",
                        "type": "string",
                    },
                    "op": {"example": "move-out", "type": "string"},
                },
                "type": "object",
            },
        ]
    },
    "INVALIDATECACHEBYTAGS_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "tags": {
                "oneOf": [
                    {
                        "items": {"maxLength": 256, "type": "string"},
                        "maxItems": 16,
                        "minItems": 1,
                        "type": "array",
                    },
                    {"maxLength": 8196, "type": "string"},
                ]
            },
            "target": {"enum": ["production", "preview"], "type": "string"},
        },
        "required": ["tags"],
        "type": "object",
    },
    "DELETECACHEBYTAGS_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "revalidationDeadlineSeconds": {"minimum": 0, "type": "number"},
            "tags": {
                "oneOf": [
                    {
                        "items": {"maxLength": 256, "type": "string"},
                        "maxItems": 16,
                        "minItems": 1,
                        "type": "array",
                    },
                    {"maxLength": 8196, "type": "string"},
                ]
            },
            "target": {"enum": ["production", "preview"], "type": "string"},
        },
        "required": ["tags"],
        "type": "object",
    },
    "CREATEEDGECONFIG_REQUEST_BODY_SCHEMA": {
        "properties": {
            "items": {"additionalProperties": {}, "type": "object"},
            "slug": {"maxLength": 64, "pattern": "^[\\\\w-]+$", "type": "string"},
        },
        "required": ["slug"],
        "type": "object",
    },
    "UPDATEEDGECONFIGITEMS_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "items": {
                "items": {
                    "oneOf": [
                        {
                            "anyOf": [
                                {
                                    "properties": {
                                        "operation": {"enum": ["create"], "type": "string"}
                                    },
                                    "required": ["operation", "key", "value"],
                                },
                                {
                                    "properties": {"operation": {"enum": ["update", "upsert"]}},
                                    "required": ["operation", "key", "value"],
                                },
                                {
                                    "properties": {"operation": {"enum": ["update", "upsert"]}},
                                    "required": ["operation", "key", "description"],
                                },
                            ],
                            "properties": {
                                "description": {
                                    "nullable": True,
                                    "oneOf": [{"maxLength": 512, "type": "string"}, {}],
                                },
                                "key": {
                                    "maxLength": 256,
                                    "pattern": "^[\\\\w-]+$",
                                    "type": "string",
                                },
                                "operation": {"enum": ["create", "update", "upsert", "delete"]},
                                "value": {"nullable": True},
                            },
                            "type": "object",
                        }
                    ]
                },
                "type": "array",
            }
        },
        "required": ["items"],
        "type": "object",
    },
    "CONNECTINTEGRATIONRESOURCETOPROJECT_REQUEST_BODY_SCHEMA": {
        "properties": {"projectId": {"type": "string"}},
        "required": ["projectId"],
        "type": "object",
    },
    "UPDATEINTEGRATIONINSTALLATION_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "billingPlan": {
                "additionalProperties": True,
                "properties": {
                    "cost": {"type": "string"},
                    "description": {"type": "string"},
                    "details": {
                        "items": {
                            "additionalProperties": False,
                            "properties": {
                                "label": {"type": "string"},
                                "value": {"type": "string"},
                            },
                            "required": ["label"],
                            "type": "object",
                        },
                        "type": "array",
                    },
                    "effectiveDate": {"type": "string"},
                    "highlightedDetails": {
                        "items": {
                            "additionalProperties": False,
                            "properties": {
                                "label": {"type": "string"},
                                "value": {"type": "string"},
                            },
                            "required": ["label"],
                            "type": "object",
                        },
                        "type": "array",
                    },
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "paymentMethodRequired": {"type": "boolean"},
                    "type": {"enum": ["prepayment", "subscription"], "type": "string"},
                },
                "required": ["id", "type", "name"],
                "type": "object",
            },
            "notification": {
                "properties": {
                    "href": {"format": "uri", "type": "string"},
                    "level": {"enum": ["info", "warn", "error"], "type": "string"},
                    "message": {"type": "string"},
                    "title": {"type": "string"},
                },
                "required": ["level", "title"],
                "type": "object",
            },
        },
        "type": "object",
    },
    "NOTIFYVERCELOFUPDATES_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "event": {
                "oneOf": [
                    {
                        "additionalProperties": False,
                        "properties": {
                            "billingPlanId": {
                                "description": "The installation-level billing plan ID",
                                "type": "string",
                            },
                            "type": {"enum": ["installation.updated"], "type": "string"},
                        },
                        "required": ["type"],
                        "type": "object",
                    },
                    {
                        "additionalProperties": False,
                        "properties": {
                            "productId": {
                                "description": "Partner-provided product slug or id",
                                "type": "string",
                            },
                            "resourceId": {
                                "description": "Partner provided resource ID",
                                "type": "string",
                            },
                            "type": {"enum": ["resource.updated"], "type": "string"},
                        },
                        "required": ["type", "productId", "resourceId"],
                        "type": "object",
                    },
                ]
            }
        },
        "required": ["event"],
        "type": "object",
    },
    "IMPORTRESOURCETOVERCEL_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "billingPlan": {
                "additionalProperties": True,
                "properties": {
                    "cost": {"type": "string"},
                    "description": {"type": "string"},
                    "details": {
                        "items": {
                            "additionalProperties": False,
                            "properties": {
                                "label": {"type": "string"},
                                "value": {"type": "string"},
                            },
                            "required": ["label"],
                            "type": "object",
                        },
                        "type": "array",
                    },
                    "effectiveDate": {"type": "string"},
                    "highlightedDetails": {
                        "items": {
                            "additionalProperties": False,
                            "properties": {
                                "label": {"type": "string"},
                                "value": {"type": "string"},
                            },
                            "required": ["label"],
                            "type": "object",
                        },
                        "type": "array",
                    },
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "paymentMethodRequired": {"type": "boolean"},
                    "type": {"enum": ["prepayment", "subscription"], "type": "string"},
                },
                "required": ["id", "type", "name"],
                "type": "object",
            },
            "extras": {"additionalProperties": True, "type": "object"},
            "metadata": {"additionalProperties": True, "type": "object"},
            "name": {"type": "string"},
            "notification": {
                "properties": {
                    "href": {"format": "uri", "type": "string"},
                    "level": {"enum": ["info", "warn", "error"], "type": "string"},
                    "message": {"type": "string"},
                    "title": {"type": "string"},
                },
                "required": ["level", "title"],
                "type": "object",
            },
            "ownership": {"enum": ["owned", "linked", "sandbox"], "type": "string"},
            "productId": {"type": "string"},
            "secrets": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "environmentOverrides": {
                            "description": "A "
                            "map "
                            "of "
                            "environments "
                            "to "
                            "override "
                            "values "
                            "for "
                            "the "
                            "secret, "
                            "used "
                            "for "
                            "setting "
                            "different "
                            "values "
                            "across "
                            "deployments "
                            "in "
                            "production, "
                            "preview, "
                            "and "
                            "development "
                            "environments. "
                            "Note: "
                            "the "
                            "same "
                            "value "
                            "will "
                            "be "
                            "used "
                            "for "
                            "all "
                            "deployments "
                            "in "
                            "the "
                            "given "
                            "environment.",
                            "properties": {
                                "development": {
                                    "description": "Value used for development environment.",
                                    "type": "string",
                                },
                                "preview": {
                                    "description": "Value used for preview environment.",
                                    "type": "string",
                                },
                                "production": {
                                    "description": "Value used for production environment.",
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "name": {"type": "string"},
                        "prefix": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["name", "value"],
                    "type": "object",
                },
                "type": "array",
            },
            "status": {
                "enum": [
                    "ready",
                    "pending",
                    "onboarding",
                    "suspended",
                    "resumed",
                    "uninstalled",
                    "error",
                ],
                "type": "string",
            },
        },
        "required": ["productId", "name", "status"],
        "type": "object",
    },
    "UPDATERESOURCE_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "billingPlan": {
                "additionalProperties": True,
                "properties": {
                    "cost": {"type": "string"},
                    "description": {"type": "string"},
                    "details": {
                        "items": {
                            "additionalProperties": False,
                            "properties": {
                                "label": {"type": "string"},
                                "value": {"type": "string"},
                            },
                            "required": ["label"],
                            "type": "object",
                        },
                        "type": "array",
                    },
                    "effectiveDate": {"type": "string"},
                    "highlightedDetails": {
                        "items": {
                            "additionalProperties": False,
                            "properties": {
                                "label": {"type": "string"},
                                "value": {"type": "string"},
                            },
                            "required": ["label"],
                            "type": "object",
                        },
                        "type": "array",
                    },
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "paymentMethodRequired": {"type": "boolean"},
                    "type": {"enum": ["prepayment", "subscription"], "type": "string"},
                },
                "required": ["id", "type", "name"],
                "type": "object",
            },
            "extras": {"additionalProperties": True, "type": "object"},
            "metadata": {"additionalProperties": True, "type": "object"},
            "name": {"type": "string"},
            "notification": {
                "properties": {
                    "href": {"format": "uri", "type": "string"},
                    "level": {"enum": ["info", "warn", "error"], "type": "string"},
                    "message": {"type": "string"},
                    "title": {"type": "string"},
                },
                "required": ["level", "title"],
                "type": "object",
            },
            "ownership": {"enum": ["owned", "linked", "sandbox"], "type": "string"},
            "secrets": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "environmentOverrides": {
                            "description": "A "
                            "map "
                            "of "
                            "environments "
                            "to "
                            "override "
                            "values "
                            "for "
                            "the "
                            "secret, "
                            "used "
                            "for "
                            "setting "
                            "different "
                            "values "
                            "across "
                            "deployments "
                            "in "
                            "production, "
                            "preview, "
                            "and "
                            "development "
                            "environments. "
                            "Note: "
                            "the "
                            "same "
                            "value "
                            "will "
                            "be "
                            "used "
                            "for "
                            "all "
                            "deployments "
                            "in "
                            "the "
                            "given "
                            "environment.",
                            "properties": {
                                "development": {
                                    "description": "Value used for development environment.",
                                    "type": "string",
                                },
                                "preview": {
                                    "description": "Value used for preview environment.",
                                    "type": "string",
                                },
                                "production": {
                                    "description": "Value used for production environment.",
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "name": {"type": "string"},
                        "prefix": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["name", "value"],
                    "type": "object",
                },
                "type": "array",
            },
            "status": {
                "enum": [
                    "ready",
                    "pending",
                    "onboarding",
                    "suspended",
                    "resumed",
                    "uninstalled",
                    "error",
                ],
                "type": "string",
            },
        },
        "type": "object",
    },
    "SUBMITBILLINGDATA_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "billing": {
                "description": "Billing data (interim invoicing data).",
                "oneOf": [
                    {
                        "items": {
                            "additionalProperties": False,
                            "properties": {
                                "billingPlanId": {
                                    "description": "Partner's billing plan ID.",
                                    "type": "string",
                                },
                                "details": {"description": "Line item details.", "type": "string"},
                                "end": {
                                    "description": "Start "
                                    "and "
                                    "end "
                                    "are "
                                    "only "
                                    "needed "
                                    "if "
                                    "different "
                                    "from "
                                    "the "
                                    "period's "
                                    "start/end.",
                                    "format": "date-time",
                                    "type": "string",
                                },
                                "name": {"description": "Line item name.", "type": "string"},
                                "price": {
                                    "description": "Price per unit.",
                                    "pattern": "^[0-9]+(\\\\.[0-9]+)?$",
                                    "type": "string",
                                },
                                "quantity": {"description": "Quantity of units.", "type": "number"},
                                "resourceId": {
                                    "description": "Partner's resource ID.",
                                    "type": "string",
                                },
                                "start": {
                                    "description": "Start "
                                    "and "
                                    "end "
                                    "are "
                                    "only "
                                    "needed "
                                    "if "
                                    "different "
                                    "from "
                                    "the "
                                    "period's "
                                    "start/end.",
                                    "format": "date-time",
                                    "type": "string",
                                },
                                "total": {
                                    "description": "Total amount.",
                                    "pattern": "^[0-9]+(\\\\.[0-9]+)?$",
                                    "type": "string",
                                },
                                "units": {
                                    "description": "Units of the quantity.",
                                    "type": "string",
                                },
                            },
                            "required": [
                                "billingPlanId",
                                "name",
                                "price",
                                "quantity",
                                "units",
                                "total",
                            ],
                            "type": "object",
                        },
                        "type": "array",
                    },
                    {
                        "properties": {
                            "discounts": {
                                "items": {
                                    "additionalProperties": False,
                                    "properties": {
                                        "amount": {
                                            "description": "Discount amount.",
                                            "pattern": "^[0-9]+(\\\\.[0-9]+)?$",
                                            "type": "string",
                                        },
                                        "billingPlanId": {
                                            "description": "Partner's billing plan ID.",
                                            "type": "string",
                                        },
                                        "details": {
                                            "description": "Discount details.",
                                            "type": "string",
                                        },
                                        "end": {
                                            "description": "Start "
                                            "and "
                                            "end "
                                            "are "
                                            "only "
                                            "needed "
                                            "if "
                                            "different "
                                            "from "
                                            "the "
                                            "period's "
                                            "start/end.",
                                            "format": "date-time",
                                            "type": "string",
                                        },
                                        "name": {"description": "Discount name.", "type": "string"},
                                        "resourceId": {
                                            "description": "Partner's resource ID.",
                                            "type": "string",
                                        },
                                        "start": {
                                            "description": "Start "
                                            "and "
                                            "end "
                                            "are "
                                            "only "
                                            "needed "
                                            "if "
                                            "different "
                                            "from "
                                            "the "
                                            "period's "
                                            "start/end.",
                                            "format": "date-time",
                                            "type": "string",
                                        },
                                    },
                                    "required": ["billingPlanId", "name", "amount"],
                                    "type": "object",
                                },
                                "type": "array",
                            },
                            "items": {
                                "items": {
                                    "additionalProperties": False,
                                    "properties": {
                                        "billingPlanId": {
                                            "description": "Partner's billing plan ID.",
                                            "type": "string",
                                        },
                                        "details": {
                                            "description": "Line item details.",
                                            "type": "string",
                                        },
                                        "end": {
                                            "description": "Start "
                                            "and "
                                            "end "
                                            "are "
                                            "only "
                                            "needed "
                                            "if "
                                            "different "
                                            "from "
                                            "the "
                                            "period's "
                                            "start/end.",
                                            "format": "date-time",
                                            "type": "string",
                                        },
                                        "name": {
                                            "description": "Line item name.",
                                            "type": "string",
                                        },
                                        "price": {
                                            "description": "Price per unit.",
                                            "pattern": "^[0-9]+(\\\\.[0-9]+)?$",
                                            "type": "string",
                                        },
                                        "quantity": {
                                            "description": "Quantity of units.",
                                            "type": "number",
                                        },
                                        "resourceId": {
                                            "description": "Partner's resource ID.",
                                            "type": "string",
                                        },
                                        "start": {
                                            "description": "Start "
                                            "and "
                                            "end "
                                            "are "
                                            "only "
                                            "needed "
                                            "if "
                                            "different "
                                            "from "
                                            "the "
                                            "period's "
                                            "start/end.",
                                            "format": "date-time",
                                            "type": "string",
                                        },
                                        "total": {
                                            "description": "Total amount.",
                                            "pattern": "^[0-9]+(\\\\.[0-9]+)?$",
                                            "type": "string",
                                        },
                                        "units": {
                                            "description": "Units of the quantity.",
                                            "type": "string",
                                        },
                                    },
                                    "required": [
                                        "billingPlanId",
                                        "name",
                                        "price",
                                        "quantity",
                                        "units",
                                        "total",
                                    ],
                                    "type": "object",
                                },
                                "type": "array",
                            },
                        },
                        "required": ["items"],
                        "type": "object",
                    },
                ],
            },
            "eod": {
                "description": "End of Day, the UTC datetime for when the end "
                "of the billing/usage day is in UTC time. This "
                "tells us which day the usage data is for, and "
                'also allows for your \\"end of day\\" to be '
                "different from UTC 00:00:00. eod must be "
                "within the period dates, and cannot be older "
                "than 24h earlier from our server's current "
                "time.",
                "format": "date-time",
                "type": "string",
            },
            "period": {
                "additionalProperties": False,
                "description": "Period for the billing cycle. The period "
                "end date cannot be older than 24 hours "
                "earlier than our current server's time.",
                "properties": {
                    "end": {"format": "date-time", "type": "string"},
                    "start": {"format": "date-time", "type": "string"},
                },
                "required": ["start", "end"],
                "type": "object",
            },
            "timestamp": {
                "description": "Server time of your integration, used to "
                "determine the most recent data for race "
                "conditions & updates. Only the latest "
                "usage data for a given day, week, and "
                "month will be kept.",
                "format": "date-time",
                "type": "string",
            },
            "usage": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "dayValue": {
                            "description": "Metric "
                            "value "
                            "for "
                            "the "
                            "day. "
                            "Could "
                            "be a "
                            "final "
                            "or an "
                            "interim "
                            "value "
                            "for "
                            "the "
                            "day.",
                            "type": "number",
                        },
                        "name": {"description": "Metric name.", "type": "string"},
                        "periodValue": {
                            "description": "Metric "
                            "value "
                            "for "
                            "the "
                            "billing "
                            "period. "
                            "Could "
                            "be "
                            "a "
                            "final "
                            "or "
                            "an "
                            "interim "
                            "value "
                            "for "
                            "the "
                            "period.",
                            "type": "number",
                        },
                        "planValue": {
                            "description": "The "
                            "limit "
                            "value "
                            "of "
                            "the "
                            "metric "
                            "for a "
                            "billing "
                            "period, "
                            "if a "
                            "limit "
                            "is "
                            "defined "
                            "by "
                            "the "
                            "plan.",
                            "type": "number",
                        },
                        "resourceId": {"description": "Partner's resource ID.", "type": "string"},
                        "type": {
                            "description": "\\n              "
                            "Type of "
                            "the "
                            "metric.\\n              "
                            "- total: "
                            "measured "
                            "total "
                            "value, "
                            "such as "
                            "Database "
                            "size\\n              "
                            "- "
                            "interval: "
                            "usage "
                            "during the "
                            "period, "
                            "such as "
                            "i/o or "
                            "number of "
                            "queries.\\n              "
                            "- rate: "
                            "rate of "
                            "usage, "
                            "such as "
                            "queries "
                            "per "
                            "second.\\n            ",
                            "enum": ["total", "interval", "rate"],
                            "type": "string",
                        },
                        "units": {
                            "description": 'Metric units. Example: \\"GB\\"',
                            "type": "string",
                        },
                    },
                    "required": ["name", "type", "units", "dayValue", "periodValue"],
                    "type": "object",
                },
                "type": "array",
            },
        },
        "required": ["timestamp", "eod", "period", "billing", "usage"],
        "type": "object",
    },
    "SUBMITINVOICETOVERCEL_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "discounts": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "amount": {
                            "description": "Currency amount as a decimal string.",
                            "pattern": "^[0-9]+(\\\\.[0-9]+)?$",
                            "type": "string",
                        },
                        "billingPlanId": {
                            "description": "Partner's billing plan ID.",
                            "type": "string",
                        },
                        "details": {"type": "string"},
                        "end": {
                            "description": "Start "
                            "and end "
                            "are "
                            "only "
                            "needed "
                            "if "
                            "different "
                            "from "
                            "the "
                            "period's "
                            "start/end.",
                            "format": "date-time",
                            "type": "string",
                        },
                        "name": {"type": "string"},
                        "resourceId": {"description": "Partner's resource ID.", "type": "string"},
                        "start": {
                            "description": "Start "
                            "and "
                            "end "
                            "are "
                            "only "
                            "needed "
                            "if "
                            "different "
                            "from "
                            "the "
                            "period's "
                            "start/end.",
                            "format": "date-time",
                            "type": "string",
                        },
                    },
                    "required": ["billingPlanId", "name", "amount"],
                    "type": "object",
                },
                "type": "array",
            },
            "externalId": {"type": "string"},
            "invoiceDate": {
                "description": "Invoice date. Must be within the period's start and end.",
                "format": "date-time",
                "type": "string",
            },
            "items": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "billingPlanId": {
                            "description": "Partner's billing plan ID.",
                            "type": "string",
                        },
                        "details": {"type": "string"},
                        "end": {
                            "description": "Start and "
                            "end are "
                            "only needed "
                            "if "
                            "different "
                            "from the "
                            "period's "
                            "start/end.",
                            "format": "date-time",
                            "type": "string",
                        },
                        "name": {"type": "string"},
                        "price": {
                            "description": "Currency amount as a decimal string.",
                            "pattern": "^[0-9]+(\\\\.[0-9]+)?$",
                            "type": "string",
                        },
                        "quantity": {"type": "number"},
                        "resourceId": {"description": "Partner's resource ID.", "type": "string"},
                        "start": {
                            "description": "Start and "
                            "end are "
                            "only "
                            "needed if "
                            "different "
                            "from the "
                            "period's "
                            "start/end.",
                            "format": "date-time",
                            "type": "string",
                        },
                        "total": {
                            "description": "Currency amount as a decimal string.",
                            "pattern": "^[0-9]+(\\\\.[0-9]+)?$",
                            "type": "string",
                        },
                        "units": {"type": "string"},
                    },
                    "required": ["billingPlanId", "name", "price", "quantity", "units", "total"],
                    "type": "object",
                },
                "type": "array",
            },
            "memo": {"description": "Additional memo for the invoice.", "type": "string"},
            "period": {
                "additionalProperties": False,
                "description": "Subscription period for this billing cycle.",
                "properties": {
                    "end": {"format": "date-time", "type": "string"},
                    "start": {"format": "date-time", "type": "string"},
                },
                "required": ["start", "end"],
                "type": "object",
            },
            "test": {
                "additionalProperties": False,
                "description": "Test mode",
                "properties": {
                    "result": {"enum": ["paid", "notpaid"], "type": "string"},
                    "validate": {"type": "boolean"},
                },
                "type": "object",
            },
        },
        "required": ["invoiceDate", "period", "items"],
        "type": "object",
    },
    "REQUESTVERCELINVOICEREFUND_REQUEST_BODY_SCHEMA": {
        "oneOf": [
            {
                "additionalProperties": False,
                "properties": {
                    "action": {"enum": ["refund"], "type": "string"},
                    "reason": {"description": "Refund reason.", "type": "string"},
                    "total": {
                        "description": "The total amount to be refunded. "
                        "Must be less than or equal to the "
                        "total amount of the invoice.",
                        "pattern": "^[0-9]+(\\\\.[0-9]+)?$",
                        "type": "string",
                    },
                },
                "required": ["action", "reason", "total"],
                "type": "object",
            }
        ]
    },
    "SUBMITPREPAYMENTBALANCES_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "balances": {
                "items": {
                    "additionalProperties": False,
                    "description": "A credit balance for a particular token type",
                    "properties": {
                        "credit": {
                            "description": "A "
                            "human-readable "
                            "description "
                            "of "
                            "the "
                            "credits "
                            "the "
                            "user "
                            "currently "
                            "has, "
                            "e.g. "
                            '\\"2,000 '
                            'Tokens\\"',
                            "type": "string",
                        },
                        "currencyValueInCents": {
                            "description": "The "
                            "dollar "
                            "value "
                            "of "
                            "the "
                            "credit "
                            "balance, "
                            "in "
                            "USD "
                            "and "
                            "provided "
                            "in "
                            "cents, "
                            "which "
                            "is "
                            "used "
                            "to "
                            "trigger "
                            "automatic "
                            "purchase "
                            "thresholds.",
                            "type": "number",
                        },
                        "nameLabel": {
                            "description": "The "
                            "name "
                            "of "
                            "the "
                            "credits, "
                            "for "
                            "display "
                            "purposes, "
                            "e.g. "
                            '\\"Tokens\\"',
                            "type": "string",
                        },
                        "resourceId": {
                            "description": "Partner's "
                            "resource "
                            "ID, "
                            "exclude "
                            "if "
                            "credits "
                            "are "
                            "tied "
                            "to "
                            "the "
                            "installation "
                            "and "
                            "not "
                            "an "
                            "individual "
                            "resource.",
                            "type": "string",
                        },
                    },
                    "required": ["currencyValueInCents"],
                    "type": "object",
                },
                "type": "array",
            },
            "timestamp": {
                "description": "Server time of your integration, used to "
                "determine the most recent data for race "
                "conditions & updates. Only the latest "
                "usage data for a given day, week, and "
                "month will be kept.",
                "format": "date-time",
                "type": "string",
            },
        },
        "required": ["timestamp", "balances"],
        "type": "object",
    },
    "UPDATERESOURCESECRETS_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "partial": {
                "description": "If true, will only update the provided secrets",
                "type": "boolean",
            },
            "secrets": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "environmentOverrides": {
                            "description": "A "
                            "map "
                            "of "
                            "environments "
                            "to "
                            "override "
                            "values "
                            "for "
                            "the "
                            "secret, "
                            "used "
                            "for "
                            "setting "
                            "different "
                            "values "
                            "across "
                            "deployments "
                            "in "
                            "production, "
                            "preview, "
                            "and "
                            "development "
                            "environments. "
                            "Note: "
                            "the "
                            "same "
                            "value "
                            "will "
                            "be "
                            "used "
                            "for "
                            "all "
                            "deployments "
                            "in "
                            "the "
                            "given "
                            "environment.",
                            "properties": {
                                "development": {
                                    "description": "Value used for development environment.",
                                    "type": "string",
                                },
                                "preview": {
                                    "description": "Value used for preview environment.",
                                    "type": "string",
                                },
                                "production": {
                                    "description": "Value used for production environment.",
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "name": {"type": "string"},
                        "prefix": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["name", "value"],
                    "type": "object",
                },
                "type": "array",
            },
        },
        "required": ["secrets"],
        "type": "object",
    },
    "UPDATESECRETSBYID_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "partial": {
                "description": "If true, will only overwrite the provided "
                "secrets instead of replacing all secrets.",
                "type": "boolean",
            },
            "secrets": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "environmentOverrides": {
                            "description": "A "
                            "map "
                            "of "
                            "environments "
                            "to "
                            "override "
                            "values "
                            "for "
                            "the "
                            "secret, "
                            "used "
                            "for "
                            "setting "
                            "different "
                            "values "
                            "across "
                            "deployments "
                            "in "
                            "production, "
                            "preview, "
                            "and "
                            "development "
                            "environments. "
                            "Note: "
                            "the "
                            "same "
                            "value "
                            "will "
                            "be "
                            "used "
                            "for "
                            "all "
                            "deployments "
                            "in "
                            "the "
                            "given "
                            "environment.",
                            "properties": {
                                "development": {
                                    "description": "Value used for development environment.",
                                    "type": "string",
                                },
                                "preview": {
                                    "description": "Value used for preview environment.",
                                    "type": "string",
                                },
                                "production": {
                                    "description": "Value used for production environment.",
                                    "type": "string",
                                },
                            },
                            "type": "object",
                        },
                        "name": {"type": "string"},
                        "prefix": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["name", "value"],
                    "type": "object",
                },
                "type": "array",
            },
        },
        "required": ["secrets"],
        "type": "object",
    },
    "CREATEINTEGRATIONLOGDRAIN_REQUEST_BODY_SCHEMA": {
        "properties": {
            "deliveryFormat": {
                "description": "The delivery log format",
                "enum": ["json", "ndjson"],
                "example": "json",
            },
            "environments": {
                "items": {"enum": ["preview", "production"], "type": "string"},
                "minItems": 1,
                "type": "array",
                "uniqueItems": True,
            },
            "headers": {
                "additionalProperties": {"type": "string"},
                "description": "Headers to be sent together with the request",
                "type": "object",
            },
            "name": {
                "description": "The name of the log drain",
                "example": "My first log drain",
                "maxLength": 100,
                "pattern": "^[A-z0-9_ -]+$",
                "type": "string",
            },
            "projectIds": {
                "items": {"pattern": "^[a-zA-z0-9_]+$", "type": "string"},
                "maxItems": 50,
                "minItems": 1,
                "type": "array",
            },
            "secret": {
                "description": "A secret to sign log drain notification "
                "headers so a consumer can verify their "
                "authenticity",
                "example": "a1Xsfd325fXcs",
                "maxLength": 100,
                "pattern": "^[A-z0-9_ -]+$",
                "type": "string",
            },
            "sources": {
                "items": {
                    "enum": ["static", "lambda", "build", "edge", "external", "firewall"],
                    "type": "string",
                },
                "minItems": 1,
                "type": "array",
                "uniqueItems": True,
            },
            "url": {
                "description": "The url where you will receive logs. The "
                "protocol must be `https://` or `http://` when "
                "type is `json` and `ndjson`.",
                "example": "https://example.com/log-drain",
                "format": "uri",
                "pattern": "^https?://",
                "type": "string",
            },
        },
        "required": ["name", "url"],
        "type": "object",
    },
    "CREATEEXPERIMENTATIONITEMS_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "items": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "category": {"enum": ["experiment", "flag"], "type": "string"},
                        "createdAt": {"type": "number"},
                        "description": {"maxLength": 1024, "type": "string"},
                        "id": {"maxLength": 1024, "type": "string"},
                        "isArchived": {"type": "boolean"},
                        "name": {"maxLength": 1024, "type": "string"},
                        "origin": {"maxLength": 2048, "type": "string"},
                        "slug": {"maxLength": 1024, "type": "string"},
                        "updatedAt": {"type": "number"},
                    },
                    "required": ["id", "slug", "origin"],
                    "type": "object",
                },
                "maxItems": 50,
                "type": "array",
            }
        },
        "required": ["items"],
        "type": "object",
    },
    "UPDATEEXPERIMENTATIONITEM_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "category": {"enum": ["experiment", "flag"], "type": "string"},
            "createdAt": {"type": "number"},
            "description": {"maxLength": 1024, "type": "string"},
            "isArchived": {"type": "boolean"},
            "name": {"maxLength": 1024, "type": "string"},
            "origin": {"maxLength": 2048, "type": "string"},
            "slug": {"maxLength": 1024, "type": "string"},
            "updatedAt": {"type": "number"},
        },
        "required": ["slug", "origin"],
        "type": "object",
    },
    "PUSHEDGECONFIG_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {"data": {"additionalProperties": {}, "type": "object"}},
        "required": ["data"],
        "type": "object",
    },
    "ADDPROJECTMEMBER_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "oneOf": [{"required": ["uid"]}, {"required": ["username"]}, {"required": ["email"]}],
        "properties": {
            "email": {
                "description": "The email of the team member that should be added to this project.",
                "example": "entity@example.com",
                "format": "email",
                "type": "string",
            },
            "role": {
                "description": "The project role of the member that will be added.",
                "enum": ["ADMIN", "PROJECT_DEVELOPER", "PROJECT_VIEWER"],
                "example": "ADMIN",
                "type": "string",
            },
            "uid": {
                "description": "The ID of the team member that should be added to this project.",
                "example": "ndlgr43fadlPyCtREAqxxdyFK",
                "maxLength": 256,
                "type": "string",
            },
            "username": {
                "description": "The username of the team member that "
                "should be added to this project.",
                "example": "example",
                "maxLength": 256,
                "type": "string",
            },
        },
        "required": ["role"],
        "type": "object",
    },
    "CREATENEWPROJECT_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "buildCommand": {
                "description": "The build command for this project. "
                "When `null` is used this value will "
                "be automatically detected",
                "maxLength": 256,
                "nullable": True,
                "type": "string",
            },
            "commandForIgnoringBuildStep": {"maxLength": 256, "nullable": True, "type": "string"},
            "devCommand": {
                "description": "The dev command for this project. When "
                "`null` is used this value will be "
                "automatically detected",
                "maxLength": 256,
                "nullable": True,
                "type": "string",
            },
            "enableAffectedProjectsDeployments": {
                "description": "Opt-in to skip "
                "deployments when "
                "there are no "
                "changes to the "
                "root directory "
                "and its "
                "dependencies",
                "type": "boolean",
            },
            "enablePreviewFeedback": {
                "description": "Opt-in to preview toolbar on the project level",
                "nullable": True,
                "type": "boolean",
            },
            "enableProductionFeedback": {
                "description": "Opt-in to production toolbar on the project level",
                "nullable": True,
                "type": "boolean",
            },
            "environmentVariables": {
                "description": "Collection of ENV Variables the Project will use",
                "items": {
                    "properties": {
                        "gitBranch": {
                            "description": "If "
                            "defined, "
                            "the "
                            "git "
                            "branch "
                            "of "
                            "the "
                            "environment "
                            "variable "
                            "(must "
                            "have "
                            "target=preview)",
                            "maxLength": 250,
                            "type": "string",
                        },
                        "key": {"description": "Name of the ENV variable", "type": "string"},
                        "target": {
                            "description": "Deployment "
                            "Target "
                            "or "
                            "Targets "
                            "in "
                            "which "
                            "the "
                            "ENV "
                            "variable "
                            "will "
                            "be "
                            "used",
                            "oneOf": [
                                {"enum": ["production", "preview", "development"]},
                                {
                                    "items": {"enum": ["production", "preview", "development"]},
                                    "type": "array",
                                },
                            ],
                        },
                        "type": {
                            "description": "Type of the ENV variable",
                            "enum": ["system", "secret", "encrypted", "plain", "sensitive"],
                            "type": "string",
                        },
                        "value": {"description": "Value for the ENV variable", "type": "string"},
                    },
                    "required": ["key", "value", "target"],
                    "type": "object",
                },
                "type": "array",
            },
            "framework": {
                "description": "The framework that is being used for "
                "this project. When `null` is used no "
                "framework is selected",
                "enum": [
                    None,
                    "blitzjs",
                    "nextjs",
                    "gatsby",
                    "remix",
                    "react-router",
                    "astro",
                    "hexo",
                    "eleventy",
                    "docusaurus-2",
                    "docusaurus",
                    "preact",
                    "solidstart-1",
                    "solidstart",
                    "dojo",
                    "ember",
                    "vue",
                    "scully",
                    "ionic-angular",
                    "angular",
                    "polymer",
                    "svelte",
                    "sveltekit",
                    "sveltekit-1",
                    "ionic-react",
                    "create-react-app",
                    "gridsome",
                    "umijs",
                    "sapper",
                    "saber",
                    "stencil",
                    "nuxtjs",
                    "redwoodjs",
                    "hugo",
                    "jekyll",
                    "brunch",
                    "middleman",
                    "zola",
                    "hydrogen",
                    "vite",
                    "vitepress",
                    "vuepress",
                    "parcel",
                    "fastapi",
                    "flask",
                    "fasthtml",
                    "sanity-v3",
                    "sanity",
                    "storybook",
                    "nitro",
                    "hono",
                    "express",
                    "h3",
                    "nestjs",
                    "xmcp",
                ],
            },
            "gitRepository": {
                "description": "The Git Repository that will be "
                "connected to the project. When this "
                "is defined, any pushes to the "
                "specified connected Git Repository "
                "will be automatically deployed",
                "properties": {
                    "repo": {
                        "description": "The name of "
                        "the git "
                        "repository. "
                        "For example: "
                        '\\"vercel/next.js\\"',
                        "type": "string",
                    },
                    "type": {
                        "description": "The Git Provider of the repository",
                        "enum": ["github", "github-limited", "gitlab", "bitbucket"],
                    },
                },
                "required": ["type", "repo"],
                "type": "object",
            },
            "installCommand": {
                "description": "The install command for this "
                "project. When `null` is used this "
                "value will be automatically "
                "detected",
                "maxLength": 256,
                "nullable": True,
                "type": "string",
            },
            "name": {
                "description": "The desired name for the project",
                "example": "a-project-name",
                "maxLength": 100,
                "type": "string",
            },
            "oidcTokenConfig": {
                "additionalProperties": False,
                "description": "OpenID Connect JSON Web Token generation configuration.",
                "properties": {
                    "enabled": {
                        "default": True,
                        "deprecated": True,
                        "description": "Whether or not to generate OpenID Connect JSON Web Tokens.",
                        "type": "boolean",
                    },
                    "issuerMode": {
                        "default": "team",
                        "description": "team: "
                        "`https://oidc.vercel.com/[team_slug]` "
                        "global: "
                        "`https://oidc.vercel.com`",
                        "enum": ["team", "global"],
                        "type": "string",
                    },
                },
                "type": "object",
            },
            "outputDirectory": {
                "description": "The output directory of the "
                "project. When `null` is used this "
                "value will be automatically "
                "detected",
                "maxLength": 256,
                "nullable": True,
                "type": "string",
            },
            "previewDeploymentsDisabled": {
                "description": "Specifies whether "
                "preview deployments are "
                "disabled for this "
                "project.",
                "nullable": True,
                "type": "boolean",
            },
            "publicSource": {
                "description": "Specifies whether the source code and "
                "logs of the deployments for this "
                "project should be public or not",
                "nullable": True,
                "type": "boolean",
            },
            "resourceConfig": {
                "additionalProperties": False,
                "description": "Specifies resource override configuration for the project",
                "properties": {
                    "buildMachineType": {"enum": ["enhanced", "turbo"]},
                    "elasticConcurrencyEnabled": {"type": "boolean"},
                    "fluid": {"type": "boolean"},
                    "functionDefaultMemoryType": {
                        "enum": ["standard_legacy", "standard", "performance"]
                    },
                    "functionDefaultRegions": {
                        "description": "The regions to deploy Vercel Functions to for this project",
                        "items": {"maxLength": 4, "type": "string"},
                        "minItems": 1,
                        "type": "array",
                        "uniqueItems": True,
                    },
                    "functionDefaultTimeout": {"maximum": 900, "minimum": 1, "type": "number"},
                    "functionZeroConfigFailover": {
                        "description": "Specifies "
                        "whether "
                        "Zero "
                        "Config "
                        "Failover "
                        "is "
                        "enabled "
                        "for "
                        "this "
                        "project.",
                        "oneOf": [{"type": "boolean"}],
                    },
                    "isNSNBDisabled": {"type": "boolean"},
                },
                "type": "object",
            },
            "rootDirectory": {
                "description": "The name of a directory or relative "
                "path to the source code of your "
                "project. When `null` is used it will "
                "default to the project root",
                "maxLength": 256,
                "nullable": True,
                "type": "string",
            },
            "serverlessFunctionRegion": {
                "description": "The region to deploy Serverless Functions in this project",
                "maxLength": 4,
                "nullable": True,
                "type": "string",
            },
            "serverlessFunctionZeroConfigFailover": {
                "description": "Specifies "
                "whether Zero "
                "Config "
                "Failover is "
                "enabled for "
                "this project.",
                "oneOf": [{"type": "boolean"}],
            },
            "skipGitConnectDuringLink": {
                "deprecated": True,
                "description": "Opts-out of the message "
                "prompting a CLI user to "
                "connect a Git repository "
                "in `vercel link`.",
                "type": "boolean",
            },
            "ssoProtection": {
                "description": "The Vercel Auth setting for the "
                'project (historically named \\"SSO '
                'Protection\\")',
                "nullable": True,
                "properties": {
                    "deploymentType": {
                        "enum": [
                            "all",
                            "preview",
                            "prod_deployment_urls_and_all_previews",
                            "all_except_custom_domains",
                        ],
                        "type": "string",
                    }
                },
                "required": ["deploymentType"],
                "type": "object",
            },
        },
        "required": ["name"],
        "type": "object",
    },
    "UPDATEPROJECTDETAILS_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "autoAssignCustomDomains": {"type": "boolean"},
            "autoAssignCustomDomainsUpdatedBy": {"type": "string"},
            "autoExposeSystemEnvs": {"type": "boolean"},
            "buildCommand": {
                "description": "The build command for this project. "
                "When `null` is used this value will "
                "be automatically detected",
                "maxLength": 256,
                "nullable": True,
                "type": "string",
            },
            "commandForIgnoringBuildStep": {"maxLength": 256, "nullable": True, "type": "string"},
            "connectConfigurations": {
                "description": "The list of connections from "
                "project environment to "
                "Secure Compute network",
                "items": {
                    "additionalProperties": False,
                    "oneOf": [{"type": "object"}],
                    "properties": {
                        "buildsEnabled": {
                            "description": "Flag "
                            "saying "
                            "if "
                            "project "
                            "builds "
                            "should "
                            "use "
                            "Secure "
                            "Compute",
                            "type": "boolean",
                        },
                        "connectConfigurationId": {
                            "description": "The ID of the Secure Compute network",
                            "type": "string",
                        },
                        "envId": {"description": "The ID of the environment", "type": "string"},
                        "passive": {
                            "description": "Whether "
                            "the "
                            "configuration "
                            "should "
                            "be "
                            "passive, "
                            "meaning "
                            "builds "
                            "will "
                            "not "
                            "run "
                            "there "
                            "and "
                            "only "
                            "passive "
                            "Serverless "
                            "Functions "
                            "will "
                            "be "
                            "deployed",
                            "type": "boolean",
                        },
                    },
                    "required": ["envId", "connectConfigurationId", "passive", "buildsEnabled"],
                },
                "minItems": 1,
                "nullable": True,
                "type": "array",
            },
            "customerSupportCodeVisibility": {
                "description": "Specifies whether "
                "customer support can "
                "see git source for a "
                "deployment",
                "type": "boolean",
            },
            "devCommand": {
                "description": "The dev command for this project. When "
                "`null` is used this value will be "
                "automatically detected",
                "maxLength": 256,
                "nullable": True,
                "type": "string",
            },
            "directoryListing": {"type": "boolean"},
            "enableAffectedProjectsDeployments": {
                "description": "Opt-in to skip "
                "deployments when "
                "there are no "
                "changes to the "
                "root directory "
                "and its "
                "dependencies",
                "type": "boolean",
            },
            "enablePreviewFeedback": {
                "description": "Opt-in to preview toolbar on the project level",
                "nullable": True,
                "type": "boolean",
            },
            "enableProductionFeedback": {
                "description": "Opt-in to production toolbar on the project level",
                "nullable": True,
                "type": "boolean",
            },
            "framework": {
                "description": "The framework that is being used for "
                "this project. When `null` is used no "
                "framework is selected",
                "enum": [
                    None,
                    "blitzjs",
                    "nextjs",
                    "gatsby",
                    "remix",
                    "react-router",
                    "astro",
                    "hexo",
                    "eleventy",
                    "docusaurus-2",
                    "docusaurus",
                    "preact",
                    "solidstart-1",
                    "solidstart",
                    "dojo",
                    "ember",
                    "vue",
                    "scully",
                    "ionic-angular",
                    "angular",
                    "polymer",
                    "svelte",
                    "sveltekit",
                    "sveltekit-1",
                    "ionic-react",
                    "create-react-app",
                    "gridsome",
                    "umijs",
                    "sapper",
                    "saber",
                    "stencil",
                    "nuxtjs",
                    "redwoodjs",
                    "hugo",
                    "jekyll",
                    "brunch",
                    "middleman",
                    "zola",
                    "hydrogen",
                    "vite",
                    "vitepress",
                    "vuepress",
                    "parcel",
                    "fastapi",
                    "flask",
                    "fasthtml",
                    "sanity-v3",
                    "sanity",
                    "storybook",
                    "nitro",
                    "hono",
                    "express",
                    "h3",
                    "nestjs",
                    "xmcp",
                ],
                "nullable": True,
                "type": "string",
            },
            "gitForkProtection": {
                "description": "Specifies whether PRs from Git "
                "forks should require a team "
                "member's authorization before it "
                "can be deployed",
                "type": "boolean",
            },
            "gitLFS": {
                "description": "Specifies whether Git LFS is enabled for this project.",
                "type": "boolean",
            },
            "installCommand": {
                "description": "The install command for this "
                "project. When `null` is used this "
                "value will be automatically "
                "detected",
                "maxLength": 256,
                "nullable": True,
                "type": "string",
            },
            "name": {
                "description": "The desired name for the project",
                "example": "a-project-name",
                "maxLength": 100,
                "type": "string",
            },
            "nodeVersion": {
                "enum": ["22.x", "20.x", "18.x", "16.x", "14.x", "12.x", "10.x"],
                "type": "string",
            },
            "oidcTokenConfig": {
                "additionalProperties": False,
                "description": "OpenID Connect JSON Web Token generation configuration.",
                "properties": {
                    "enabled": {
                        "default": True,
                        "deprecated": True,
                        "description": "Whether or not to generate OpenID Connect JSON Web Tokens.",
                        "type": "boolean",
                    },
                    "issuerMode": {
                        "default": "team",
                        "description": "team: "
                        "`https://oidc.vercel.com/[team_slug]` "
                        "global: "
                        "`https://oidc.vercel.com`",
                        "enum": ["team", "global"],
                        "type": "string",
                    },
                },
                "type": "object",
            },
            "optionsAllowlist": {
                "additionalProperties": False,
                "description": "Specify a list of paths that "
                "should not be protected by "
                "Deployment Protection to enable "
                "Cors preflight requests",
                "nullable": True,
                "properties": {
                    "paths": {
                        "items": {
                            "additionalProperties": False,
                            "properties": {
                                "value": {
                                    "description": "The "
                                    "regex "
                                    "path "
                                    "that "
                                    "should "
                                    "not "
                                    "be "
                                    "protected "
                                    "by "
                                    "Deployment "
                                    "Protection",
                                    "pattern": "^/.*",
                                    "type": "string",
                                }
                            },
                            "required": ["value"],
                            "type": "object",
                        },
                        "maxItems": 5,
                        "minItems": 1,
                        "type": "array",
                    }
                },
                "required": ["paths"],
                "type": "object",
            },
            "outputDirectory": {
                "description": "The output directory of the "
                "project. When `null` is used this "
                "value will be automatically "
                "detected",
                "maxLength": 256,
                "nullable": True,
                "type": "string",
            },
            "passwordProtection": {
                "additionalProperties": False,
                "description": "Allows to protect project deployments with a password",
                "nullable": True,
                "properties": {
                    "deploymentType": {
                        "description": "Specify "
                        "if "
                        "the "
                        "password "
                        "will "
                        "apply "
                        "to "
                        "every "
                        "Deployment "
                        "Target "
                        "or "
                        "just "
                        "Preview",
                        "enum": [
                            "all",
                            "preview",
                            "prod_deployment_urls_and_all_previews",
                            "all_except_custom_domains",
                        ],
                        "type": "string",
                    },
                    "password": {
                        "description": "The "
                        "password "
                        "that "
                        "will "
                        "be "
                        "used "
                        "to "
                        "protect "
                        "Project "
                        "Deployments",
                        "maxLength": 72,
                        "nullable": True,
                        "type": "string",
                    },
                },
                "required": ["deploymentType"],
                "type": "object",
            },
            "previewDeploymentsDisabled": {
                "description": "Specifies whether "
                "preview deployments are "
                "disabled for this "
                "project.",
                "nullable": True,
                "type": "boolean",
            },
            "publicSource": {
                "description": "Specifies whether the source code and "
                "logs of the deployments for this "
                "project should be public or not",
                "nullable": True,
                "type": "boolean",
            },
            "resourceConfig": {
                "additionalProperties": False,
                "description": "Specifies resource override configuration for the project",
                "properties": {
                    "buildMachineType": {"enum": [None, "enhanced", "turbo"]},
                    "elasticConcurrencyEnabled": {"type": "boolean"},
                    "fluid": {"type": "boolean"},
                    "functionDefaultMemoryType": {
                        "enum": ["standard_legacy", "standard", "performance"]
                    },
                    "functionDefaultRegions": {
                        "description": "The regions to deploy Vercel Functions to for this project",
                        "items": {"maxLength": 4, "type": "string"},
                        "minItems": 1,
                        "type": "array",
                        "uniqueItems": True,
                    },
                    "functionDefaultTimeout": {"maximum": 900, "minimum": 1, "type": "number"},
                    "functionZeroConfigFailover": {
                        "description": "Specifies "
                        "whether "
                        "Zero "
                        "Config "
                        "Failover "
                        "is "
                        "enabled "
                        "for "
                        "this "
                        "project.",
                        "oneOf": [{"type": "boolean"}],
                    },
                    "isNSNBDisabled": {"type": "boolean"},
                },
                "type": "object",
            },
            "rootDirectory": {
                "description": "The name of a directory or relative "
                "path to the source code of your "
                "project. When `null` is used it will "
                "default to the project root",
                "maxLength": 256,
                "nullable": True,
                "type": "string",
            },
            "serverlessFunctionRegion": {
                "description": "The region to deploy Serverless Functions in this project",
                "maxLength": 4,
                "nullable": True,
                "type": "string",
            },
            "serverlessFunctionZeroConfigFailover": {
                "description": "Specifies "
                "whether Zero "
                "Config "
                "Failover is "
                "enabled for "
                "this project.",
                "oneOf": [{"type": "boolean"}],
            },
            "skewProtectionBoundaryAt": {
                "description": "Deployments created "
                "before this absolute "
                "datetime have Skew "
                "Protection disabled. "
                "Value is in milliseconds "
                "since epoch to match "
                '\\"createdAt\\" fields.',
                "minimum": 0,
                "type": "integer",
            },
            "skewProtectionMaxAge": {
                "description": "Deployments created before "
                "this rolling window have Skew "
                "Protection disabled. Value is "
                "in seconds to match "
                '\\"revalidate\\" fields.',
                "minimum": 0,
                "type": "integer",
            },
            "skipGitConnectDuringLink": {
                "deprecated": True,
                "description": "Opts-out of the message "
                "prompting a CLI user to "
                "connect a Git repository "
                "in `vercel link`.",
                "type": "boolean",
            },
            "sourceFilesOutsideRootDirectory": {
                "description": "Indicates if there are source files outside of the root directory",
                "type": "boolean",
            },
            "ssoProtection": {
                "additionalProperties": False,
                "description": "Ensures visitors to your Preview "
                "Deployments are logged into Vercel "
                "and have a minimum of Viewer access "
                "on your team",
                "nullable": True,
                "properties": {
                    "deploymentType": {
                        "default": "preview",
                        "description": "Specify "
                        "if "
                        "the "
                        "Vercel "
                        "Authentication "
                        "(SSO "
                        "Protection) "
                        "will "
                        "apply "
                        "to "
                        "every "
                        "Deployment "
                        "Target "
                        "or "
                        "just "
                        "Preview",
                        "enum": [
                            "all",
                            "preview",
                            "prod_deployment_urls_and_all_previews",
                            "all_except_custom_domains",
                        ],
                        "type": "string",
                    }
                },
                "required": ["deploymentType"],
                "type": "object",
            },
            "staticIps": {
                "additionalProperties": False,
                "description": "Manage Static IPs for this project",
                "properties": {
                    "enabled": {
                        "description": "Opt-in to Static IPs for this project",
                        "type": "boolean",
                    }
                },
                "required": ["enabled"],
                "type": "object",
            },
            "trustedIps": {
                "additionalProperties": False,
                "description": "Restricts access to deployments based "
                "on the incoming request IP address",
                "nullable": True,
                "properties": {
                    "addresses": {
                        "items": {
                            "additionalProperties": False,
                            "properties": {
                                "note": {
                                    "description": "An "
                                    "optional "
                                    "note "
                                    "explaining "
                                    "what "
                                    "the "
                                    "IP "
                                    "address "
                                    "or "
                                    "subnet "
                                    "is "
                                    "used "
                                    "for",
                                    "maxLength": 20,
                                    "type": "string",
                                },
                                "value": {
                                    "description": "The "
                                    "IP "
                                    "addresses "
                                    "that "
                                    "are "
                                    "allowlisted. "
                                    "Supports "
                                    "IPv4 "
                                    "addresses "
                                    "and "
                                    "CIDR "
                                    "notations. "
                                    "IPv6 "
                                    "is "
                                    "not "
                                    "supported",
                                    "type": "string",
                                },
                            },
                            "required": ["value"],
                            "type": "object",
                        },
                        "minItems": 1,
                        "type": "array",
                    },
                    "deploymentType": {
                        "description": "Specify "
                        "if "
                        "the "
                        "Trusted "
                        "IPs "
                        "will "
                        "apply "
                        "to "
                        "every "
                        "Deployment "
                        "Target "
                        "or "
                        "just "
                        "Preview",
                        "enum": [
                            "all",
                            "preview",
                            "production",
                            "prod_deployment_urls_and_all_previews",
                            "all_except_custom_domains",
                        ],
                        "type": "string",
                    },
                    "protectionMode": {
                        "description": "exclusive: "
                        "ip "
                        "match "
                        "is "
                        "enough "
                        "to "
                        "bypass "
                        "deployment "
                        "protection "
                        "(regardless "
                        "of "
                        "other "
                        "settings). "
                        "additional: "
                        "ip "
                        "must "
                        "match "
                        "+ any "
                        "other "
                        "protection "
                        "should "
                        "be "
                        "also "
                        "provided "
                        "(password, "
                        "vercel "
                        "auth, "
                        "shareable "
                        "link, "
                        "automation "
                        "bypass "
                        "header, "
                        "automation "
                        "bypass "
                        "query "
                        "param)",
                        "enum": ["exclusive", "additional"],
                        "type": "string",
                    },
                },
                "required": ["deploymentType", "addresses", "protectionMode"],
                "type": "object",
            },
        },
        "type": "object",
    },
    "UPDATEPROJECTNETWORKLINKS_REQUEST_BODY_SCHEMA": {
        "properties": {
            "regions": {
                "items": {
                    "description": "The region of shared Secure Compute network to connect to.",
                    "example": "iad1",
                    "maxLength": 4,
                    "type": "string",
                },
                "maxItems": 3,
                "minItems": 0,
                "type": "array",
                "uniqueItems": True,
            }
        },
        "required": ["regions"],
        "type": "object",
    },
    "MOVEPROJECTDOMAIN_REQUEST_BODY_SCHEMA": {
        "properties": {
            "projectId": {
                "description": "The unique target project identifier",
                "example": "prj_XLKmu1DyR1eY7zq8UgeRKbA7yVLA",
                "oneOf": [{"type": "string"}],
            }
        },
        "required": ["projectId"],
        "type": "object",
    },
    "CREATEPROJECTENVIRONMENTVARIABLES_REQUEST_BODY_SCHEMA": {
        "oneOf": [
            {
                "anyOf": [{"required": ["target"]}, {"required": ["customEnvironmentIds"]}],
                "properties": {
                    "comment": {
                        "description": "A comment to add context on "
                        "what this environment variable "
                        "is for",
                        "example": "database connection string for production",
                        "maxLength": 500,
                        "type": "string",
                    },
                    "customEnvironmentIds": {
                        "description": "The custom "
                        "environment IDs "
                        "associated with "
                        "the environment "
                        "variable",
                        "items": {"example": "env_1234567890", "type": "string"},
                        "type": "array",
                    },
                    "gitBranch": {
                        "description": "If defined, the git branch of "
                        "the environment variable "
                        "(must have target=preview)",
                        "example": "feature-1",
                        "maxLength": 250,
                        "nullable": True,
                        "type": "string",
                    },
                    "key": {
                        "description": "The name of the environment variable",
                        "example": "API_URL",
                        "type": "string",
                    },
                    "target": {
                        "description": "The target environment of the environment variable",
                        "example": ["preview"],
                        "items": {"enum": ["production", "preview", "development"]},
                        "type": "array",
                    },
                    "type": {
                        "description": "The type of environment variable",
                        "enum": ["system", "secret", "encrypted", "plain", "sensitive"],
                        "example": "plain",
                        "type": "string",
                    },
                    "value": {
                        "description": "The value of the environment variable",
                        "example": "https://api.vercel.com",
                        "type": "string",
                    },
                },
                "required": ["key", "value", "type"],
                "type": "object",
            },
            {
                "items": {
                    "anyOf": [{"required": ["target"]}, {"required": ["customEnvironmentIds"]}],
                    "properties": {
                        "comment": {
                            "description": "A comment to add "
                            "context on what this "
                            "environment variable "
                            "is for",
                            "example": "database connection string for production",
                            "maxLength": 500,
                            "type": "string",
                        },
                        "customEnvironmentIds": {
                            "description": "The "
                            "custom "
                            "environment "
                            "IDs "
                            "associated "
                            "with the "
                            "environment "
                            "variable",
                            "items": {"example": "env_1234567890", "type": "string"},
                            "type": "array",
                        },
                        "gitBranch": {
                            "description": "If defined, the git "
                            "branch of the "
                            "environment "
                            "variable (must have "
                            "target=preview)",
                            "example": "feature-1",
                            "maxLength": 250,
                            "nullable": True,
                            "type": "string",
                        },
                        "key": {
                            "description": "The name of the environment variable",
                            "example": "API_URL",
                            "type": "string",
                        },
                        "target": {
                            "description": "The target environment of the environment variable",
                            "example": ["preview"],
                            "items": {"enum": ["production", "preview", "development"]},
                            "type": "array",
                        },
                        "type": {
                            "description": "The type of environment variable",
                            "enum": ["system", "secret", "encrypted", "plain", "sensitive"],
                            "example": "plain",
                            "type": "string",
                        },
                        "value": {
                            "description": "The value of the environment variable",
                            "example": "https://api.vercel.com",
                            "type": "string",
                        },
                    },
                    "required": ["key", "value", "type"],
                    "type": "object",
                },
                "type": "array",
            },
        ]
    },
    "EDITPROJECTENVIRONMENTVARIABLE_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "comment": {
                "description": "A comment to add context on what this env var is for",
                "example": "database connection string for production",
                "maxLength": 500,
                "type": "string",
            },
            "customEnvironmentIds": {
                "description": "The custom environments that "
                "the environment variable "
                "should be synced to",
                "items": {"example": "env_1234567890", "type": "string"},
                "type": "array",
            },
            "gitBranch": {
                "description": "If defined, the git branch of the "
                "environment variable (must have "
                "target=preview)",
                "example": "feature-1",
                "maxLength": 250,
                "nullable": True,
                "type": "string",
            },
            "key": {
                "description": "The name of the environment variable",
                "example": "GITHUB_APP_ID",
                "type": "string",
            },
            "target": {
                "description": "The target environment of the environment variable",
                "example": ["preview"],
                "items": {"enum": ["production", "preview", "development"]},
                "type": "array",
            },
            "type": {
                "description": "The type of environment variable",
                "enum": ["system", "secret", "encrypted", "plain", "sensitive"],
                "example": "plain",
                "type": "string",
            },
            "value": {
                "description": "The value of the environment variable",
                "example": "bkWIjbnxcvo78",
                "type": "string",
            },
        },
        "type": "object",
    },
    "DELETEPROJECTENVVARIABLES_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "ids": {
                "description": "Array of environment variable IDs to delete",
                "items": {"type": "string"},
                "maxItems": 1000,
                "minItems": 1,
                "type": "array",
            }
        },
        "required": ["ids"],
        "type": "object",
    },
    "UPLOADCLIENTCERTTOPROJECT_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "ca": {
                "description": "The certificate authority in PEM format",
                "example": "-----BEGIN CERTIFICATE-----\\\\n...\\\\n-----END CERTIFICATE-----",
                "type": "string",
            },
            "cert": {
                "description": "The client certificate in PEM format",
                "example": "-----BEGIN CERTIFICATE-----\\\\n...\\\\n-----END CERTIFICATE-----",
                "type": "string",
            },
            "key": {
                "description": "The private key in PEM format",
                "example": "-----BEGIN PRIVATE KEY-----\\\\n...\\\\n-----END PRIVATE KEY-----",
                "type": "string",
            },
            "origin": {
                "description": "The origin this certificate should be used "
                "for. If not specified, the certificate will "
                "be project-wide.",
                "example": "https://api.example.com",
                "type": "string",
            },
            "skipValidation": {
                "description": "Skip validation of the certificate",
                "type": "boolean",
            },
        },
        "required": ["cert", "key"],
        "type": "object",
    },
    "ADVANCEROLLOUTSTAGE_REQUEST_BODY_SCHEMA": {
        "properties": {
            "canaryDeploymentId": {
                "description": "The id of the canary deployment to approve for the next stage",
                "type": "string",
            },
            "nextStageIndex": {
                "description": "The index of the stage to transition to",
                "type": "number",
            },
        },
        "required": ["nextStageIndex", "canaryDeploymentId"],
        "type": "object",
    },
    "FORCECOMPLETEROLLINGRELEASE_REQUEST_BODY_SCHEMA": {
        "properties": {
            "canaryDeploymentId": {
                "description": "The ID of the canary deployment to complete",
                "type": "string",
            }
        },
        "required": ["canaryDeploymentId"],
        "type": "object",
    },
    "ACCEPTPROJECTTRANSFER_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "acceptedPolicies": {
                "additionalProperties": {
                    "additionalProperties": {"format": "date-time", "type": "string"},
                    "properties": {
                        "eula": {"format": "date-time", "type": "string"},
                        "privacy": {"format": "date-time", "type": "string"},
                    },
                    "required": ["eula", "privacy"],
                    "type": "object",
                },
                "type": "object",
            },
            "newProjectName": {
                "description": "The desired name for the project",
                "example": "a-project-name",
                "maxLength": 100,
                "type": "string",
            },
            "paidFeatures": {
                "additionalProperties": False,
                "properties": {
                    "concurrentBuilds": {"nullable": True, "type": "integer"},
                    "passwordProtection": {"nullable": True, "type": "boolean"},
                    "previewDeploymentSuffix": {"nullable": True, "type": "boolean"},
                },
                "type": "object",
            },
        },
        "type": "object",
    },
    "SETFIREWALLCONFIGURATION_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "botIdEnabled": {"type": "boolean"},
            "crs": {
                "additionalProperties": False,
                "description": "Custom Ruleset",
                "properties": {
                    "gen": {
                        "additionalProperties": False,
                        "description": "Generic Attack - "
                        "Provide broad "
                        "protection from various "
                        "undefined or novel "
                        "attack vectors.",
                        "properties": {
                            "action": {"enum": ["deny", "log"], "type": "string"},
                            "active": {"type": "boolean"},
                        },
                        "required": ["active", "action"],
                        "type": "object",
                    },
                    "java": {
                        "additionalProperties": False,
                        "description": "Java Attack - Mitigate "
                        "risks of exploitation "
                        "targeting Java-based "
                        "applications or "
                        "components.",
                        "properties": {
                            "action": {"enum": ["deny", "log"], "type": "string"},
                            "active": {"type": "boolean"},
                        },
                        "required": ["active", "action"],
                        "type": "object",
                    },
                    "lfi": {
                        "additionalProperties": False,
                        "description": "Local File Inclusion "
                        "Attack - Prevent "
                        "unauthorized access to "
                        "local files through web "
                        "applications.",
                        "properties": {
                            "action": {"enum": ["deny", "log"], "type": "string"},
                            "active": {"type": "boolean"},
                        },
                        "required": ["active", "action"],
                        "type": "object",
                    },
                    "ma": {
                        "additionalProperties": False,
                        "description": "Multipart Attack - Block "
                        "attempts to bypass "
                        "security controls using "
                        "multipart/form-data "
                        "encoding.",
                        "properties": {
                            "action": {"enum": ["deny", "log"], "type": "string"},
                            "active": {"type": "boolean"},
                        },
                        "required": ["active", "action"],
                        "type": "object",
                    },
                    "php": {
                        "additionalProperties": False,
                        "description": "PHP Attack - Safeguard "
                        "against vulnerability "
                        "exploits in PHP-based "
                        "applications.",
                        "properties": {
                            "action": {"enum": ["deny", "log"], "type": "string"},
                            "active": {"type": "boolean"},
                        },
                        "required": ["active", "action"],
                        "type": "object",
                    },
                    "rce": {
                        "additionalProperties": False,
                        "description": "Remote Execution Attack "
                        "- Prevent unauthorized "
                        "execution of remote "
                        "scripts or commands.",
                        "properties": {
                            "action": {"enum": ["deny", "log"], "type": "string"},
                            "active": {"type": "boolean"},
                        },
                        "required": ["active", "action"],
                        "type": "object",
                    },
                    "rfi": {
                        "additionalProperties": False,
                        "description": "Remote File Inclusion "
                        "Attack - Prohibit "
                        "unauthorized upload or "
                        "execution of remote "
                        "files.",
                        "properties": {
                            "action": {"enum": ["deny", "log"], "type": "string"},
                            "active": {"type": "boolean"},
                        },
                        "required": ["active", "action"],
                        "type": "object",
                    },
                    "sd": {
                        "additionalProperties": False,
                        "description": "Scanner Detection - "
                        "Detect and prevent "
                        "reconnaissance "
                        "activities from network "
                        "scanning tools.",
                        "properties": {
                            "action": {"enum": ["deny", "log"], "type": "string"},
                            "active": {"type": "boolean"},
                        },
                        "required": ["active", "action"],
                        "type": "object",
                    },
                    "sf": {
                        "additionalProperties": False,
                        "description": "Session Fixation Attack "
                        "- Prevent unauthorized "
                        "takeover of user "
                        "sessions by enforcing "
                        "unique session IDs.",
                        "properties": {
                            "action": {"enum": ["deny", "log"], "type": "string"},
                            "active": {"type": "boolean"},
                        },
                        "required": ["active", "action"],
                        "type": "object",
                    },
                    "sqli": {
                        "additionalProperties": False,
                        "description": "SQL Injection Attack - "
                        "Prohibit unauthorized "
                        "use of SQL commands to "
                        "manipulate databases.",
                        "properties": {
                            "action": {"enum": ["deny", "log"], "type": "string"},
                            "active": {"type": "boolean"},
                        },
                        "required": ["active", "action"],
                        "type": "object",
                    },
                    "xss": {
                        "additionalProperties": False,
                        "description": "XSS Attack - Prevent "
                        "injection of malicious "
                        "scripts into trusted "
                        "webpages.",
                        "properties": {
                            "action": {"enum": ["deny", "log"], "type": "string"},
                            "active": {"type": "boolean"},
                        },
                        "required": ["active", "action"],
                        "type": "object",
                    },
                },
                "type": "object",
            },
            "firewallEnabled": {"type": "boolean"},
            "ips": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "action": {
                            "enum": ["deny", "challenge", "log", "bypass"],
                            "type": "string",
                        },
                        "hostname": {"type": "string"},
                        "id": {"type": "string"},
                        "ip": {"type": "string"},
                        "notes": {"type": "string"},
                    },
                    "required": ["hostname", "ip", "action"],
                    "type": "object",
                },
                "type": "array",
            },
            "managedRules": {"additionalProperties": {"anyOf": []}, "type": "object"},
            "rules": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "action": {
                            "additionalProperties": False,
                            "properties": {
                                "mitigate": {
                                    "additionalProperties": False,
                                    "properties": {
                                        "action": {
                                            "enum": [
                                                "log",
                                                "challenge",
                                                "deny",
                                                "bypass",
                                                "rate_limit",
                                                "redirect",
                                            ],
                                            "type": "string",
                                        },
                                        "actionDuration": {"nullable": True, "type": "string"},
                                        "bypassSystem": {"nullable": True, "type": "boolean"},
                                        "rateLimit": {
                                            "anyOf": [
                                                {
                                                    "additionalProperties": False,
                                                    "properties": {
                                                        "action": {
                                                            "anyOf": [
                                                                {
                                                                    "enum": [
                                                                        "log",
                                                                        "challenge",
                                                                        "deny",
                                                                        "rate_limit",
                                                                    ],
                                                                    "type": "string",
                                                                },
                                                                {},
                                                            ],
                                                            "nullable": True,
                                                        },
                                                        "algo": {
                                                            "enum": [
                                                                "fixed_window",
                                                                "token_bucket",
                                                            ],
                                                            "type": "string",
                                                        },
                                                        "keys": {
                                                            "items": {"type": "string"},
                                                            "type": "array",
                                                        },
                                                        "limit": {"type": "number"},
                                                        "window": {"type": "number"},
                                                    },
                                                    "required": ["algo", "window", "limit", "keys"],
                                                    "type": "object",
                                                },
                                                {},
                                            ],
                                            "nullable": True,
                                        },
                                        "redirect": {
                                            "anyOf": [
                                                {
                                                    "additionalProperties": False,
                                                    "properties": {
                                                        "location": {"type": "string"},
                                                        "permanent": {"type": "boolean"},
                                                    },
                                                    "required": ["location", "permanent"],
                                                    "type": "object",
                                                },
                                                {},
                                            ],
                                            "nullable": True,
                                        },
                                    },
                                    "required": ["action"],
                                    "type": "object",
                                }
                            },
                            "type": "object",
                        },
                        "active": {"type": "boolean"},
                        "conditionGroup": {
                            "items": {
                                "additionalProperties": False,
                                "properties": {
                                    "conditions": {
                                        "items": {
                                            "additionalProperties": False,
                                            "properties": {
                                                "key": {"type": "string"},
                                                "neg": {"type": "boolean"},
                                                "op": {
                                                    "enum": [
                                                        "re",
                                                        "eq",
                                                        "neq",
                                                        "ex",
                                                        "nex",
                                                        "inc",
                                                        "ninc",
                                                        "pre",
                                                        "suf",
                                                        "sub",
                                                        "gt",
                                                        "gte",
                                                        "lt",
                                                        "lte",
                                                    ],
                                                    "type": "string",
                                                },
                                                "type": {
                                                    "description": "[Parameter](https://vercel.com/docs/security/vercel-waf/rule-configuration#parameters) "
                                                    "from "
                                                    "the "
                                                    "incoming "
                                                    "traffic.",
                                                    "enum": [
                                                        "host",
                                                        "path",
                                                        "method",
                                                        "header",
                                                        "query",
                                                        "cookie",
                                                        "target_path",
                                                        "route",
                                                        "raw_path",
                                                        "ip_address",
                                                        "region",
                                                        "protocol",
                                                        "scheme",
                                                        "environment",
                                                        "user_agent",
                                                        "geo_continent",
                                                        "geo_country",
                                                        "geo_country_region",
                                                        "geo_city",
                                                        "geo_as_number",
                                                        "ja4_digest",
                                                        "ja3_digest",
                                                        "rate_limit_api_id",
                                                    ],
                                                    "type": "string",
                                                },
                                                "value": {
                                                    "anyOf": [
                                                        {"type": "string"},
                                                        {
                                                            "items": {"type": "string"},
                                                            "maxItems": 75,
                                                            "type": "array",
                                                        },
                                                        {"type": "number"},
                                                    ]
                                                },
                                            },
                                            "required": ["type", "op"],
                                            "type": "object",
                                        },
                                        "maxItems": 65,
                                        "type": "array",
                                    }
                                },
                                "required": ["conditions"],
                                "type": "object",
                            },
                            "maxItems": 25,
                            "type": "array",
                        },
                        "description": {"maxLength": 256, "type": "string"},
                        "id": {"type": "string"},
                        "name": {"maxLength": 160, "type": "string"},
                    },
                    "required": ["name", "active", "conditionGroup", "action"],
                    "type": "object",
                },
                "type": "array",
            },
        },
        "required": ["firewallEnabled"],
        "type": "object",
    },
    "UPDATEFIREWALLCONFIG_REQUEST_BODY_SCHEMA": {
        "oneOf": [
            {
                "additionalProperties": False,
                "description": "Enable Firewall",
                "properties": {
                    "action": {"enum": ["firewallEnabled"], "type": "string"},
                    "id": {"nullable": True},
                    "value": {"type": "boolean"},
                },
                "required": ["action", "value"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "description": "Add a custom rule",
                "properties": {
                    "action": {"enum": ["rules.insert"], "type": "string"},
                    "id": {"nullable": True},
                    "value": {
                        "additionalProperties": False,
                        "properties": {
                            "action": {
                                "additionalProperties": False,
                                "properties": {
                                    "mitigate": {
                                        "additionalProperties": False,
                                        "properties": {
                                            "action": {
                                                "enum": [
                                                    "log",
                                                    "challenge",
                                                    "deny",
                                                    "bypass",
                                                    "rate_limit",
                                                    "redirect",
                                                ],
                                                "type": "string",
                                            },
                                            "actionDuration": {"nullable": True, "type": "string"},
                                            "bypassSystem": {"nullable": True, "type": "boolean"},
                                            "rateLimit": {
                                                "anyOf": [
                                                    {
                                                        "additionalProperties": False,
                                                        "properties": {
                                                            "action": {
                                                                "anyOf": [
                                                                    {
                                                                        "enum": [
                                                                            "log",
                                                                            "challenge",
                                                                            "deny",
                                                                            "rate_limit",
                                                                        ],
                                                                        "type": "string",
                                                                    },
                                                                    {},
                                                                ],
                                                                "nullable": True,
                                                            },
                                                            "algo": {
                                                                "enum": [
                                                                    "fixed_window",
                                                                    "token_bucket",
                                                                ],
                                                                "type": "string",
                                                            },
                                                            "keys": {
                                                                "items": {"type": "string"},
                                                                "type": "array",
                                                            },
                                                            "limit": {"type": "number"},
                                                            "window": {"type": "number"},
                                                        },
                                                        "required": [
                                                            "algo",
                                                            "window",
                                                            "limit",
                                                            "keys",
                                                        ],
                                                        "type": "object",
                                                    },
                                                    {},
                                                ],
                                                "nullable": True,
                                            },
                                            "redirect": {
                                                "anyOf": [
                                                    {
                                                        "additionalProperties": False,
                                                        "properties": {
                                                            "location": {"type": "string"},
                                                            "permanent": {"type": "boolean"},
                                                        },
                                                        "required": ["location", "permanent"],
                                                        "type": "object",
                                                    },
                                                    {},
                                                ],
                                                "nullable": True,
                                            },
                                        },
                                        "required": ["action"],
                                        "type": "object",
                                    }
                                },
                                "type": "object",
                            },
                            "active": {"type": "boolean"},
                            "conditionGroup": {
                                "items": {
                                    "additionalProperties": False,
                                    "properties": {
                                        "conditions": {
                                            "items": {
                                                "additionalProperties": False,
                                                "properties": {
                                                    "key": {"type": "string"},
                                                    "neg": {"type": "boolean"},
                                                    "op": {
                                                        "enum": [
                                                            "re",
                                                            "eq",
                                                            "neq",
                                                            "ex",
                                                            "nex",
                                                            "inc",
                                                            "ninc",
                                                            "pre",
                                                            "suf",
                                                            "sub",
                                                            "gt",
                                                            "gte",
                                                            "lt",
                                                            "lte",
                                                        ],
                                                        "type": "string",
                                                    },
                                                    "type": {
                                                        "enum": [
                                                            "host",
                                                            "path",
                                                            "method",
                                                            "header",
                                                            "query",
                                                            "cookie",
                                                            "target_path",
                                                            "route",
                                                            "raw_path",
                                                            "ip_address",
                                                            "region",
                                                            "protocol",
                                                            "scheme",
                                                            "environment",
                                                            "user_agent",
                                                            "geo_continent",
                                                            "geo_country",
                                                            "geo_country_region",
                                                            "geo_city",
                                                            "geo_as_number",
                                                            "ja4_digest",
                                                            "ja3_digest",
                                                            "rate_limit_api_id",
                                                            "server_action",
                                                        ],
                                                        "type": "string",
                                                    },
                                                    "value": {
                                                        "oneOf": [
                                                            {"type": "string"},
                                                            {
                                                                "items": {"type": "string"},
                                                                "maxItems": 75,
                                                                "type": "array",
                                                            },
                                                            {"type": "number"},
                                                        ]
                                                    },
                                                },
                                                "required": ["type", "op"],
                                                "type": "object",
                                            },
                                            "maxItems": 65,
                                            "type": "array",
                                        }
                                    },
                                    "required": ["conditions"],
                                    "type": "object",
                                },
                                "maxItems": 25,
                                "type": "array",
                            },
                            "description": {"maxLength": 256, "type": "string"},
                            "name": {"maxLength": 160, "type": "string"},
                        },
                        "required": ["name", "active", "conditionGroup", "action"],
                        "type": "object",
                    },
                },
                "required": ["action", "value"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "description": "Update a custom rule",
                "properties": {
                    "action": {"enum": ["rules.update"], "type": "string"},
                    "id": {"type": "string"},
                    "value": {
                        "additionalProperties": False,
                        "properties": {
                            "action": {
                                "additionalProperties": False,
                                "properties": {
                                    "mitigate": {
                                        "additionalProperties": False,
                                        "properties": {
                                            "action": {
                                                "enum": [
                                                    "log",
                                                    "challenge",
                                                    "deny",
                                                    "bypass",
                                                    "rate_limit",
                                                    "redirect",
                                                ],
                                                "type": "string",
                                            },
                                            "actionDuration": {"nullable": True, "type": "string"},
                                            "bypassSystem": {"nullable": True, "type": "boolean"},
                                            "rateLimit": {
                                                "anyOf": [
                                                    {
                                                        "additionalProperties": False,
                                                        "properties": {
                                                            "action": {
                                                                "anyOf": [
                                                                    {
                                                                        "enum": [
                                                                            "log",
                                                                            "challenge",
                                                                            "deny",
                                                                            "rate_limit",
                                                                        ],
                                                                        "type": "string",
                                                                    },
                                                                    {},
                                                                ],
                                                                "nullable": True,
                                                            },
                                                            "algo": {
                                                                "enum": [
                                                                    "fixed_window",
                                                                    "token_bucket",
                                                                ],
                                                                "type": "string",
                                                            },
                                                            "keys": {
                                                                "items": {"type": "string"},
                                                                "type": "array",
                                                            },
                                                            "limit": {"type": "number"},
                                                            "window": {"type": "number"},
                                                        },
                                                        "required": [
                                                            "algo",
                                                            "window",
                                                            "limit",
                                                            "keys",
                                                        ],
                                                        "type": "object",
                                                    },
                                                    {},
                                                ],
                                                "nullable": True,
                                            },
                                            "redirect": {
                                                "anyOf": [
                                                    {
                                                        "additionalProperties": False,
                                                        "properties": {
                                                            "location": {"type": "string"},
                                                            "permanent": {"type": "boolean"},
                                                        },
                                                        "required": ["location", "permanent"],
                                                        "type": "object",
                                                    },
                                                    {},
                                                ],
                                                "nullable": True,
                                            },
                                        },
                                        "required": ["action"],
                                        "type": "object",
                                    }
                                },
                                "type": "object",
                            },
                            "active": {"type": "boolean"},
                            "conditionGroup": {
                                "items": {
                                    "additionalProperties": False,
                                    "properties": {
                                        "conditions": {
                                            "items": {
                                                "additionalProperties": False,
                                                "properties": {
                                                    "key": {"type": "string"},
                                                    "neg": {"type": "boolean"},
                                                    "op": {
                                                        "enum": [
                                                            "re",
                                                            "eq",
                                                            "neq",
                                                            "ex",
                                                            "nex",
                                                            "inc",
                                                            "ninc",
                                                            "pre",
                                                            "suf",
                                                            "sub",
                                                            "gt",
                                                            "gte",
                                                            "lt",
                                                            "lte",
                                                        ],
                                                        "type": "string",
                                                    },
                                                    "type": {
                                                        "enum": [
                                                            "host",
                                                            "path",
                                                            "method",
                                                            "header",
                                                            "query",
                                                            "cookie",
                                                            "target_path",
                                                            "route",
                                                            "raw_path",
                                                            "ip_address",
                                                            "region",
                                                            "protocol",
                                                            "scheme",
                                                            "environment",
                                                            "user_agent",
                                                            "geo_continent",
                                                            "geo_country",
                                                            "geo_country_region",
                                                            "geo_city",
                                                            "geo_as_number",
                                                            "ja4_digest",
                                                            "ja3_digest",
                                                            "rate_limit_api_id",
                                                            "server_action",
                                                        ],
                                                        "type": "string",
                                                    },
                                                    "value": {
                                                        "anyOf": [
                                                            {"type": "string"},
                                                            {
                                                                "items": {"type": "string"},
                                                                "maxItems": 75,
                                                                "type": "array",
                                                            },
                                                            {"type": "number"},
                                                        ]
                                                    },
                                                },
                                                "required": ["type", "op"],
                                                "type": "object",
                                            },
                                            "maxItems": 65,
                                            "type": "array",
                                        }
                                    },
                                    "required": ["conditions"],
                                    "type": "object",
                                },
                                "maxItems": 25,
                                "type": "array",
                            },
                            "description": {"maxLength": 256, "type": "string"},
                            "name": {"maxLength": 160, "type": "string"},
                        },
                        "required": ["name", "active", "conditionGroup", "action"],
                        "type": "object",
                    },
                },
                "required": ["action", "id", "value"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "description": "Remove a custom rule",
                "properties": {
                    "action": {"enum": ["rules.remove"], "type": "string"},
                    "id": {"type": "string"},
                    "value": {"nullable": True},
                },
                "required": ["action", "id"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "description": "Reorder a custom rule",
                "properties": {
                    "action": {"enum": ["rules.priority"], "type": "string"},
                    "id": {"type": "string"},
                    "value": {"type": "number"},
                },
                "required": ["action", "id", "value"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "description": "Enable a managed rule",
                "properties": {
                    "action": {"enum": ["crs.update"], "type": "string"},
                    "id": {
                        "enum": [
                            "sd",
                            "ma",
                            "lfi",
                            "rfi",
                            "rce",
                            "php",
                            "gen",
                            "xss",
                            "sqli",
                            "sf",
                            "java",
                        ],
                        "type": "string",
                    },
                    "value": {
                        "additionalProperties": False,
                        "properties": {
                            "action": {"enum": ["deny", "log"], "type": "string"},
                            "active": {"type": "boolean"},
                        },
                        "required": ["active", "action"],
                        "type": "object",
                    },
                },
                "required": ["action", "id", "value"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "description": "Disable a managed rule",
                "properties": {
                    "action": {"enum": ["crs.disable"], "type": "string"},
                    "id": {"nullable": True},
                    "value": {"nullable": True},
                },
                "required": ["action"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "description": "Add an IP Blocking rule",
                "properties": {
                    "action": {"enum": ["ip.insert"], "type": "string"},
                    "id": {"nullable": True},
                    "value": {
                        "additionalProperties": False,
                        "properties": {
                            "action": {
                                "enum": ["deny", "challenge", "log", "bypass"],
                                "type": "string",
                            },
                            "hostname": {"type": "string"},
                            "ip": {"type": "string"},
                            "notes": {"type": "string"},
                        },
                        "required": ["hostname", "ip", "action"],
                        "type": "object",
                    },
                },
                "required": ["action", "value"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "description": "Update an IP Blocking rule",
                "properties": {
                    "action": {"enum": ["ip.update"], "type": "string"},
                    "id": {"type": "string"},
                    "value": {
                        "additionalProperties": False,
                        "properties": {
                            "action": {
                                "enum": ["deny", "challenge", "log", "bypass"],
                                "type": "string",
                            },
                            "hostname": {"type": "string"},
                            "ip": {"type": "string"},
                            "notes": {"type": "string"},
                        },
                        "required": ["hostname", "ip", "action"],
                        "type": "object",
                    },
                },
                "required": ["action", "id", "value"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "description": "Remove an IP Blocking rule",
                "properties": {
                    "action": {"enum": ["ip.remove"], "type": "string"},
                    "id": {"type": "string"},
                    "value": {"nullable": True},
                },
                "required": ["action", "id"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "description": "Update a managed ruleset",
                "properties": {
                    "action": {"enum": ["managedRules.update"], "type": "string"},
                    "id": {
                        "enum": ["ai_bots", "bot_filter", "bot_protection", "owasp"],
                        "type": "string",
                    },
                    "value": {
                        "additionalProperties": False,
                        "properties": {
                            "action": {"enum": ["log", "challenge", "deny"], "type": "string"},
                            "active": {"type": "boolean"},
                        },
                        "required": ["active"],
                        "type": "object",
                    },
                },
                "required": ["action", "id", "value"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "description": "Update a managed rule group",
                "properties": {
                    "action": {"type": "string"},
                    "id": {
                        "enum": ["ai_bots", "bot_filter", "bot_protection", "owasp"],
                        "type": "string",
                    },
                    "value": {
                        "additionalProperties": {
                            "additionalProperties": False,
                            "properties": {
                                "action": {"enum": ["log", "challenge", "deny"], "type": "string"},
                                "active": {"type": "boolean"},
                            },
                            "required": ["active"],
                            "type": "object",
                        },
                        "type": "object",
                    },
                },
                "required": ["action", "id", "value"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "description": "Toggle bot ID",
                "properties": {
                    "action": {"type": "string"},
                    "id": {"type": "string"},
                    "value": {"type": "boolean"},
                },
                "required": ["action", "value"],
                "type": "object",
            },
        ]
    },
    "CREATEFIREWALLBYPASSRULE_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "oneOf": [{"required": ["domain"]}, {"required": ["projectScope"]}],
        "properties": {
            "allSources": {"type": "boolean"},
            "domain": {"maxLength": 2544, "pattern": "([a-z]+[a-z.]+)$", "type": "string"},
            "note": {"maxLength": 500, "type": "string"},
            "projectScope": {
                "description": "If the specified bypass will apply to all domains for a project.",
                "type": "boolean",
            },
            "sourceIp": {"type": "string"},
            "ttl": {"description": "Time to live in milliseconds", "type": "number"},
        },
        "type": "object",
    },
    "REMOVEBYPASSRULE_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "oneOf": [{"required": ["domain"]}, {"required": ["projectScope"]}],
        "properties": {
            "allSources": {"type": "boolean"},
            "domain": {"maxLength": 2544, "pattern": "([a-z]+[a-z.]+)$", "type": "string"},
            "note": {"maxLength": 500, "type": "string"},
            "projectScope": {"type": "boolean"},
            "sourceIp": {"type": "string"},
        },
        "type": "object",
    },
    "CREATEINTEGRATIONSTORE_REQUEST_BODY_SCHEMA": {
        "properties": {
            "billingPlanId": {
                "description": "ID of the billing plan for paid "
                "resources. Get available plans from "
                "GET "
                "/integrations/integration/{id}/products/{productId}/plans. "
                "If not provided, automatically "
                "discovers free billing plans.",
                "example": "bp_abc123def456",
                "type": "string",
            },
            "externalId": {
                "description": "Optional external identifier for tracking purposes",
                "example": "dev-db-001",
                "type": "string",
            },
            "integrationConfigurationId": {
                "description": "ID of your integration "
                "configuration. Get this "
                "from GET "
                "/v1/integrations/configurations",
                "example": "icfg_cuwj0AdCdH3BwWT4LPijCC7t",
                "pattern": "^icfg_[a-zA-Z0-9]+$",
                "type": "string",
            },
            "integrationProductIdOrSlug": {
                "description": "ID or slug of the "
                "integration product. "
                "Get available products "
                "from GET "
                "/v1/integrations/configuration/{id}/products",
                "example": "iap_postgres_db",
                "oneOf": [
                    {"description": "Product ID format", "pattern": "^iap_[a-zA-Z0-9_]+$"},
                    {"description": "Product slug format", "pattern": "^[a-z0-9-]+$"},
                ],
                "type": "string",
            },
            "metadata": {
                "additionalProperties": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "number"},
                        {"type": "boolean"},
                        {"items": {"type": "string"}, "type": "array"},
                        {"items": {"type": "number"}, "type": "array"},
                    ]
                },
                "description": "Optional key-value pairs for resource metadata",
                "example": {
                    "environment": "development",
                    "project": "my-app",
                    "tags": ["database", "postgres"],
                },
                "type": "object",
            },
            "name": {
                "description": "Human-readable name for the storage resource",
                "example": "my-dev-database",
                "maxLength": 128,
                "type": "string",
            },
            "paymentMethodId": {
                "description": "Payment method ID for paid "
                "resources. Optional - uses default "
                "payment method if not provided.",
                "example": "pm_1AbcDefGhiJklMno",
                "type": "string",
            },
            "prepaymentAmountCents": {
                "description": "Amount in cents for "
                "prepayment billing plans. "
                "Required only for prepayment "
                "plans with variable amounts.",
                "example": 5000,
                "minimum": 50,
                "type": "number",
            },
            "protocolSettings": {
                "additionalProperties": True,
                "description": "Protocol-specific configuration settings",
                "example": {"experimentation": {"edgeConfigSyncingEnabled": True}},
                "type": "object",
            },
            "source": {
                "default": "marketplace",
                "description": "Source of the store creation request",
                "example": "api",
                "type": "string",
            },
        },
        "required": ["name", "integrationConfigurationId", "integrationProductIdOrSlug"],
        "type": "object",
    },
    "INVITEUSERTOTEAM_REQUEST_BODY_SCHEMA": {
        "properties": {
            "email": {
                "description": "The email address of the user to invite",
                "example": "john@example.com",
                "format": "email",
                "type": "string",
            },
            "projects": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "projectId": {
                            "description": "The ID of the project.",
                            "example": "prj_ndlgr43fadlPyCtREAqxxdyFK",
                            "maxLength": 64,
                            "type": "string",
                        },
                        "role": {
                            "description": "Sets the project roles for the invited user",
                            "enum": ["ADMIN", "PROJECT_VIEWER", "PROJECT_DEVELOPER"],
                            "example": "ADMIN",
                            "type": "string",
                        },
                    },
                    "required": ["role", "projectId"],
                    "type": "object",
                },
                "type": "array",
            },
            "role": {
                "default": "MEMBER",
                "description": "The role of the user to invite",
                "enum": [
                    "OWNER",
                    "MEMBER",
                    "DEVELOPER",
                    "SECURITY",
                    "BILLING",
                    "VIEWER",
                    "VIEWER_FOR_PLUS",
                    "CONTRIBUTOR",
                ],
                "example": [
                    "OWNER",
                    "MEMBER",
                    "DEVELOPER",
                    "SECURITY",
                    "BILLING",
                    "VIEWER",
                    "VIEWER_FOR_PLUS",
                    "CONTRIBUTOR",
                ],
                "type": "string",
            },
        },
        "required": ["email"],
        "type": "object",
    },
    "REQUESTTEAMACCESS_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "joinedFrom": {
                "additionalProperties": False,
                "properties": {
                    "commitId": {
                        "description": "The commit sha if the origin is a git provider.",
                        "example": "f498d25d8bd654b578716203be73084b31130cd7",
                        "type": "string",
                    },
                    "gitUserId": {
                        "description": "The ID of the Git account of the user who requests access.",
                        "example": 103053343,
                        "oneOf": [{"type": "string"}, {"type": "number"}],
                    },
                    "gitUserLogin": {
                        "description": "The "
                        "login "
                        "name "
                        "for the "
                        "Git "
                        "account "
                        "of the "
                        "user "
                        "who "
                        "requests "
                        "access.",
                        "example": "jane-doe",
                        "type": "string",
                    },
                    "origin": {
                        "description": "The origin of the request.",
                        "enum": [
                            "import",
                            "teams",
                            "github",
                            "gitlab",
                            "bitbucket",
                            "feedback",
                            "organization-teams",
                        ],
                        "example": "github",
                        "type": "string",
                    },
                    "repoId": {
                        "description": "The ID of the repository for the given Git provider.",
                        "example": "67753070",
                        "type": "string",
                    },
                    "repoPath": {
                        "description": "The path to the repository for the given Git provider.",
                        "example": "jane-doe/example",
                        "type": "string",
                    },
                },
                "required": ["origin"],
                "type": "object",
            }
        },
        "required": ["joinedFrom"],
        "type": "object",
    },
    "UPDATETEAMMEMBER_REQUEST_BODY_SCHEMA": {
        "properties": {
            "confirmed": {
                "description": "Accept a user who requested access to the team.",
                "enum": [True],
                "example": True,
                "type": "boolean",
            },
            "joinedFrom": {
                "additionalProperties": False,
                "properties": {"ssoUserId": {"nullable": True}},
                "type": "object",
            },
            "projects": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "projectId": {
                            "description": "The ID of the project.",
                            "example": "prj_ndlgr43fadlPyCtREAqxxdyFK",
                            "maxLength": 256,
                            "type": "string",
                        },
                        "role": {
                            "description": "The "
                            "project "
                            "role of "
                            "the "
                            "member "
                            "that "
                            "will be "
                            "added. "
                            '\\"null\\" '
                            "will "
                            "remove "
                            "this "
                            "project "
                            "level "
                            "role.",
                            "enum": ["ADMIN", "PROJECT_VIEWER", "PROJECT_DEVELOPER", None],
                            "example": "ADMIN",
                            "nullable": True,
                            "type": "string",
                        },
                    },
                    "required": ["role", "projectId"],
                    "type": "object",
                },
                "type": "array",
            },
            "role": {
                "default": "MEMBER",
                "description": "The role in the team of the member.",
                "example": ["MEMBER", "VIEWER"],
                "type": "string",
            },
        },
        "type": "object",
    },
    "UPDATETEAMINFO_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "avatar": {
                "description": "The hash value of an uploaded image.",
                "format": "regex",
                "type": "string",
            },
            "defaultDeploymentProtection": {
                "additionalProperties": False,
                "description": "Default deployment protection settings for new projects.",
                "properties": {
                    "passwordProtection": {
                        "additionalProperties": False,
                        "description": "Allows to protect project deployments with a password",
                        "nullable": True,
                        "properties": {
                            "deploymentType": {
                                "description": "Specify "
                                "if "
                                "the "
                                "password "
                                "will "
                                "apply "
                                "to "
                                "every "
                                "Deployment "
                                "Target "
                                "or "
                                "just "
                                "Preview",
                                "enum": [
                                    "all",
                                    "preview",
                                    "prod_deployment_urls_and_all_previews",
                                    "all_except_custom_domains",
                                ],
                                "type": "string",
                            },
                            "password": {
                                "description": "The "
                                "password "
                                "that "
                                "will "
                                "be "
                                "used "
                                "to "
                                "protect "
                                "Project "
                                "Deployments",
                                "maxLength": 72,
                                "nullable": True,
                                "type": "string",
                            },
                        },
                        "required": ["deploymentType"],
                        "type": "object",
                    },
                    "ssoProtection": {
                        "additionalProperties": False,
                        "description": "Ensures "
                        "visitors "
                        "to "
                        "your "
                        "Preview "
                        "Deployments "
                        "are "
                        "logged "
                        "into "
                        "Vercel "
                        "and "
                        "have "
                        "a "
                        "minimum "
                        "of "
                        "Viewer "
                        "access "
                        "on "
                        "your "
                        "team",
                        "nullable": True,
                        "properties": {
                            "deploymentType": {
                                "default": "preview",
                                "description": "Specify "
                                "if "
                                "the "
                                "Vercel "
                                "Authentication "
                                "(SSO "
                                "Protection) "
                                "will "
                                "apply "
                                "to "
                                "every "
                                "Deployment "
                                "Target "
                                "or "
                                "just "
                                "Preview",
                                "enum": [
                                    "all",
                                    "preview",
                                    "prod_deployment_urls_and_all_previews",
                                    "all_except_custom_domains",
                                ],
                                "type": "string",
                            }
                        },
                        "required": ["deploymentType"],
                        "type": "object",
                    },
                },
                "type": "object",
            },
            "defaultExpirationSettings": {
                "additionalProperties": False,
                "properties": {
                    "expiration": {
                        "description": "The time period to keep non-production deployments for",
                        "enum": [
                            "3y",
                            "2y",
                            "1y",
                            "6m",
                            "3m",
                            "2m",
                            "1m",
                            "2w",
                            "1w",
                            "1d",
                            "unlimited",
                        ],
                        "example": "1y",
                        "type": "string",
                    },
                    "expirationCanceled": {
                        "description": "The time period to keep canceled deployments for",
                        "enum": ["1y", "6m", "3m", "2m", "1m", "2w", "1w", "1d", "unlimited"],
                        "example": "1y",
                        "type": "string",
                    },
                    "expirationErrored": {
                        "description": "The time period to keep errored deployments for",
                        "enum": ["1y", "6m", "3m", "2m", "1m", "2w", "1w", "1d", "unlimited"],
                        "example": "1y",
                        "type": "string",
                    },
                    "expirationProduction": {
                        "description": "The time period to keep production deployments for",
                        "enum": [
                            "3y",
                            "2y",
                            "1y",
                            "6m",
                            "3m",
                            "2m",
                            "1m",
                            "2w",
                            "1w",
                            "1d",
                            "unlimited",
                        ],
                        "example": "1y",
                        "type": "string",
                    },
                },
                "type": "object",
            },
            "description": {
                "description": "A short text that describes the team.",
                "example": "Our mission is to make cloud computing accessible to everyone",
                "maxLength": 140,
                "type": "string",
            },
            "emailDomain": {
                "example": "example.com",
                "format": "regex",
                "nullable": True,
                "type": "string",
            },
            "enablePreviewFeedback": {
                "description": "Enable preview toolbar: one of on, off or default.",
                "example": "on",
                "type": "string",
            },
            "enableProductionFeedback": {
                "description": "Enable production toolbar: one of on, off or default.",
                "example": "on",
                "type": "string",
            },
            "hideIpAddresses": {
                "description": "Display or hide IP addresses in Monitoring queries.",
                "example": False,
                "type": "boolean",
            },
            "hideIpAddressesInLogDrains": {
                "description": "Display or hide IP addresses in Log Drains.",
                "example": False,
                "type": "boolean",
            },
            "name": {
                "description": "The name of the team.",
                "example": "My Team",
                "maxLength": 256,
                "type": "string",
            },
            "previewDeploymentSuffix": {
                "description": "Suffix that will be used for all preview deployments.",
                "example": "example.dev",
                "format": "hostname",
                "nullable": True,
                "type": "string",
            },
            "regenerateInviteCode": {
                "description": "Create a new invite code and replace the current one.",
                "example": True,
                "type": "boolean",
            },
            "remoteCaching": {
                "additionalProperties": False,
                "description": "Whether or not remote caching is enabled for the team",
                "properties": {
                    "enabled": {
                        "description": "Enable or disable remote caching for the team.",
                        "example": True,
                        "type": "boolean",
                    }
                },
                "type": "object",
            },
            "saml": {
                "additionalProperties": False,
                "properties": {
                    "enforced": {
                        "description": "Require that members of the team use SAML Single Sign-On.",
                        "example": True,
                        "type": "boolean",
                    },
                    "roles": {
                        "additionalProperties": {
                            "anyOf": [
                                {
                                    "enum": [
                                        "OWNER",
                                        "MEMBER",
                                        "DEVELOPER",
                                        "SECURITY",
                                        "BILLING",
                                        "VIEWER",
                                        "VIEWER_FOR_PLUS",
                                        "CONTRIBUTOR",
                                    ],
                                    "type": "string",
                                },
                                {
                                    "additionalProperties": False,
                                    "properties": {
                                        "accessGroupId": {
                                            "pattern": "^ag_[A-z0-9_ -]+$",
                                            "type": "string",
                                        }
                                    },
                                    "required": ["accessGroupId"],
                                    "type": "object",
                                },
                            ]
                        },
                        "description": "Directory groups to role or access group mappings.",
                        "type": "object",
                    },
                },
                "type": "object",
            },
            "sensitiveEnvironmentVariablePolicy": {
                "description": "Sensitive environment variable policy: one of on, off or default.",
                "example": "on",
                "type": "string",
            },
            "slug": {
                "description": "A new slug for the team.",
                "example": "my-team",
                "type": "string",
            },
        },
        "type": "object",
    },
    "DELETETEAM_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "reasons": {
                "description": "Optional array of objects that describe "
                "the reason why the team is being deleted.",
                "items": {
                    "additionalProperties": False,
                    "description": "An object describing the reason why the team is being deleted.",
                    "properties": {
                        "description": {
                            "description": "Description "
                            "of "
                            "the "
                            "reason "
                            "why "
                            "the "
                            "team "
                            "is "
                            "being "
                            "deleted.",
                            "type": "string",
                        },
                        "slug": {
                            "description": "Idenitifier "
                            "slug of "
                            "the "
                            "reason "
                            "why the "
                            "team is "
                            "being "
                            "deleted.",
                            "type": "string",
                        },
                    },
                    "required": ["slug", "description"],
                    "type": "object",
                },
                "type": "array",
            }
        },
        "type": "object",
    },
    "INITIATEUSERDELETION_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "reasons": {
                "description": "Optional array of objects that describe "
                "the reason why the User account is being "
                "deleted.",
                "items": {
                    "additionalProperties": False,
                    "description": "An object describing the reason "
                    "why the User account is being "
                    "deleted.",
                    "properties": {
                        "description": {
                            "description": "Description "
                            "of "
                            "the "
                            "reason "
                            "why "
                            "the "
                            "User "
                            "account "
                            "is "
                            "being "
                            "deleted.",
                            "type": "string",
                        },
                        "slug": {
                            "description": "Idenitifier "
                            "slug of "
                            "the "
                            "reason "
                            "why the "
                            "User "
                            "account "
                            "is being "
                            "deleted.",
                            "type": "string",
                        },
                    },
                    "required": ["slug", "description"],
                    "type": "object",
                },
                "type": "array",
            }
        },
        "type": "object",
    },
    "UPDATEURLPROTECTIONBYPASS_REQUEST_BODY_SCHEMA": {
        "oneOf": [
            {
                "additionalProperties": False,
                "properties": {
                    "revoke": {
                        "description": "Optional instructions for "
                        "revoking and regenerating a "
                        "shareable link",
                        "properties": {
                            "regenerate": {
                                "description": "Whether "
                                "or "
                                "not "
                                "a "
                                "new "
                                "shareable "
                                "link "
                                "should "
                                "be "
                                "created "
                                "after "
                                "the "
                                "provided "
                                "secret "
                                "is "
                                "revoked",
                                "type": "boolean",
                            },
                            "secret": {
                                "description": "Sharebale link to revoked",
                                "type": "string",
                            },
                        },
                        "required": ["secret", "regenerate"],
                        "type": "object",
                    },
                    "ttl": {
                        "description": "Optional time the shareable link is "
                        "valid for in seconds. If not "
                        "provided, the shareable link will "
                        "never expire.",
                        "maximum": 63072000,
                        "type": "number",
                    },
                },
                "type": "object",
            },
            {
                "additionalProperties": False,
                "properties": {
                    "scope": {
                        "allOf": [
                            {"anyOf": [{"required": ["userId"]}, {"required": ["email"]}]},
                            {"required": ["access"]},
                        ],
                        "description": "Instructions for creating a user scoped protection bypass",
                        "properties": {
                            "access": {
                                "description": "Invitation status for the user scoped bypass.",
                                "enum": ["denied", "granted"],
                            },
                            "email": {
                                "description": "Specified email for the scoped bypass.",
                                "format": "email",
                                "type": "string",
                            },
                            "userId": {
                                "description": "Specified user id for the scoped bypass.",
                                "type": "string",
                            },
                        },
                        "type": "object",
                    }
                },
                "required": ["scope"],
                "type": "object",
            },
            {
                "additionalProperties": False,
                "properties": {
                    "override": {
                        "properties": {
                            "action": {"enum": ["create", "revoke"]},
                            "scope": {"enum": ["alias-protection-override"]},
                        },
                        "required": ["scope", "action"],
                        "type": "object",
                    }
                },
                "required": ["override"],
                "type": "object",
            },
        ]
    },
    "UPLOADCERTIFICATE_REQUEST_BODY_SCHEMA": {
        "additionalProperties": False,
        "properties": {
            "ca": {"description": "The certificate authority", "type": "string"},
            "cert": {"description": "The certificate", "type": "string"},
            "key": {"description": "The certificate key", "type": "string"},
            "skipValidation": {
                "description": "Skip validation of the certificate",
                "type": "boolean",
            },
        },
        "required": ["ca", "key", "cert"],
        "type": "object",
    },
}
