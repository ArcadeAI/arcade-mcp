"""Tests for MCP 2025-11-25 types added in Phase 2."""

import pytest
from arcade_mcp_server.types import (
    CancelledNotification,
    CancelTaskRequest,
    CancelTaskResult,
    ClientCapabilities,
    CreateMessageParams,
    CreateMessageResult,
    CreateTaskResult,
    ElicitationCompleteNotification,
    ElicitRequestFormParams,
    ElicitRequestURLParams,
    ElicitResult,
    GetTaskRequest,
    GetTaskResult,
    Icon,
    Implementation,
    LegacyTitledEnumSchema,
    ListTasksRequest,
    ListTasksResult,
    MCPTool,
    Prompt,
    Resource,
    ResourceTemplate,
    SamplingMessage,
    ServerCapabilities,
    Task,
    TaskStatus,
    TextContent,
    TitledMultiSelectEnumSchema,
    TitledSingleSelectEnumSchema,
    ToolChoice,
    ToolExecution,
    ToolResultContent,
    ToolUseContent,
    UntitledMultiSelectEnumSchema,
    UntitledSingleSelectEnumSchema,
    URLElicitationRequiredError,
)
from pydantic import ValidationError


class TestIcon:
    def test_construction_minimal(self):
        icon = Icon(src="https://example.com/icon.png")
        assert icon.src == "https://example.com/icon.png"
        assert icon.mimeType is None
        assert icon.sizes is None
        assert icon.theme is None

    def test_construction_full(self):
        icon = Icon(
            src="https://example.com/icon.png",
            mimeType="image/png",
            sizes=["48x48", "96x96"],
            theme="dark",
        )
        assert icon.sizes == ["48x48", "96x96"]
        assert icon.theme == "dark"

    def test_theme_light(self):
        icon = Icon(src="https://example.com/icon.png", theme="light")
        assert icon.theme == "light"

    def test_serialization_excludes_none(self):
        icon = Icon(src="https://example.com/icon.png")
        dumped = icon.model_dump(exclude_none=True)
        assert "mimeType" not in dumped
        assert "sizes" not in dumped
        assert "theme" not in dumped


class TestToolUseContent:
    def test_construction(self):
        content = ToolUseContent(
            type="tool_use", id="call_123", name="my_tool", input={"arg": "val"}
        )
        assert content.type == "tool_use"
        assert content.name == "my_tool"

    def test_type_literal_enforced(self):
        """type field must be 'tool_use'."""
        with pytest.raises(ValidationError):
            ToolUseContent(type="text", id="x", name="y", input={})


class TestToolResultContent:
    def test_construction(self):
        content = ToolResultContent(
            type="tool_result",
            toolUseId="call_123",
            content=[TextContent(type="text", text="result")],
        )
        assert content.toolUseId == "call_123"

    def test_is_error_defaults_none(self):
        content = ToolResultContent(type="tool_result", toolUseId="x", content=[])
        assert content.isError is None

    def test_structured_content(self):
        """ToolResultContent can have structuredContent for typed JSON output."""
        content = ToolResultContent(
            type="tool_result",
            toolUseId="call_123",
            content=[],
            structuredContent={"key": "value", "count": 42},
        )
        assert content.structuredContent == {"key": "value", "count": 42}

    def test_structured_content_defaults_none(self):
        content = ToolResultContent(type="tool_result", toolUseId="x", content=[])
        assert content.structuredContent is None

    def test_structured_content_excludes_from_dump_when_none(self):
        content = ToolResultContent(type="tool_result", toolUseId="x", content=[])
        dumped = content.model_dump(exclude_none=True)
        assert "structuredContent" not in dumped


class TestToolChoice:
    @pytest.mark.parametrize("mode", ["auto", "required", "none"])
    def test_valid_modes(self, mode):
        tc = ToolChoice(mode=mode)
        assert tc.mode == mode


class TestToolExecution:
    @pytest.mark.parametrize("support", ["forbidden", "optional", "required"])
    def test_valid_task_support(self, support):
        te = ToolExecution(taskSupport=support)
        assert te.taskSupport == support

    def test_default_none(self):
        te = ToolExecution()
        assert te.taskSupport is None


