"""Tests for Resource Manager implementation."""

import asyncio
import base64
import logging

import pytest
from arcade_mcp_server.exceptions import NotFoundError, ResourceError
from arcade_mcp_server.managers.resource import (
    ResourceManager,
    _is_template_uri,
    _template_to_regex,
    _template_to_sample_uri,
)
from arcade_mcp_server.types import (
    BlobResourceContents,
    Resource,
    ResourceContents,
    ResourceTemplate,
    TextResourceContents,
)


class TestResourceManager:
    """Test ResourceManager class."""

    @pytest.fixture
    def resource_manager(self):
        """Create a resource manager instance."""
        return ResourceManager()

    @pytest.fixture
    def sample_resource(self):
        """Create a sample resource."""
        return Resource(
            uri="file:///test.txt",
            name="test.txt",
            description="A test text file",
            mimeType="text/plain",
        )

    @pytest.fixture
    def sample_template(self):
        """Create a sample resource template."""
        return ResourceTemplate(
            uriTemplate="file:///{path}",
            name="File Template",
            description="Template for file resources",
            mimeType="text/plain",
        )

    def test_manager_initialization(self):
        """Test resource manager initialization."""
        manager = ResourceManager()
        # Passive manager: no started flag
        assert isinstance(manager, ResourceManager)

    @pytest.mark.asyncio
    async def test_manager_lifecycle(self, resource_manager):
        """Passive manager has no explicit lifecycle; ensure methods work."""
        resources = await resource_manager.list_resources()
        assert resources == []

    @pytest.mark.asyncio
    async def test_add_resource(self, resource_manager, sample_resource):
        """Test adding resources."""
        await resource_manager.add_resource(sample_resource)

        resources = await resource_manager.list_resources()
        assert len(resources) == 1
        assert resources[0].uri == sample_resource.uri

    @pytest.mark.asyncio
    async def test_remove_resource(self, resource_manager, sample_resource):
        """Test removing resources."""
        await resource_manager.add_resource(sample_resource)
        removed = await resource_manager.remove_resource(sample_resource.uri)
        assert removed.uri == sample_resource.uri

        resources = await resource_manager.list_resources()
        assert len(resources) == 0

    @pytest.mark.asyncio
    async def test_remove_nonexistent_resource(self, resource_manager):
        """Test removing non-existent resource."""
        with pytest.raises(NotFoundError):
            await resource_manager.remove_resource("file:///nonexistent.txt")

    @pytest.mark.asyncio
    async def test_add_resource_template(self, resource_manager, sample_template):
        """Test adding resource templates."""
        await resource_manager.add_template(sample_template)

        templates = await resource_manager.list_resource_templates()
        assert len(templates) == 1
        assert templates[0].uriTemplate == sample_template.uriTemplate

    @pytest.mark.asyncio
    async def test_resource_handlers(self, resource_manager):
        """Test adding and using resource handlers."""
        resource = Resource(
            uri="custom://test", name="Custom Resource", description="Resource with custom handler"
        )

        async def custom_handler(uri: str) -> list[ResourceContents]:
            return [
                TextResourceContents(
                    uri=uri, text="Custom content for " + uri, mimeType="text/plain"
                )
            ]

        await resource_manager.add_resource(resource, handler=custom_handler)

        contents = await resource_manager.read_resource("custom://test")

        assert len(contents) == 1
        assert contents[0].text == "Custom content for custom://test"

    @pytest.mark.asyncio
    async def test_read_resource_without_handler(self, resource_manager, sample_resource):
        """Test reading resource without a handler returns default content."""
        await resource_manager.add_resource(sample_resource)

        contents = await resource_manager.read_resource(sample_resource.uri)
        assert len(contents) == 1
        assert contents[0].uri == sample_resource.uri

    @pytest.mark.asyncio
    async def test_read_nonexistent_resource(self, resource_manager):
        """Test reading non-existent resource."""
        with pytest.raises(NotFoundError):
            await resource_manager.read_resource("file:///nonexistent.txt")

    @pytest.mark.asyncio
    async def test_binary_resource_content(self, resource_manager):
        """Test handling binary resource content."""
        resource = Resource(uri="file:///image.png", name="image.png", mimeType="image/png")

        async def image_handler(uri: str) -> list[ResourceContents]:
            png_data = base64.b64encode(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
            ).decode()
            return [BlobResourceContents(uri=uri, blob=png_data, mimeType="image/png")]

        await resource_manager.add_resource(resource, handler=image_handler)

        contents = await resource_manager.read_resource("file:///image.png")

        assert len(contents) == 1
        assert isinstance(contents[0], BlobResourceContents)
        assert contents[0].mimeType == "image/png"

    @pytest.mark.asyncio
    async def test_multiple_resource_contents(self, resource_manager):
        """Test resources that return multiple contents."""
        resource = Resource(uri="multi://resource", name="Multi Resource")

        async def multi_handler(uri: str) -> list[ResourceContents]:
            return [
                TextResourceContents(uri=uri + "#part1", text="Part 1"),
                TextResourceContents(uri=uri + "#part2", text="Part 2"),
                BlobResourceContents(uri=uri + "#data", blob="YmluYXJ5"),
            ]

        await resource_manager.add_resource(resource, handler=multi_handler)

        contents = await resource_manager.read_resource("multi://resource")

        assert len(contents) == 3
        assert contents[0].text == "Part 1"
        assert contents[1].text == "Part 2"
        assert contents[2].blob == "YmluYXJ5"

    @pytest.mark.asyncio
    async def test_concurrent_resource_operations(self, resource_manager):
        """Test concurrent resource operations."""
        # Create multiple resources
        resources = []
        for i in range(10):
            resource = Resource(
                uri=f"file:///{i}.txt", name=f"File {i}", description=f"Test file {i}"
            )
            resources.append(resource)

        tasks = [resource_manager.add_resource(r) for r in resources]
        await asyncio.gather(*tasks)

        listed = await resource_manager.list_resources()
        assert len(listed) == 10

    @pytest.mark.asyncio
    async def test_list_resources_and_templates_initial(self):
        """Passive manager lists resources/templates initially as empty."""
        manager = ResourceManager()
        resources = await manager.list_resources()
        assert resources == []
        templates = await manager.list_resource_templates()
        assert templates == []


