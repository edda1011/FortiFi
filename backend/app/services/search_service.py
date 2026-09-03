"""Small, dependency-free news search used by both dashboard and claims.

Google News' public RSS feed is deliberately used for the prototype so a
claim check works without adding another paid API credential.  A production
deployment should replace this adapter with a licensed search provider.
"""

from __future__ import annotations

from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import quote_plus, urlparse
from xml.etree import ElementTree

import httpx

from app.schemas.analysis import EvidenceItem, NewsItem


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._ignored = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript"}:
            self._ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._ignored:
            self._ignored -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)


class SearchService:
    timeout = httpx.Timeout(8.0, connect=4.0)

    async def search_evidence(self, claim: str, limit: int = 5) -> list[EvidenceItem]:
        return await self._search(claim, limit=limit, model=EvidenceItem)

    async def dashboard_news(self, limit: int = 6) -> list[NewsItem]:
        return await self._search("crypto markets finance", limit=limit, model=NewsItem)

    async def _search(self, query: str, limit: int, model):
        url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPError:
            # Search failure should not prevent an evidence-aware model from
            # explicitly reporting that evidence could not be retrieved.
            return []

        try:
            root = ElementTree.fromstring(response.content)
        except ElementTree.ParseError:
            return []

        results = []
        for item in root.findall("./channel/item")[:limit]:
            title = unescape(item.findtext("title") or "Untitled source")
            link = item.findtext("link") or ""
            source = item.findtext("source") or urlparse(link).netloc or "News source"
            raw_description = item.findtext("description") or ""
            excerpt = self._to_text(raw_description)
            pub_date = item.findtext("pubDate")
            published_at = self._normalize_date(pub_date)
            if link:
                results.append(model(title=title, url=link, source=source, excerpt=excerpt[:700], published_at=published_at))
        return results

    @staticmethod
    def _to_text(value: str) -> str:
        parser = _TextExtractor()
        parser.feed(value)
        return " ".join(parser.parts)

    @staticmethod
    def _normalize_date(value: str | None) -> str | None:
        if not value:
            return None
        try:
            return parsedate_to_datetime(value).isoformat()
        except (TypeError, ValueError):
            return value
