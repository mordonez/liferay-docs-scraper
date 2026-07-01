#!/usr/bin/env python3
"""Build distilled/{capability}/_index.md from "index"-classified raw pages.

Pure text extraction, no API calls. Uses reports/page_classification.json
(produced by classify_pages.py) to find the "index" pages for each
capability, then assembles the navigation hierarchy from how each page's
Markdown is actually structured:

  - A page's body is split into paragraphs (blank-line separated).
  - A paragraph containing exactly one link whose link-text is bold
    (`[**Section**](url)`) starts a new "section" at this level.
  - A paragraph of one or more plain (non-bold) links immediately
    following a section belongs to that section as its local children
    (used only as a fallback -- see below).
  - Orphan link paragraphs with no preceding section become leaf entries.

  Rendering starts at raw/{capability}/index.md's top-level sections. For
  each section, if its URL matches another "index"-classified page, we
  recurse into *that page's own* section structure (its real subpages) --
  this avoids duplicating the flat sibling-links paragraph that sites like
  this one place directly after a section's bold header. If no such page
  was captured (i.e. the section points at a "content" page or an
  uncrawled URL), we fall back to the local children captured inline at
  this level.

Writes one distilled/{capability}/_index.md per capability as a nested
Markdown bullet list (title + URL for every node).
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
DISTILLED_DIR = ROOT / "distilled"
CLASSIFICATION_PATH = ROOT / "reports" / "page_classification.json"

LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
H1_RE = re.compile(r"^#\s*\[([^\]]*)\]\(([^)]*)\)")
MAX_DEPTH = 8


def split_frontmatter(text: str) -> tuple[dict, str]:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text
    try:
        closing_offset = lines[1:].index("---")
    except ValueError:
        return {}, text
    closing_idx = closing_offset + 1
    fm = {}
    for line in lines[1:closing_idx]:
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip().strip('"')
    body = "\n".join(lines[closing_idx + 1 :])
    return fm, body


def clean_text(text: str) -> str:
    return text.replace("*", "").strip()


def is_bold_link_text(text: str) -> bool:
    return text.startswith("**") and text.endswith("**") and len(text) > 4


def parse_sections(body: str, h1_url: str | None, keep_orphans: bool = True) -> list[dict]:
    """Split body into an ordered list of {text, url, local_children} sections.

    keep_orphans controls what happens to link paragraphs that appear before
    any bold-header section: True keeps them as top-level leaf entries (the
    right call for genuine short TOC pages with no bold headers at all, e.g.
    a page that's just a bare bullet list of links). False discards them --
    used for landing-page-style root pages, where such paragraphs are prose
    with inline links, not navigation.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    sections: list[dict] = []
    current: dict | None = None

    for para in paragraphs:
        if H1_RE.match(para):
            continue
        links = [
            (t.strip(), u.strip())
            for t, u in LINK_RE.findall(para)
            if t.strip() and u.strip() and u.strip() != h1_url
        ]
        if not links:
            continue

        if len(links) == 1 and is_bold_link_text(links[0][0]):
            text, url = links[0]
            current = {"text": clean_text(text), "url": url, "local_children": []}
            sections.append(current)
            continue

        if current is None:
            if keep_orphans:
                for text, url in links:
                    sections.append({"text": clean_text(text), "url": url, "local_children": []})
            continue

        for text, url in links:
            entry = (clean_text(text), url)
            if entry not in current["local_children"]:
                current["local_children"].append(entry)

    # De-duplicate top-level sections by URL, preserving first occurrence order.
    seen = set()
    deduped = []
    for section in sections:
        if section["url"] in seen:
            continue
        seen.add(section["url"])
        deduped.append(section)
    return deduped


class IndexPage:
    __slots__ = ("path", "url", "title", "sections")

    def __init__(self, path: Path, keep_orphans: bool = True):
        self.path = path
        text = path.read_text(encoding="utf-8")
        fm, body = split_frontmatter(text)
        self.url = fm.get("url", "")
        h1 = H1_RE.search(body)
        self.title = h1.group(1).strip() if h1 else path.stem
        self.sections = parse_sections(body, self.url, keep_orphans=keep_orphans)


def load_index_pages(capability: str, classification: dict) -> dict[str, IndexPage]:
    by_url: dict[str, IndexPage] = {}
    for entry in classification["index"]:
        if entry["capability"] != capability:
            continue
        page = IndexPage(ROOT / entry["path"])
        by_url[page.url] = page
    return by_url


def render_section(section: dict, index_pages: dict[str, IndexPage],
                    depth: int, visited: set[str], lines: list[str]) -> None:
    indent = "  " * depth
    text, url = section["text"], section["url"]
    page = index_pages.get(url)

    if page is not None and url not in visited and depth < MAX_DEPTH and page.sections:
        visited.add(url)
        lines.append(f"{indent}- **{text}** — {url}")
        for child in page.sections:
            render_section(child, index_pages, depth + 1, visited, lines)
        visited.discard(url)
    elif section["local_children"]:
        lines.append(f"{indent}- **{text}** — {url}")
        for child_text, child_url in section["local_children"]:
            lines.append(f"{indent}  - [{child_text}]({child_url})")
    else:
        lines.append(f"{indent}- [{text}]({url})")


def build_capability_index(capability: str, index_pages: dict[str, IndexPage],
                            classification: dict) -> str | None:
    root_path = RAW_DIR / capability / "index.md"
    if not root_path.exists():
        return None

    root_rel = str(root_path.relative_to(ROOT))
    root_was_classified_index = any(
        e["path"] == root_rel for e in classification["index"] if e["capability"] == capability
    )
    # If raw/{capability}/index.md itself wasn't classified as an "index" page
    # (e.g. it's a prose landing page with inline links, like cloud/index.md),
    # link paragraphs that appear before the first bold-header section are
    # narrative prose, not navigation -- drop them instead of surfacing every
    # inline link as a bogus top-level entry.
    root = IndexPage(root_path, keep_orphans=root_was_classified_index)

    lines = [f"# {root.title}", "", f"Source: {root.url}", ""]
    visited = {root.url}
    for section in root.sections:
        render_section(section, index_pages, 0, visited, lines)
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--classification", default=str(CLASSIFICATION_PATH),
        help="Path to page_classification.json (from classify_pages.py).",
    )
    parser.add_argument(
        "capabilities", nargs="*",
        help="Capabilities to build nav indexes for (default: all found in classification report).",
    )
    args = parser.parse_args()

    classification = json.loads(Path(args.classification).read_text(encoding="utf-8"))
    all_capabilities = sorted({e["capability"] for e in classification["index"]})
    capabilities = args.capabilities or all_capabilities

    for capability in capabilities:
        index_pages = load_index_pages(capability, classification)
        content = build_capability_index(capability, index_pages, classification)
        if content is None:
            print(f"{capability}: no raw/{capability}/index.md found, skipped")
            continue
        out_dir = DISTILLED_DIR / capability
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "_index.md"
        out_path.write_text(content, encoding="utf-8")
        print(f"{capability}: wrote {out_path.relative_to(ROOT)} ({len(index_pages)} index pages folded in)")


if __name__ == "__main__":
    main()