class TestBytesReturnType:
    """Test that handlers returning raw bytes are auto-encoded to BlobResourceContents."""

    @pytest.mark.asyncio
    async def test_handler_returning_bytes_produces_blob_contents(self):
        manager = ResourceManager()
        resource = Resource(uri="img://test", name="test")
        await manager.add_resource(resource, handler=lambda _uri: b"\x89PNG\r\n")

        result = await manager.read_resource("img://test")

        assert len(result) == 1
        assert isinstance(result[0], BlobResourceContents)
        assert result[0].blob == base64.b64encode(b"\x89PNG\r\n").decode("ascii")

    @pytest.mark.asyncio
    async def test_handler_returning_bytes_preserves_mime_type(self):
        manager = ResourceManager()
        resource = Resource(uri="img://png", name="png", mimeType="image/png")
        await manager.add_resource(resource, handler=lambda _uri: b"\x89PNG")

        result = await manager.read_resource("img://png")

        assert isinstance(result[0], BlobResourceContents)
        assert result[0].mimeType == "image/png"

    @pytest.mark.asyncio
    async def test_handler_returning_empty_bytes(self):
        manager = ResourceManager()
        resource = Resource(uri="img://empty", name="empty")
        await manager.add_resource(resource, handler=lambda _uri: b"")

        result = await manager.read_resource("img://empty")

        assert isinstance(result[0], BlobResourceContents)
        assert result[0].blob == ""


