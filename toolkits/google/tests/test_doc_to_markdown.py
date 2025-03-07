import pytest

from arcade_google.doc_to_markdown import convert_document_to_markdown


@pytest.mark.asyncio
async def test_convert_document_to_markdown(sample_document_and_expected_formats):
    (sample_document, expected_markdown, _) = sample_document_and_expected_formats
    markdown = convert_document_to_markdown(sample_document)
    assert markdown == expected_markdown