class TestTaskStatus:
    def test_all_values(self):
        for status in ["working", "input_required", "completed", "failed", "cancelled"]:
            assert TaskStatus(status) == status


class TestTask:
    def test_construction(self):
        task = Task(
            taskId="t1",
            status=TaskStatus.WORKING,
            createdAt="2025-01-01T00:00:00Z",
            lastUpdatedAt="2025-01-01T00:00:00Z",
            ttl=60000,
        )
        assert task.taskId == "t1"
        assert task.status == TaskStatus.WORKING

    def test_optional_fields(self):
        task = Task(
            taskId="t1",
            status=TaskStatus.WORKING,
            createdAt="2025-01-01T00:00:00Z",
            lastUpdatedAt="2025-01-01T00:00:00Z",
            ttl=60000,
        )
        assert task.statusMessage is None
        assert task.pollInterval is None

    def test_ttl_nullable(self):
        """Task.ttl type model accepts None per schema (schema.ts:1375).
        Note: our server only reports None when _max_retention is explicitly None
        (operator opt-in). With default config, ttl is always an integer."""
        task = Task(
            taskId="t1",
            status=TaskStatus.WORKING,
            createdAt="2025-01-01T00:00:00Z",
            lastUpdatedAt="2025-01-01T00:00:00Z",
            ttl=None,
        )
        assert task.ttl is None

    def test_ttl_integer(self):
        """Task.ttl is an integer in milliseconds when not null."""
        task = Task(
            taskId="t1",
            status=TaskStatus.WORKING,
            createdAt="2025-01-01T00:00:00Z",
            lastUpdatedAt="2025-01-01T00:00:00Z",
            ttl=300000,
        )
        assert task.ttl == 300000


class TestCreateTaskResult:
    """CreateTaskResult has a NESTED `task` field (unlike GetTaskResult/CancelTaskResult
    which are flat allOf: [Result, Task])."""

    def test_construction(self):
        task = Task(
            taskId="t1",
            status=TaskStatus.WORKING,
            createdAt="...",
            lastUpdatedAt="...",
            ttl=60000,
        )
        result = CreateTaskResult(task=task)
        assert result.task.taskId == "t1"


class TestGetTaskResult:
    """GetTaskResult is allOf: [Result, Task] -- flat shape with taskId/status at top level."""

    def test_flat_shape(self):
        result = GetTaskResult(
            taskId="t1",
            status=TaskStatus.WORKING,
            createdAt="...",
            lastUpdatedAt="...",
            ttl=60000,
        )
        assert result.taskId == "t1"
        assert result.status == TaskStatus.WORKING

    def test_includes_meta(self):
        result = GetTaskResult(
            taskId="t1",
            status=TaskStatus.WORKING,
            createdAt="...",
            lastUpdatedAt="...",
            ttl=60000,
            _meta={},
        )
        dumped = result.model_dump(exclude_none=True, by_alias=True)
        assert "taskId" in dumped
        assert "status" in dumped


class TestCancelTaskResult:
    """CancelTaskResult is allOf: [Result, Task] -- flat shape like GetTaskResult."""

    def test_flat_shape(self):
        result = CancelTaskResult(
            taskId="t1",
            status=TaskStatus.CANCELLED,
            createdAt="...",
            lastUpdatedAt="...",
            ttl=60000,
        )
        assert result.status == TaskStatus.CANCELLED


class TestListTasksResult:
    def test_construction(self):
        task = Task(
            taskId="t1",
            status=TaskStatus.WORKING,
            createdAt="...",
            lastUpdatedAt="...",
            ttl=60000,
        )
        result = ListTasksResult(tasks=[task])
        assert len(result.tasks) == 1
        assert result.nextCursor is None


class TestTaskRequests:
    def test_get_task_request(self):
        req = GetTaskRequest(id=1, params={"taskId": "t1"})
        assert req.method == "tasks/get"

    def test_list_tasks_request(self):
        req = ListTasksRequest(id=1)
        assert req.method == "tasks/list"

    def test_cancel_task_request(self):
        req = CancelTaskRequest(id=1, params={"taskId": "t1"})
        assert req.method == "tasks/cancel"