class TestResourceTemplateMatching:
    """Test URI template matching for resources/read."""

    def test_is_template_uri_with_braces(self):
        assert _is_template_uri("weather://{city}/current") is True

    def test_is_template_uri_without_braces(self):
        assert _is_template_uri("file:///static.txt") is False

    def test_template_to_regex_single_param(self):
        pattern = _template_to_regex("weather://{city}/current")
        m = pattern.match("weather://london/current")
        assert m is not None
        assert m.group("city") == "london"

    def test_template_to_regex_multiple_params(self):
        pattern = _template_to_regex("db://{database}/{table}")
        m = pattern.match("db://mydb/users")
        assert m is not None
        assert m.group("database") == "mydb"
        assert m.group("table") == "users"

    def test_template_to_regex_wildcard(self):
        pattern = _template_to_regex("file:///{path*}")
        m = pattern.match("file:///a/b/c.txt")
        assert m is not None
        assert m.group("path") == "a/b/c.txt"

    @pytest.mark.asyncio
    async def test_read_resource_matches_template(self):
        manager = ResourceManager()
        tmpl = ResourceTemplate(
            uriTemplate="weather://{city}/current",
            name="Weather",
            mimeType="text/plain",
        )

        def handler(uri: str, city: str) -> str:
            return f"Weather for {city}"

        await manager.add_template_with_handler(tmpl, handler)

        result = await manager.read_resource("weather://london/current")
        assert len(result) == 1
        assert isinstance(result[0], TextResourceContents)
        assert result[0].text == "Weather for london"

    @pytest.mark.asyncio
    async def test_read_resource_template_handler_receives_params(self):
        manager = ResourceManager()
        tmpl = ResourceTemplate(
            uriTemplate="weather://{city}/current",
            name="Weather",
        )
        received: dict[str, str] = {}

        def handler(uri: str, city: str) -> str:
            received["city"] = city
            return "ok"

        await manager.add_template_with_handler(tmpl, handler)
        await manager.read_resource("weather://london/current")
        assert received["city"] == "london"

    @pytest.mark.asyncio
    async def test_read_resource_exact_match_takes_priority(self):
        manager = ResourceManager()
        # Add exact match
        exact = Resource(uri="weather://london/current", name="London Weather")
        await manager.add_resource(exact, handler=lambda _uri: "exact match")

        # Add template
        tmpl = ResourceTemplate(
            uriTemplate="weather://{city}/current", name="Weather Template"
        )
        await manager.add_template_with_handler(tmpl, lambda uri, city: "template match")

        result = await manager.read_resource("weather://london/current")
        assert result[0].text == "exact match"

    @pytest.mark.asyncio
    async def test_read_resource_template_no_match_raises_not_found(self):
        manager = ResourceManager()
        tmpl = ResourceTemplate(
            uriTemplate="weather://{city}/current", name="Weather"
        )
        await manager.add_template_with_handler(tmpl, lambda uri, city: "ok")

        with pytest.raises(NotFoundError):
            await manager.read_resource("completely://different")

    @pytest.mark.asyncio
    async def test_read_resource_template_handler_str_return_coercion(self):
        manager = ResourceManager()
        tmpl = ResourceTemplate(
            uriTemplate="data://{item_id}",
            name="Data",
            mimeType="text/plain",
        )
        await manager.add_template_with_handler(tmpl, lambda uri, item_id: "hello")

        result = await manager.read_resource("data://42")
        assert isinstance(result[0], TextResourceContents)
        assert result[0].text == "hello"

    @pytest.mark.asyncio
    async def test_read_resource_template_handler_bytes_return_coercion(self):
        manager = ResourceManager()
        tmpl = ResourceTemplate(
            uriTemplate="bin://{item_id}",
            name="Binary",
            mimeType="application/octet-stream",
        )
        await manager.add_template_with_handler(tmpl, lambda uri, item_id: b"\x00\x01")

        result = await manager.read_resource("bin://42")
        assert isinstance(result[0], BlobResourceContents)
        assert result[0].blob == base64.b64encode(b"\x00\x01").decode("ascii")

    @pytest.mark.asyncio
    async def test_read_resource_template_async_handler(self):
        manager = ResourceManager()
        tmpl = ResourceTemplate(
            uriTemplate="async://{key}",
            name="Async",
        )

        async def handler(uri: str, key: str) -> str:
            return f"async-{key}"

        await manager.add_template_with_handler(tmpl, handler)

        result = await manager.read_resource("async://abc")
        assert result[0].text == "async-abc"


class TestStaticResources:
    """Test convenience methods for static resources."""

    @pytest.mark.asyncio
    async def test_add_text_resource(self):
        manager = ResourceManager()
        await manager.add_text_resource("text://hello", text="hello")

        result = await manager.read_resource("text://hello")
        assert isinstance(result[0], TextResourceContents)
        assert result[0].text == "hello"

    @pytest.mark.asyncio
    async def test_add_text_resource_with_metadata(self):
        manager = ResourceManager()
        await manager.add_text_resource(
            "text://meta",
            text="content",
            name="my-resource",
            description="A description",
            mime_type="text/html",
        )

        resources = await manager.list_resources()
        assert len(resources) == 1
        assert resources[0].name == "my-resource"
        assert resources[0].description == "A description"
        assert resources[0].mimeType == "text/html"

    @pytest.mark.asyncio
    async def test_add_file_resource(self, tmp_path):
        manager = ResourceManager()
        f = tmp_path / "test.txt"
        f.write_text("file content")

        await manager.add_file_resource("file:///test.txt", path=str(f))

        result = await manager.read_resource("file:///test.txt")
        assert isinstance(result[0], TextResourceContents)
        assert result[0].text == "file content"

    @pytest.mark.asyncio
    async def test_add_file_resource_binary(self, tmp_path):
        manager = ResourceManager()
        f = tmp_path / "image.bin"
        f.write_bytes(b"\x89PNG\r\n")

        await manager.add_file_resource("file:///image.bin", path=str(f))

        result = await manager.read_resource("file:///image.bin")
        assert isinstance(result[0], BlobResourceContents)

    @pytest.mark.asyncio
    async def test_add_file_resource_not_found(self, tmp_path):
        manager = ResourceManager()
        await manager.add_file_resource(
            "file:///missing.txt", path=str(tmp_path / "missing.txt")
        )

        with pytest.raises(NotFoundError, match="File not found"):
            await manager.read_resource("file:///missing.txt")


