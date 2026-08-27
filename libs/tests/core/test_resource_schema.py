"""The resource schema must serialize exactly as it goes on the wire.

The field names, the ``_meta`` alias, and the text-versus-blob distinction are
wire contract rather than internal detail: a caller decodes these bytes, so a
renamed field or a collapsed distinction is a break.
"""

import pytest
from arcade_core.resource_schema import (
    BlobResourceContents,
    ListResourcesParams,
    ListResourcesResult,
    ReadResourceResult,
    Resource,
    TextResourceContents,
)
from pydantic import ValidationError


def test_resource_serializes_meta_under_the_underscore_key():
    resource = Resource(
        uri="ui://Gmail/8.1.0/draft.html",
        name="Draft review",
        mimeType="text/html;profile=example",
        meta={"ui": {"csp": {"resourceDomains": ["https://cdn.example.com"]}}},
    )

    dumped = resource.model_dump(by_alias=True, exclude_none=True)

    assert dumped["_meta"] == {"ui": {"csp": {"resourceDomains": ["https://cdn.example.com"]}}}
    assert "meta" not in dumped


def test_resource_accepts_the_underscore_key_on_the_way_in():
    resource = Resource.model_validate({
        "uri": "ui://Gmail/8.1.0/draft.html",
        "name": "Draft review",
        "_meta": {"ui": {"prefersBorder": True}},
    })

    assert resource.meta == {"ui": {"prefersBorder": True}}


def test_mime_type_is_carried_byte_for_byte():
    """A host that renders an interface compares this with string equality."""
    resource = Resource(uri="ui://x/1.0.0/a.html", name="a", mimeType="text/html;profile=example")

    assert resource.model_dump(by_alias=True)["mimeType"] == "text/html;profile=example"


def test_empty_text_and_empty_blob_stay_distinguishable():
    text = ReadResourceResult(contents=[TextResourceContents(uri="res://a", text="")])
    blob = ReadResourceResult(contents=[BlobResourceContents(uri="res://a", blob="")])

    text_dumped = text.model_dump(by_alias=True, exclude_none=True)["contents"][0]
    blob_dumped = blob.model_dump(by_alias=True, exclude_none=True)["contents"][0]

    assert text_dumped == {"uri": "res://a", "text": ""}
    assert blob_dumped == {"uri": "res://a", "blob": ""}
    assert text_dumped != blob_dumped


def test_blob_stays_a_string_and_is_never_re_encoded():
    """A bytes-typed field would normalize padding and alphabet on every read."""
    padded = "YQ=="
    result = ReadResourceResult.model_validate({"contents": [{"uri": "res://a", "blob": padded}]})

    assert isinstance(result.contents[0], BlobResourceContents)
    assert result.contents[0].blob == padded


def test_read_result_round_trips_a_mixed_contents_list():
    payload = {
        "contents": [
            {"uri": "res://t", "mimeType": "text/plain", "text": "hello"},
            {"uri": "res://b", "mimeType": "application/octet-stream", "blob": "AAEC"},
        ]
    }

    result = ReadResourceResult.model_validate(payload)

    assert isinstance(result.contents[0], TextResourceContents)
    assert isinstance(result.contents[1], BlobResourceContents)
    assert result.model_dump(by_alias=True, exclude_none=True) == payload


def test_list_result_defaults_to_an_empty_page():
    result = ListResourcesResult()

    assert result.resources == []
    assert result.model_dump(by_alias=True, exclude_none=True) == {"resources": []}


def test_list_params_accept_an_absent_cursor():
    """A first-page request sends an empty body, which the router coerces to {}."""
    assert ListResourcesParams.model_validate({}).cursor is None
    assert ListResourcesParams.model_validate({"cursor": "b2Zmc2V0OjI="}).cursor == "b2Zmc2V0OjI="


def test_resource_requires_a_uri_and_a_name():
    with pytest.raises(ValidationError):
        Resource(name="missing uri")
    with pytest.raises(ValidationError):
        Resource(uri="ui://x/1.0.0/a.html")


def test_meta_keyword_reaches_the_aliased_field_rather_than_extras():
    """``meta=`` must land on ``_meta``.

    With extra="allow" and no populate_by_name, pydantic accepts ``meta=`` as an
    extra field and emits it as ``meta``. A caller reads only ``_meta``, so a
    developer-declared CSP would vanish with no error anywhere.
    """
    resource = Resource(uri="ui://x/1.0.0/a.html", name="a", meta={"ui": {"csp": {}}})
    contents = TextResourceContents(uri="ui://x/1.0.0/a.html", text="<html>", meta={"ui": {}})

    assert resource.meta == {"ui": {"csp": {}}}
    assert contents.meta == {"ui": {}}
    assert "meta" not in resource.model_dump(by_alias=True)
    assert "meta" not in contents.model_dump(by_alias=True)