class TestEnumSchemas:
    def test_untitled_single_select(self):
        schema = UntitledSingleSelectEnumSchema(enum=["a", "b", "c"])
        assert schema.enum == ["a", "b", "c"]

    def test_titled_single_select(self):
        schema = TitledSingleSelectEnumSchema(
            oneOf=[{"const": "a", "title": "Option A"}, {"const": "b", "title": "Option B"}]
        )
        assert len(schema.oneOf) == 2

    def test_untitled_multi_select(self):
        schema = UntitledMultiSelectEnumSchema(items={"enum": ["a", "b"]})
        assert schema.type == "array"

    def test_titled_multi_select(self):
        schema = TitledMultiSelectEnumSchema(
            items={"anyOf": [{"const": "a", "title": "A"}]}
        )
        assert schema.type == "array"

    def test_legacy_titled_enum(self):
        schema = LegacyTitledEnumSchema(enum=["a", "b"], enumNames=["Option A", "Option B"])
        assert schema.enumNames == ["Option A", "Option B"]


class TestImplementationIconsField:
    def test_implementation_with_icons(self):
        impl = Implementation(
            name="test",
            version="1.0.0",
            icons=[Icon(src="https://example.com/icon.png")],
        )
        assert len(impl.icons) == 1

    def test_implementation_without_icons_excludes_from_dump(self):
        impl = Implementation(name="test", version="1.0.0")
        dumped = impl.model_dump(exclude_none=True)
        assert "icons" not in dumped

    def test_implementation_with_title(self):
        impl = Implementation(name="test", version="1.0.0", title="My Test Server")
        assert impl.title == "My Test Server"

    def test_implementation_without_title_excludes_from_dump(self):
        impl = Implementation(name="test", version="1.0.0")
        dumped = impl.model_dump(exclude_none=True)
        assert "title" not in dumped

    def test_implementation_with_description(self):
        impl = Implementation(name="test", version="1.0.0", description="A test server")
        assert impl.description == "A test server"

    def test_implementation_with_website_url(self):
        impl = Implementation(name="test", version="1.0.0", websiteUrl="https://example.com")
        assert impl.websiteUrl == "https://example.com"


class TestMCPToolIconsField:
    def test_tool_with_icons(self):
        tool = MCPTool(
            name="test",
            inputSchema={"type": "object"},
            icons=[Icon(src="https://example.com/icon.png")],
        )
        assert len(tool.icons) == 1

    def test_tool_without_icons_excludes_from_dump(self):
        tool = MCPTool(name="test", inputSchema={"type": "object"})
        dumped = tool.model_dump(exclude_none=True)
        assert "icons" not in dumped


class TestResourceIconsField:
    def test_resource_with_icons(self):
        resource = Resource(
            name="test",
            uri="file:///test",
            icons=[Icon(src="https://example.com/icon.png")],
        )
        assert len(resource.icons) == 1


class TestResourceTemplateIconsField:
    def test_resource_template_with_icons(self):
        template = ResourceTemplate(
            name="test",
            uriTemplate="file:///{path}",
            icons=[Icon(src="https://example.com/icon.png")],
        )
        assert len(template.icons) == 1

    def test_resource_template_without_icons_excludes_from_dump(self):
        template = ResourceTemplate(name="test", uriTemplate="file:///{path}")
        dumped = template.model_dump(exclude_none=True)
        assert "icons" not in dumped


class TestPromptIconsField:
    def test_prompt_with_icons(self):
        prompt = Prompt(name="test", icons=[Icon(src="https://example.com/icon.png")])
        assert len(prompt.icons) == 1


class TestToolExecutionOnMCPTool:
    """ToolExecution is on Tool (MCPTool), NOT on ToolAnnotations per spec."""

    def test_tool_with_execution(self):
        tool = MCPTool(
            name="test",
            inputSchema={"type": "object"},
            execution=ToolExecution(taskSupport="optional"),
        )
        assert tool.execution.taskSupport == "optional"

    def test_tool_without_execution_excludes_from_dump(self):
        tool = MCPTool(name="test", inputSchema={"type": "object"})
        dumped = tool.model_dump(exclude_none=True)
        assert "execution" not in dumped

    def test_execution_required_means_must_use_task(self):
        tool = MCPTool(
            name="test",
            inputSchema={"type": "object"},
            execution=ToolExecution(taskSupport="required"),
        )
        assert tool.execution.taskSupport == "required"

    def test_execution_forbidden_means_must_not_use_task(self):
        tool = MCPTool(
            name="test",
            inputSchema={"type": "object"},
            execution=ToolExecution(taskSupport="forbidden"),
        )
        assert tool.execution.taskSupport == "forbidden"