class TestDuplicateHandlingPolicy:
    """Test duplicate resource handling policies."""

    def test_default_policy_is_warn(self):
        manager = ResourceManager()
        assert manager.duplicate_policy == "warn"

    @pytest.mark.asyncio
    async def test_policy_warn_logs_and_replaces(self, caplog):
        manager = ResourceManager(duplicate_policy="warn")
        r1 = Resource(uri="dup://test", name="first")
        r2 = Resource(uri="dup://test", name="second")

        await manager.add_resource(r1, handler=lambda _: "first")
        with caplog.at_level(logging.WARNING, logger="arcade.mcp.managers.resource"):
            await manager.add_resource(r2, handler=lambda _: "second")

        assert "Replacing duplicate resource" in caplog.text

        # Second handler should win
        result = await manager.read_resource("dup://test")
        assert result[0].text == "second"

    @pytest.mark.asyncio
    async def test_policy_error_raises(self):
        manager = ResourceManager(duplicate_policy="error")
        r = Resource(uri="dup://test", name="first")
        await manager.add_resource(r)

        with pytest.raises(ResourceError, match="already registered"):
            await manager.add_resource(r)

    @pytest.mark.asyncio
    async def test_policy_replace_silently(self, caplog):
        manager = ResourceManager(duplicate_policy="replace")
        r1 = Resource(uri="dup://test", name="first")
        r2 = Resource(uri="dup://test", name="second")

        await manager.add_resource(r1, handler=lambda _: "first")
        with caplog.at_level(logging.WARNING, logger="arcade.mcp.managers.resource"):
            await manager.add_resource(r2, handler=lambda _: "second")

        # No warning logged
        assert "Replacing duplicate resource" not in caplog.text

        result = await manager.read_resource("dup://test")
        assert result[0].text == "second"

    @pytest.mark.asyncio
    async def test_policy_ignore_keeps_first(self):
        manager = ResourceManager(duplicate_policy="ignore")
        r1 = Resource(uri="dup://test", name="first")
        r2 = Resource(uri="dup://test", name="second")

        await manager.add_resource(r1, handler=lambda _: "first")
        await manager.add_resource(r2, handler=lambda _: "second")

        # First handler should be kept
        result = await manager.read_resource("dup://test")
        assert result[0].text == "first"


class TestCoerceResultDictBranches:
    """Test _coerce_result dict sub-branches and other handler return types."""

    @pytest.mark.asyncio
    async def test_handler_returning_dict_with_text_key(self):
        manager = ResourceManager()
        resource = Resource(uri="dict://text", name="text", mimeType="text/plain")
        await manager.add_resource(resource, handler=lambda _uri: {"text": "from dict"})

        result = await manager.read_resource("dict://text")
        assert isinstance(result[0], TextResourceContents)
        assert result[0].text == "from dict"
        assert result[0].mimeType == "text/plain"

    @pytest.mark.asyncio
    async def test_handler_returning_dict_with_blob_key(self):
        manager = ResourceManager()
        resource = Resource(uri="dict://blob", name="blob", mimeType="application/octet-stream")
        await manager.add_resource(resource, handler=lambda _uri: {"blob": "AQID"})

        result = await manager.read_resource("dict://blob")
        assert isinstance(result[0], BlobResourceContents)
        assert result[0].blob == "AQID"
        assert result[0].mimeType == "application/octet-stream"

    @pytest.mark.asyncio
    async def test_handler_returning_dict_with_no_text_or_blob(self):
        manager = ResourceManager()
        resource = Resource(uri="dict://empty", name="empty", mimeType="application/json")
        await manager.add_resource(resource, handler=lambda _uri: {"foo": "bar"})

        result = await manager.read_resource("dict://empty")
        assert isinstance(result[0], ResourceContents)
        assert result[0].mimeType == "application/json"

    @pytest.mark.asyncio
    async def test_handler_returning_non_standard_type(self):
        """Handlers returning arbitrary types get str()-converted."""
        manager = ResourceManager()
        resource = Resource(uri="misc://int", name="int")
        await manager.add_resource(resource, handler=lambda _uri: 42)

        result = await manager.read_resource("misc://int")
        assert isinstance(result[0], TextResourceContents)
        assert result[0].text == "42"


