from unittest.mock import MagicMock, patch

import pytest
from workflows.llm_review import (
    Entity,
    LLMEntities,
    classify_doc,
    extract_entities,
    summarize_doc,
)
from workflows.utils.extract_text import extract_text_from_url


def test_extract_text_from_url():
    url = "http://example.com"
    text = extract_text_from_url(url)
    assert "Example Domain" in text  # Basic check to see if content is fetched


@pytest.mark.asyncio
@patch("workflows.llm_review.get_openai_client")
async def test_summarize_doc(mock_get_openai_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="A summary."))
    ]
    mock_get_openai_client.return_value = mock_client
    result = await summarize_doc("http://example.com")
    assert result == "A summary."
    mock_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
@patch("workflows.llm_review.get_openai_client")
async def test_extract_entities(mock_get_openai_client):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value.output_parsed = LLMEntities(
        entities=[
            Entity(name="Entity1", type="TypeA"),
            Entity(name="Entity2", type="TypeB"),
        ]
    )
    mock_get_openai_client.return_value = mock_client
    result = await extract_entities("doc")
    assert isinstance(result, LLMEntities)
    assert [e.name for e in result.entities] == ["Entity1", "Entity2"]
    mock_client.responses.parse.assert_called_once()


@pytest.mark.asyncio
@patch("workflows.llm_review.get_openai_client")
async def test_classify_doc(mock_get_openai_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="invoice"))
    ]
    mock_get_openai_client.return_value = mock_client
    result = await classify_doc("doc")
    assert result == "invoice"
    mock_client.chat.completions.create.assert_called_once()