class TestSamplingMessageExpandedContent:
    """SamplingMessage.content changed from single block to single-or-array:
    `SamplingMessageContentBlock | SamplingMessageContentBlock[]`
    where SamplingMessageContentBlock = TextContent | ImageContent | AudioContent
    | ToolUseContent | ToolResultContent.
    Also added optional `_meta` field."""

    def test_sampling_message_with_tool_use_content(self):
        msg = SamplingMessage(
            role="assistant",
            content=ToolUseContent(type="tool_use", id="c1", name="t", input={}),
        )
        assert msg.content.type == "tool_use"

    def test_sampling_message_with_tool_result_content(self):
        msg = SamplingMessage(
            role="user",
            content=ToolResultContent(type="tool_result", toolUseId="c1", content=[]),
        )
        assert msg.content.type == "tool_result"

    def test_sampling_message_with_text_still_works(self):
        """Backward compatibility: existing TextContent still works."""
        msg = SamplingMessage(
            role="user", content=TextContent(type="text", text="hello")
        )
        assert msg.content.type == "text"

    def test_sampling_message_with_array_content(self):
        """Content can be an array of SamplingMessageContentBlock."""
        msg = SamplingMessage(
            role="assistant",
            content=[
                TextContent(type="text", text="I'll call the tool"),
                ToolUseContent(type="tool_use", id="c1", name="t", input={"x": 1}),
            ],
        )
        assert isinstance(msg.content, list)
        assert len(msg.content) == 2

    def test_sampling_message_with_meta(self):
        """SamplingMessage has optional _meta field."""
        msg = SamplingMessage(
            role="user",
            content=TextContent(type="text", text="hello"),
            _meta={"custom_key": "value"},
        )
        dumped = msg.model_dump(exclude_none=True, by_alias=True)
        assert "_meta" in dumped

    def test_sampling_message_without_meta_excludes_from_dump(self):
        msg = SamplingMessage(
            role="user", content=TextContent(type="text", text="hello")
        )
        dumped = msg.model_dump(exclude_none=True, by_alias=True)
        assert "_meta" not in dumped


class TestCreateMessageParamsToolFields:
    def test_create_message_params_with_tools(self):
        params = CreateMessageParams(
            messages=[],
            maxTokens=100,
            tools=[MCPTool(name="t", inputSchema={"type": "object"})],
            toolChoice=ToolChoice(mode="auto"),
        )
        assert len(params.tools) == 1
        assert params.toolChoice.mode == "auto"

    def test_create_message_params_without_tools_backward_compat(self):
        """Existing usage without tools still works."""
        params = CreateMessageParams(messages=[], maxTokens=100)
        assert params.tools is None
        assert params.toolChoice is None


class TestElicitResultExpandedContent:
    def test_elicit_result_with_string_array_value(self):
        result = ElicitResult(action="accept", content={"choices": ["a", "b"]})
        assert result.content["choices"] == ["a", "b"]

    def test_elicit_result_with_scalar_values_still_works(self):
        """Backward compatibility: existing scalar values still work."""
        result = ElicitResult(action="accept", content={"name": "test", "count": 5})
        assert result.content["name"] == "test"


class TestServerCapabilitiesTasks:
    def test_server_capabilities_with_nested_tasks_structure(self):
        """Tasks capability must have nested requests structure per spec."""
        caps = ServerCapabilities(
            tasks={
                "list": {},
                "cancel": {},
                "requests": {"tools": {"call": {}}},
            }
        )
        assert caps.tasks["requests"]["tools"]["call"] == {}

    def test_server_capabilities_without_tasks_backward_compat(self):
        caps = ServerCapabilities(tools={"listChanged": True})
        dumped = caps.model_dump(exclude_none=True)
        assert "tasks" not in dumped