class TestUpdateResource:
    """Test ResourceManager.update_resource."""

    @pytest.mark.asyncio
    async def test_update_existing_resource(self):
        manager = ResourceManager()
        r = Resource(uri="upd://test", name="original")
        await manager.add_resource(r, handler=lambda _uri: "original")

        updated = Resource(uri="upd://test", name="updated")
        result = await manager.update_resource("upd://test", updated, handler=lambda _uri: "updated")
        assert result.name == "updated"

        contents = await manager.read_resource("upd://test")
        assert contents[0].text == "updated"

    @pytest.mark.asyncio
    async def test_update_nonexistent_resource_raises(self):
        manager = ResourceManager()
        r = Resource(uri="upd://missing", name="missing")
        with pytest.raises(NotFoundError, match="not found"):
            await manager.update_resource("upd://missing", r)


class TestRemoveTemplate:
    """Test ResourceManager.remove_template."""

    @pytest.mark.asyncio
    async def test_remove_template_success(self):
        manager = ResourceManager()
        tmpl = ResourceTemplate(uriTemplate="rm://{id}", name="removable")
        await manager.add_template_with_handler(tmpl, lambda uri, id: f"item {id}")

        removed = await manager.remove_template("rm://{id}")
        assert removed.uriTemplate == "rm://{id}"

        # Template handler should no longer match
        with pytest.raises(NotFoundError):
            await manager.read_resource("rm://123")

    @pytest.mark.asyncio
    async def test_remove_template_not_found(self):
        manager = ResourceManager()
        with pytest.raises(NotFoundError, match="not found"):
            await manager.remove_template("nonexistent://{x}")


class TestTemplateOverlapWarning:
    """Test that overlapping templates produce a warning at registration time."""

    def test_template_to_sample_uri_simple(self):
        assert _template_to_sample_uri("weather://{city}/current") == "weather://__city__/current"

    def test_template_to_sample_uri_wildcard(self):
        sample = _template_to_sample_uri("file:///{path*}")
        assert sample == "file:///__path__/nested"

    @pytest.mark.asyncio
    async def test_wildcard_before_specific_warns(self, caplog):
        """A broad wildcard registered first should warn when a narrower template is added."""
        manager = ResourceManager()
        broad = ResourceTemplate(uriTemplate="kb://docs/{path*}", name="Catch-all")
        specific = ResourceTemplate(
            uriTemplate="kb://docs/{category}/articles/{slug}", name="Specific"
        )

        await manager.add_template_with_handler(broad, lambda uri, path: "broad")
        with caplog.at_level(logging.WARNING, logger="arcade.mcp.managers.resource"):
            await manager.add_template_with_handler(specific, lambda uri, category, slug: "specific")

        assert "overlaps" in caplog.text
        assert "kb://docs/{path*}" in caplog.text
        assert "kb://docs/{category}/articles/{slug}" in caplog.text

    @pytest.mark.asyncio
    async def test_specific_before_wildcard_warns(self, caplog):
        """Adding a broad template after a specific one also warns."""
        manager = ResourceManager()
        specific = ResourceTemplate(
            uriTemplate="kb://docs/{category}/articles/{slug}", name="Specific"
        )
        broad = ResourceTemplate(uriTemplate="kb://docs/{path*}", name="Catch-all")

        await manager.add_template_with_handler(specific, lambda uri, category, slug: "specific")
        with caplog.at_level(logging.WARNING, logger="arcade.mcp.managers.resource"):
            await manager.add_template_with_handler(broad, lambda uri, path: "broad")

        assert "overlaps" in caplog.text

    @pytest.mark.asyncio
    async def test_non_overlapping_templates_no_warning(self, caplog):
        """Templates with different prefixes should not warn."""
        manager = ResourceManager()
        t1 = ResourceTemplate(uriTemplate="weather://{city}/current", name="Weather")
        t2 = ResourceTemplate(uriTemplate="news://{topic}/latest", name="News")

        await manager.add_template_with_handler(t1, lambda uri, city: "weather")
        with caplog.at_level(logging.WARNING, logger="arcade.mcp.managers.resource"):
            await manager.add_template_with_handler(t2, lambda uri, topic: "news")

        assert "overlaps" not in caplog.text
