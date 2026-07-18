"""Webpage extractor — pulls structured data from pages.

Extracts:
- Title, description, metadata
- Main text content
- Links with context
- Buttons and interactive elements
- Forms with field details
- Tables as structured data
- Images with alt text

Returns clean, structured data ready for LLM consumption.
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

log = logging.getLogger("jarvis.browser.extractor")


@dataclass
class ExtractedLink:
    """A link found on a page."""
    text: str = ""
    url: str = ""
    is_external: bool = False

    def to_dict(self) -> dict:
        return {"text": self.text[:200], "url": self.url, "is_external": self.is_external}


@dataclass
class ExtractedButton:
    """A button or clickable element."""
    text: str = ""
    selector: str = ""
    element_type: str = ""  # button, link, input[type=submit]

    def to_dict(self) -> dict:
        return {"text": self.text[:100], "selector": self.selector, "type": self.element_type}


@dataclass
class ExtractedForm:
    """A form found on a page."""
    action: str = ""
    method: str = "GET"
    fields: list[dict] = None

    def __post_init__(self):
        if self.fields is None:
            self.fields = []

    def to_dict(self) -> dict:
        return {"action": self.action, "method": self.method, "fields": self.fields}


@dataclass
class ExtractedTable:
    """A table found on a page."""
    headers: list[str] = None
    rows: list[list[str]] = None

    def __post_init__(self):
        if self.headers is None:
            self.headers = []
        if self.rows is None:
            self.rows = []

    def to_dict(self) -> dict:
        return {"headers": self.headers, "rows": self.rows[:20]}


@dataclass
class PageData:
    """Complete structured data extracted from a webpage."""
    url: str = ""
    title: str = ""
    description: str = ""
    content: str = ""  # main text content
    links: list[ExtractedLink] = None
    buttons: list[ExtractedButton] = None
    forms: list[ExtractedForm] = None
    tables: list[ExtractedTable] = None
    metadata: dict = None
    word_count: int = 0
    language: str = ""

    def __post_init__(self):
        if self.links is None:
            self.links = []
        if self.buttons is None:
            self.buttons = []
        if self.forms is None:
            self.forms = []
        if self.tables is None:
            self.tables = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "content": self.content[:5000],
            "word_count": self.word_count,
            "language": self.language,
            "link_count": len(self.links),
            "links": [l.to_dict() for l in self.links[:30]],
            "button_count": len(self.buttons),
            "buttons": [b.to_dict() for b in self.buttons[:20]],
            "form_count": len(self.forms),
            "forms": [f.to_dict() for f in self.forms[:5]],
            "table_count": len(self.tables),
            "tables": [t.to_dict() for t in self.tables[:5]],
            "metadata": self.metadata,
        }

    def to_llm_context(self, max_chars: int = 4000) -> str:
        """Format as context string for LLM consumption."""
        parts = []

        if self.title:
            parts.append(f"Title: {self.title}")
        if self.description:
            parts.append(f"Description: {self.description}")
        if self.url:
            parts.append(f"URL: {self.url}")

        if self.content:
            content = self.content[:max_chars]
            parts.append(f"\n--- Page Content ---\n{content}")

        if self.tables:
            parts.append(f"\n--- Tables ({len(self.tables)}) ---")
            for table in self.tables[:3]:
                if table.headers:
                    parts.append("  " + " | ".join(table.headers[:6]))
                for row in table.rows[:5]:
                    parts.append("  " + " | ".join(str(c)[:30] for c in row[:6]))

        if self.links:
            external = [l for l in self.links if l.is_external][:10]
            if external:
                parts.append(f"\n--- Key Links ({len(external)}) ---")
                for link in external:
                    parts.append(f"  [{link.text[:50]}]({link.url})")

        return "\n".join(parts)[:max_chars]


class PageExtractor:
    """Extracts structured data from HTML pages.

    Can work with:
    - Raw HTML strings
    - Playwright page objects
    - Accessibility snapshots

    Usage:
        extractor = PageExtractor()
        data = await extractor.extract_from_html(html, url="https://example.com")
        context = data.to_llm_context()
    """

    async def extract_from_html(self, html: str, url: str = "") -> PageData:
        """Extract structured data from raw HTML."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        base_domain = urlparse(url).netloc if url else ""

        data = PageData(url=url)

        # Title
        title_tag = soup.find("title")
        if title_tag:
            data.title = title_tag.get_text(strip=True)

        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            data.description = meta_desc.get("content", "")

        # Meta tags
        for meta in soup.find_all("meta"):
            name = meta.get("name", meta.get("property", ""))
            content = meta.get("content", "")
            if name and content:
                data.metadata[name] = content[:200]

        # Language
        html_tag = soup.find("html")
        if html_tag:
            data.language = html_tag.get("lang", "")

        # Main content — try article/main first, fallback to body
        main = soup.find("article") or soup.find("main") or soup.find("body")
        if main:
            # Remove scripts and styles
            for tag in main.find_all(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            data.content = main.get_text(separator="\n", strip=True)
            data.word_count = len(data.content.split())

        # Links
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            text = a_tag.get_text(strip=True)
            if not text or len(text) < 2:
                continue

            full_url = urljoin(url, href)
            is_external = bool(base_domain) and urlparse(full_url).netloc != base_domain

            data.links.append(ExtractedLink(
                text=text[:200],
                url=full_url,
                is_external=is_external,
            ))

        # Buttons
        for btn in soup.find_all(["button", "input"]):
            text = btn.get("value", "") or btn.get_text(strip=True)
            if not text:
                continue
            selector = self._build_selector(btn)
            elem_type = btn.name
            if btn.get("type"):
                elem_type = f"{btn.name}[type={btn['type']}]"
            data.buttons.append(ExtractedButton(
                text=text[:100], selector=selector, element_type=elem_type,
            ))

        # Forms
        for form in soup.find_all("form"):
            form_data = ExtractedForm(
                action=urljoin(url, form.get("action", "")),
                method=form.get("method", "GET").upper(),
            )
            for field in form.find_all(["input", "select", "textarea"]):
                form_data.fields.append({
                    "type": field.get("type", field.name),
                    "name": field.get("name", ""),
                    "placeholder": field.get("placeholder", ""),
                    "required": field.get("required") is not None,
                })
            data.forms.append(form_data)

        # Tables
        for table in soup.find_all("table"):
            table_data = ExtractedTable()
            headers = []
            for th in table.find_all("th"):
                headers.append(th.get_text(strip=True)[:100])
            table_data.headers = headers

            for tr in table.find_all("tr")[len(headers) and 1 or 0:]:
                row = []
                for td in tr.find_all(["td", "th"]):
                    row.append(td.get_text(strip=True)[:100])
                if row:
                    table_data.rows.append(row)

            if table_data.headers or table_data.rows:
                data.tables.append(table_data)

        return data

    async def extract_from_snapshot(self, snapshot: dict) -> PageData:
        """Extract from a Playwright accessibility snapshot (dict)."""
        data = PageData(
            url=snapshot.get("url", ""),
            title=snapshot.get("title", ""),
        )

        # Extract from snapshot nodes
        nodes = snapshot.get("nodes", [])
        for node in nodes:
            node_type = node.get("type", "")
            text = node.get("text", "")

            if node_type == "link" and text:
                data.links.append(ExtractedLink(
                    text=text[:200],
                    url=node.get("url", ""),
                    is_external=True,
                ))
            elif node_type in ("button", "submit") and text:
                data.buttons.append(ExtractedButton(
                    text=text[:100],
                    selector=node.get("selector", ""),
                    element_type=node_type,
                ))

        return data

    def _build_selector(self, element) -> str:
        """Build a CSS selector for an element."""
        parts = []
        if element.name:
            parts.append(element.name)
        if element.get("id"):
            parts.append(f"#{element['id']}")
        elif element.get("class"):
            classes = element["class"][:2]  # first 2 classes
            parts.append("." + ".".join(classes))
        return "".join(parts)


# Module-level singleton
extractor = PageExtractor()