class TestClientCapabilitiesExpanded:
    def test_client_capabilities_with_tasks_sampling_augmentation(self):
        """Client declares support for task-augmented sampling/createMessage."""
        caps = ClientCapabilities(
            tasks={
                "list": {},
                "cancel": {},
                "requests": {
                    "sampling": {"createMessage": {}},
                    "elicitation": {"create": {}},
                },
            }
        )
        assert caps.tasks is not None
        assert "sampling" in caps.tasks["requests"]
        assert "createMessage" in caps.tasks["requests"]["sampling"]
        assert "elicitation" in caps.tasks["requests"]
        assert "create" in caps.tasks["requests"]["elicitation"]

    def test_client_capabilities_with_sampling_tools(self):
        """Client declares support for tool use via tools and toolChoice params."""
        caps = ClientCapabilities(sampling={"tools": {}})
        assert caps.sampling["tools"] is not None

    def test_client_capabilities_with_elicitation_form_and_url(self):
        """2025-11-25 clients declare form/url elicitation support separately."""
        caps = ClientCapabilities(elicitation={"form": {}, "url": {}})
        assert "url" in caps.elicitation
        assert "form" in caps.elicitation

    def test_client_capabilities_elicitation_form_only_backward_compat(self):
        """Empty elicitation dict is equivalent to form-only support."""
        caps = ClientCapabilities(elicitation={})
        assert caps.elicitation is not None


class TestElicitRequestURLParams:
    def test_construction_with_elicitation_id(self):
        """URL mode requires elicitationId per spec."""
        params = ElicitRequestURLParams(
            mode="url",
            url="https://example.com/auth",
            elicitationId="elic_123",
            message="Please authenticate",
        )
        assert params.elicitationId == "elic_123"
        assert params.mode == "url"

    def test_serialization(self):
        params = ElicitRequestURLParams(
            mode="url",
            url="https://example.com/auth",
            elicitationId="elic_123",
            message="Please authenticate",
        )
        dumped = params.model_dump(exclude_none=True)
        assert "elicitationId" in dumped
        assert "url" in dumped
        assert "mode" in dumped


class TestElicitationCompleteNotification:
    def test_construction(self):
        notif = ElicitationCompleteNotification(
            method="notifications/elicitation/complete",
            params={"elicitationId": "elic_123"},
        )
        assert notif.params["elicitationId"] == "elic_123"


class TestURLElicitationRequiredError:
    def test_error_code_is_minus_32042(self):
        """URLElicitationRequiredError must use code -32042."""
        err = URLElicitationRequiredError(
            code=-32042,
            message="Elicitation required",
            data={
                "elicitations": [
                    {
                        "mode": "url",
                        "elicitationId": "e1",
                        "url": "https://example.com/auth",
                        "message": "Auth needed",
                    }
                ]
            },
        )
        assert err.code == -32042


class TestCancelledNotificationRequestIdOptional:
    """In 2025-11-25, CancelledNotification.requestId schema type became optional
    (was required in 2025-06-18). However, spec constrains usage:
    - MUST be provided for non-task requests (schema.ts:218)
    - MUST NOT use CancelledNotification for task cancellation -- use tasks/cancel (cancellation.mdx:38)
    So in practice, the server ALWAYS includes requestId when sending this notification.
    These tests verify schema-level type tolerance (deserialization), not sending behavior."""

    def test_cancelled_notification_with_request_id(self):
        """Normal usage: requestId always present when server sends for non-task cancellation."""
        notif = CancelledNotification(
            method="notifications/cancelled",
            params={"requestId": "req-123", "reason": "User requested"},
        )
        assert notif.params["requestId"] == "req-123"

    def test_cancelled_notification_schema_allows_missing_request_id(self):
        """Schema-level: the type accepts missing requestId (2025-11-25 schema change).
        This tests deserialization tolerance only -- the server should NOT send
        CancelledNotification without requestId. It should use tasks/cancel for task
        cancellation instead (cancellation.mdx:38, schema.ts:219)."""
        notif = CancelledNotification(
            method="notifications/cancelled",
            params={"reason": "Some reason"},
        )
        # Model accepts this without validation error -- schema is permissive
        assert "requestId" not in notif.params or notif.params.get("requestId") is None

    def test_cancelled_notification_serialization_excludes_none(self):
        notif = CancelledNotification(
            method="notifications/cancelled",
            params={"reason": "Cancelled"},
        )
        dumped = notif.model_dump(exclude_none=True)
        assert "requestId" not in dumped.get("params", {})


