"""Web tools: search and fetch.

Two tools:
  web_search(query)   - search the web via DuckDuckGo
  web_fetch(url)      - fetch a URL and extract clean text

No API keys. No registration. Uses DuckDuckGo's HTML endpoint
(designed for lightweight clients) and html2text for readability.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.hidden += 1
        if not self.hidden and tag in {"p", "div", "br", "h1", "h2", "h3", "li", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"}:
            self.hidden = max(0, self.hidden - 1)
        if not self.hidden and tag in {"p", "div", "li", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)

from typing import Any, Dict, List

from _base.tool import Tool
from guard.contract import ToolEffect


class WebSearch(Tool):
    name = "web_search"
    description = (
        "Search the web. Returns a list of results with title, URL, "
        "and snippet. Use for research when memory and the model "
        "do not already know the answer."
    )
    parameters = {
        "query": "the search query string",
        "max_results": "optional, default 8",
    }

    def effects(self, args: Dict[str, Any]) -> tuple[ToolEffect, ...]:
        query = (args.get("query") or "").strip()
        if not query:
            raise ValueError("query is required")

        return (
            ToolEffect(
                action="network",
                target="web-search",
                scope="service",
            ),
        )

    def call(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = (args.get("query") or "").strip()
        if not query:
            return {"ok": False, "data": None, "error": "query is required"}

        max_results = int(args.get("max_results") or 8)

        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return {
                "ok": False,
                "data": None,
                "error": "duckduckgo-search is not installed. "
                         "Run: pip3 install duckduckgo-search",
            }

        try:
            with DDGS() as ddgs:
                raw = list(ddgs.text(query, max_results=max_results))
        except Exception as e:
            return {"ok": False, "data": None, "error": f"search failed: {e}"}

        results = []
        for r in raw:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            })

        return {
            "ok": True,
            "data": {
                "query": query,
                "count": len(results),
                "results": results,
            },
            "error": None,
        }


class WebFetch(Tool):
    name = "web_fetch"
    description = (
        "Fetch a URL and return its main text content as clean "
        "markdown. Strips navigation, ads, and scripts."
    )
    parameters = {
        "url": "the full URL to fetch",
        "max_chars": "optional; omit for the default 20000-character preview, or use null for the full response",
    }

    def effects(self, args: Dict[str, Any]) -> tuple[ToolEffect, ...]:
        url = (args.get("url") or "").strip()
        if not url:
            raise ValueError("url is required")

        if not re.match(r"^https?://", url):
            url = "https://" + url

        return (
            ToolEffect(
                action="network",
                target=url,
                scope="service",
            ),
        )

    def call(self, args: Dict[str, Any]) -> Dict[str, Any]:
        url = (args.get("url") or "").strip()
        if not url:
            return {"ok": False, "data": None, "error": "url is required"}

        if not re.match(r"^https?://", url):
            url = "https://" + url

        max_chars = args.get("max_chars", 20000)
        if max_chars is not None:
            max_chars = max(1, int(max_chars))

        try:
            import requests
        except ImportError:
            return {
                "ok": False,
                "data": None,
                "error": "requests is not installed. Run: pip3 install requests",
            }

        try:
            resp = requests.get(
                url,
                timeout=20,
                stream=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0 Safari/537.36"
                    ),
                },
            )
            resp.raise_for_status()
        except Exception as e:
            return {"ok": False, "data": None, "error": f"fetch failed: {e}"}

        try:
            chunks = []
            try:
                for chunk in resp.iter_content(16384):
                    chunks.append(chunk)
            finally:
                resp.close()
            raw = b"".join(chunks).decode(resp.encoding or "utf-8", errors="replace")
            content_type = resp.headers.get("Content-Type", "").lower()
            if "html" in content_type:
                parser = _TextExtractor()
                parser.feed(raw)
                text = "".join(parser.parts)
            elif content_type.startswith("text/") or any(kind in content_type for kind in ("json", "xml")):
                text = raw
            else:
                raise ValueError("URL must serve text or HTML; binary documents require extraction")
        except Exception as exc:
            return {"ok": False, "data": None, "error": str(exc)}

        # Collapse excess whitespace.
        text = re.sub(r"\n{3,}", "\n\n", text).strip()

        truncated = False
        if max_chars is not None and len(text) > max_chars:
            text = text[:max_chars]
            truncated = True

        return {
            "ok": True,
            "data": {
                "url": url,
                "chars": len(text),
                "truncated": truncated,
                "text": text,
            },
            "error": None,
        }


from .browser import BrowserInteract

TOOLS = [WebSearch, WebFetch, BrowserInteract]
