"""Small, dependency-free news search used by both dashboard and claims.

Google News' public RSS feed is deliberately used for the prototype so a
claim check works without adding another paid API credential.  A production
deployment should replace this adapter with a licensed search provider.
"""

from __future__ import annotations

import ipaddress
import socket
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import quote_plus, urljoin, urlparse
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


class _ArticleExtractor(_TextExtractor):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs) -> None:
        super().handle_starttag(tag, attrs)
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        super().handle_endtag(tag)
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            text = " ".join(data.split())
            if text:
                self.title_parts.append(text)
        super().handle_data(data)


class SearchService:
    timeout = httpx.Timeout(8.0, connect=4.0)
    max_article_bytes = 1_000_000
    max_article_chars = 6_000
    max_redirects = 3

    async def search_evidence(self, claim: str, limit: int = 5) -> list[EvidenceItem]:
        input_url = self._extract_url(claim)
        if not input_url:
            return await self._search(claim, limit=limit, model=EvidenceItem)

        article = await self._fetch_url_evidence(input_url)
        query = article.title if article else claim
        news_limit = max(0, limit - 1)
        news = await self._search(query, limit=news_limit, model=EvidenceItem)

        if article:
            return [article, *news]

        parsed = urlparse(input_url)
        unavailable = EvidenceItem(
            title="Page content unavailable",
            url=input_url,
            source=parsed.netloc or "Submitted URL",
            excerpt=(
                "FortiFi could not retrieve this page's text. The models received "
                "the submitted URL and any separately retrieved news evidence only."
            ),
        )
        return [unavailable, *news]

    async def dashboard_news(self, limit: int = 6) -> list[NewsItem]:
        return await self._search("crypto markets finance", limit=limit, model=NewsItem)

    async def _search(self, query: str, limit: int, model):
        url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPError:
            return self._fallback_news(limit, model) if model is NewsItem else []

        try:
            root = ElementTree.fromstring(response.content)
        except ElementTree.ParseError:
            return self._fallback_news(limit, model) if model is NewsItem else []

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

    async def _fetch_url_evidence(self, url: str) -> EvidenceItem | None:
        current_url = url
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
                for _ in range(self.max_redirects + 1):
                    self._validate_public_url(current_url)
                    async with client.stream(
                        "GET",
                        current_url,
                        headers={"User-Agent": "FortiFi/0.1 claim-verification"},
                    ) as response:
                        if response.is_redirect:
                            location = response.headers.get("location")
                            if not location:
                                return None
                            current_url = urljoin(current_url, location)
                            continue

                        response.raise_for_status()
                        content_type = response.headers.get("content-type", "").lower()
                        if not any(kind in content_type for kind in ("text/html", "text/plain")):
                            return None

                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > self.max_article_bytes:
                                return None

                        encoding = response.encoding or "utf-8"
                        text = bytes(body).decode(encoding, errors="replace")
                        title, excerpt = self._extract_article(text, content_type)
                        if not excerpt:
                            return None

                        parsed = urlparse(current_url)
                        return EvidenceItem(
                            title=title or parsed.netloc or "Submitted page",
                            url=current_url,
                            source=parsed.netloc or "Submitted page",
                            excerpt=excerpt[:self.max_article_chars],
                        )
        except (httpx.HTTPError, OSError, UnicodeError, ValueError):
            return None
        return None

    @staticmethod
    def _extract_url(value: str) -> str | None:
        candidate = value.strip()
        parsed = urlparse(candidate)
        if parsed.scheme in {"http", "https"} and parsed.netloc and not any(char.isspace() for char in candidate):
            return candidate
        return None

    @staticmethod
    def _validate_public_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Only public HTTP and HTTPS URLs are supported.")
        if parsed.username or parsed.password:
            raise ValueError("URLs containing credentials are not supported.")

        default_port = 443 if parsed.scheme == "https" else 80
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or default_port, type=socket.SOCK_STREAM)
        if not addresses:
            raise ValueError("URL hostname could not be resolved.")
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                raise ValueError("Private or local network URLs are not supported.")

    @staticmethod
    def _extract_article(value: str, content_type: str) -> tuple[str, str]:
        if "text/plain" in content_type:
            return "", " ".join(value.split())
        parser = _ArticleExtractor()
        parser.feed(value)
        return " ".join(parser.title_parts), " ".join(parser.parts)

    @staticmethod
    def _fallback_news(limit: int, model) -> list[NewsItem]:
        """Keeps the prototype dashboard useful if its public RSS source is blocked.

        These are intentionally labelled briefing links, rather than being
        presented as live headlines. Claim evidence never uses this fallback.
        """
        briefing = [
            ("Crypto market overview", "CoinGecko", "https://www.coingecko.com/en/coins/bitcoin", "Open a current market overview before acting on a headline."),
            ("Digital asset market data", "CoinMarketCap", "https://coinmarketcap.com/", "Review market movements and asset data from the source."),
            ("Federal Reserve news", "Federal Reserve", "https://www.federalreserve.gov/newsevents.htm", "Check primary-source US monetary-policy announcements."),
        ]
        return [
            model(title=title, source=source, url=url, excerpt=excerpt, is_live=False)
            for title, source, url, excerpt in briefing[:limit]
        ]

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
