"""Web search service — multi-backend web search.

Uses Bing (primary) -> Sogou (fallback) -> Yandex (fallback) for web search.
DuckDuckGo is unreliable in Docker environments due to DNS issues.
"""
import logging
import re
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

SEARCH_TIMEOUT = 15


@dataclass
class WebSearchResult:
    """Single web search result."""
    title: str = ""
    url: str = ""
    snippet: str = ""
    source: str = ""


class WebSearchService:
    """Search the web via multiple backends with automatic fallback."""

    async def search(self, query: str, max_results: int = 5) -> list[WebSearchResult]:
        """Search the web for *query*.

        Tries Bing -> Sogou -> Yandex in order. Returns up to *max_results*
        results. On any failure returns an empty list so callers never crash.
        """
        if not query or not query.strip():
            return []

        # Try backends in order
        for backend_name, backend_fn in [
            ("bing", self._search_bing),
            ("sogou", self._search_sogou),
            ("yandex", self._search_yandex),
        ]:
            try:
                results = await backend_fn(query, max_results)
                if results:
                    logger.info("Search succeeded via %s: %d results", backend_name, len(results))
                    return results
            except Exception as e:
                logger.warning("Backend %s failed: %s", backend_name, e)
                continue

        logger.error("All search backends failed for query: %s", query[:50])
        return []

    async def _search_bing(self, query: str, max_results: int) -> list[WebSearchResult]:
        """Scrape Bing search results using BeautifulSoup."""
        from bs4 import BeautifulSoup
        results = []
        async with httpx.AsyncClient(
            timeout=SEARCH_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"},
        ) as client:
            resp = await client.get(f"https://www.bing.com/search?q={query}")
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for item in soup.select("li.b_algo")[:max_results]:
                a_tag = item.select_one("h2 a")
                if not a_tag:
                    continue
                url = a_tag.get("href", "")
                title = a_tag.get_text(strip=True)
                snippet_tag = item.select_one("p, .b_caption p, .b_algoSlug")
                snippet = snippet_tag.get_text(strip=True)[:300] if snippet_tag else ""
                if title and url.startswith("http"):
                    results.append(WebSearchResult(title=title, url=url, snippet=snippet, source="bing"))

        return results

    async def _search_sogou(self, query: str, max_results: int) -> list[WebSearchResult]:
        """Scrape Sogou search results using BeautifulSoup."""
        from bs4 import BeautifulSoup
        results = []
        async with httpx.AsyncClient(
            timeout=SEARCH_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"},
        ) as client:
            resp = await client.get(f"https://www.sogou.com/web?query={query}")
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for item in soup.select("div.vrwrap, div.rb")[:max_results]:
                a_tag = item.select_one("h3 a, a.vr-title, a.ft")
                if not a_tag:
                    continue
                url = a_tag.get("href", "")
                title = a_tag.get_text(strip=True)
                snippet_tag = item.select_one("p.space-txt, div.str-text-info, .star-wiki")
                snippet = snippet_tag.get_text(strip=True)[:300] if snippet_tag else ""
                if title and "http" in url:
                    results.append(WebSearchResult(title=title, url=url, snippet=snippet, source="sogou"))

        return results

    async def _search_yandex(self, query: str, max_results: int) -> list[WebSearchResult]:
        """Scrape Yandex search results using BeautifulSoup."""
        from bs4 import BeautifulSoup
        results = []
        async with httpx.AsyncClient(
            timeout=SEARCH_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"},
        ) as client:
            resp = await client.get(f"https://yandex.com/search/?text={query}")
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for item in soup.select("li.serp-item, div.Organic")[:max_results]:
                a_tag = item.select_one("a.Link, a.OrganicTitle-Link")
                if not a_tag:
                    continue
                url = a_tag.get("href", "")
                title = a_tag.get_text(strip=True)
                snippet_tag = item.select_one("span.OrganicText, div.OrganicText")
                snippet = snippet_tag.get_text(strip=True)[:300] if snippet_tag else ""
                if title and url.startswith("http"):
                    results.append(WebSearchResult(title=title, url=url, snippet=snippet, source="yandex"))

        return results