class TestElicitationPrimitiveDefaults:
    """All elicitation primitive types (String, Number, Boolean) gained optional
    `default` fields in 2025-11-25 (SEP-1034)."""

    def test_string_schema_with_default(self):
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string", "default": "John"}},
        }
        params = ElicitRequestFormParams(message="Enter name", requestedSchema=schema)
        assert params.requestedSchema["properties"]["name"]["default"] == "John"

    def test_number_schema_with_default(self):
        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "default": 10, "minimum": 1, "maximum": 100}
            },
        }
        params = ElicitRequestFormParams(message="Enter count", requestedSchema=schema)
        assert params.requestedSchema["properties"]["count"]["default"] == 10

    def test_boolean_schema_with_default(self):
        schema = {
            "type": "object",
            "properties": {"enabled": {"type": "boolean", "default": True}},
        }
        params = ElicitRequestFormParams(message="Toggle", requestedSchema=schema)
        assert params.requestedSchema["properties"]["enabled"]["default"] is True

    def test_schemas_without_default_backward_compat(self):
        """Schemas without default still work (backward compat)."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }
        params = ElicitRequestFormParams(message="Enter name", requestedSchema=schema)
        assert "default" not in params.requestedSchema["properties"]["name"]


class TestExpandedClientInfo:
    """Clients now send title, description, icons, websiteUrl in clientInfo.
    Since Implementation type is being updated with these fields, verify parsing."""

    def test_parse_expanded_client_info(self):
        """Client sends full Implementation with new optional fields."""
        client_info = Implementation(
            name="test-client",
            version="2.0.0",
            title="My Test Client",
            description="A test MCP client",
            icons=[Icon(src="https://example.com/icon.png", theme="dark")],
            websiteUrl="https://example.com",
        )
        assert client_info.title == "My Test Client"
        assert client_info.description == "A test MCP client"
        assert len(client_info.icons) == 1
        assert client_info.icons[0].theme == "dark"
        assert client_info.websiteUrl == "https://example.com"

    def test_parse_minimal_client_info_backward_compat(self):
        """Older clients send only name+version -- still works."""
        client_info = Implementation(name="old-client", version="1.0.0")
        dumped = client_info.model_dump(exclude_none=True)
        assert "title" not in dumped
        assert "icons" not in dumped


class TestStopReasonExpanded:
    """CreateMessageResult.stopReason now explicitly includes 'toolUse'
    (alongside endTurn, stopSequence, maxTokens). It's an open string."""

    def test_stop_reason_tool_use(self):
        result = CreateMessageResult(
            role="assistant",
            content=TextContent(type="text", text="calling tool"),
            model="test-model",
            stopReason="toolUse",
        )
        assert result.stopReason == "toolUse"

    def test_stop_reason_end_turn(self):
        result = CreateMessageResult(
            role="assistant",
            content=TextContent(type="text", text="done"),
            model="test-model",
            stopReason="endTurn",
        )
        assert result.stopReason == "endTurn"

    def test_stop_reason_provider_specific(self):
        """stopReason is an open string -- provider-specific values allowed."""
        result = CreateMessageResult(
            role="assistant",
            content=TextContent(type="text", text="done"),
            model="test-model",
            stopReason="custom_provider_reason",
        )
        assert result.stopReason == "custom_provider_reason"


class TestInputSchemaAcceptsSchemaDialect:
    """Tool.inputSchema can include $schema to declare JSON Schema dialect.
    Since inputSchema is dict[str, Any], this already works -- verify it."""

    def test_input_schema_with_dollar_schema(self):
        tool = MCPTool(
            name="test",
            inputSchema={
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {"x": {"type": "integer"}},
            },
        )
        assert (
            tool.inputSchema["$schema"]
            == "https://json-schema.org/draft/2020-12/schema"
        )

    def test_input_schema_without_dollar_schema_backward_compat(self):
        tool = MCPTool(name="test", inputSchema={"type": "object"})
        assert "$schema" not in tool.inputSchema
