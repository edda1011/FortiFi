import asyncio
import socket
from unittest.mock import AsyncMock

import pytest

from app.schemas.analysis import EvidenceItem
from app.services.search_service import SearchService


def test_extract_url_accepts_only_a_complete_url():
    service = SearchService()

    assert service._extract_url("https://example.com/article") == "https://example.com/article"
    assert service._extract_url("Read https://example.com/article") is None
    assert service._extract_url("example.com/article") is None


def test_extract_article_removes_scripts_and_reads_title():
    title, excerpt = SearchService._extract_article(
        "<html><head><title>Market update</title><script>ignore me</script></head>"
        "<body><article>Bitcoin rose after the announcement.</article></body></html>",
        "text/html",
    )

    assert title == "Market update"
    assert "Bitcoin rose" in excerpt
    assert "ignore me" not in excerpt


def test_validate_public_url_blocks_private_addresses(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))],
    )

    with pytest.raises(ValueError, match="Private or local"):
        SearchService._validate_public_url("http://example.test")


def test_url_evidence_is_placed_before_news():
    async def run():
        service = SearchService()
        article = EvidenceItem(
            title="Article title",
            url="https://example.com/article",
            source="example.com",
            excerpt="Article body",
        )
        news = EvidenceItem(
            title="Related report",
            url="https://news.example/report",
            source="News",
            excerpt="Related evidence",
        )
        service._fetch_url_evidence = AsyncMock(return_value=article)
        service._search = AsyncMock(return_value=[news])

        result = await service.search_evidence("https://example.com/article")
        return result, service

    result, service = asyncio.run(run())

    assert len(result) == 2
    assert result[0].title == "Article title"
    assert result[1].title == "Related report"
    service._search.assert_awaited_once_with("Article title", limit=4, model=EvidenceItem)


def test_unavailable_url_is_disclosed_to_models_and_ui():
    async def run():
        service = SearchService()
        service._fetch_url_evidence = AsyncMock(return_value=None)
        service._search = AsyncMock(return_value=[])
        return await service.search_evidence("https://x.com/example/status/123")

    result = asyncio.run(run())

    assert result[0].title == "Page content unavailable"
    assert "could not retrieve" in result[0].excerpt
