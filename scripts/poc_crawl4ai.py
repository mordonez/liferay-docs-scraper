#!/usr/bin/env python3
"""POC: extract clean learn.liferay.com Markdown with crawl4ai, no Firecrawl involved.

Setup (crawl4ai needs Python <=3.13 and its own Playwright browsers):
    python3.13 -m venv .venv-crawl4ai
    source .venv-crawl4ai/bin/activate
    pip install crawl4ai
    crawl4ai-setup

Run (from repo root, with the venv activated):
    python3 scripts/poc_crawl4ai.py --capability search --limit 3
    python3 scripts/poc_crawl4ai.py            # 2 URLs per capability, all 6

Why this reaches the same result as the Firecrawl pipeline, without Firecrawl:
  - learn.liferay.com's article template always wraps the real page (breadcrumb,
    sidebar TOC, title, body, resource-type tags) in `<div id="main-content">`,
    and puts the maintenance banner + global footer OUTSIDE it (siblings in the
    page DOM). Scoping the crawl to `css_selector="#main-content"` (crawl4ai's
    CrawlerRunConfig) is a local, free equivalent of Firecrawl's
    only_main_content=true -- and it already excludes the banner/footer that
    scripts/clean_boilerplate.py has to cut out of Firecrawl's output.
  - The remaining chrome (breadcrumb + "Submit Feedback" + sidebar TOC, before
    the real title) has the exact same shape as Firecrawl's header chrome, so
    the same `# [Title](url)` H1 anchor from clean_boilerplate.find_header_cut
    is reused verbatim to cut it. No footer cut is needed here since the
    footer was never fetched in the first place.
  - Output uses the identical frontmatter schema (url, capability, fetched_at,
    content_hash) as scripts/extract_content.py, so files are directly
    comparable to raw/{capability}/*.md.

Writes to raw_crawl4ai_poc/{capability}/{slug}.md (separate from raw/, which
stays the Firecrawl-produced corpus) and prints a diff-style comparison
against the matching raw/ file when one exists.
"""

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

from clean_boilerplate import NotCleanable, find_header_cut
from extract_content import CAPABILITY_PREFIXES, build_frontmatter, slugify

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig

ROOT = Path(__file__).resolve().parent.parent
FILTERED_DIR = ROOT / "reports" / "filtered"
OUT_DIR = ROOT / "raw_crawl4ai_poc"
RAW_DIR = ROOT / "raw"

DEFAULT_CONCURRENCY = 5
DEFAULT_SAMPLE_PER_CAPABILITY = 2


@dataclass
class PocResult:
    url: str
    ok: bool
    path: Path | None = None
    error: str | None = None
    cleaned: bool = False


def clean_main_content(markdown: str) -> str:
    """Cut the breadcrumb/TOC chrome before the real H1. No footer cut needed:
    #main-content never includes the site's global footer."""
    lines = markdown.split("\n")
    header_cut = find_header_cut(lines)  # raises NotCleanable if absent
    cleaned_lines = lines[header_cut:]
    while cleaned_lines and cleaned_lines[-1].strip() == "":
        cleaned_lines.pop()
    return "\n".join(cleaned_lines) + "\n"


async def fetch_one(crawler: AsyncWebCrawler, url: str, capability: str, prefix: str,
                     out_dir: Path, semaphore: asyncio.Semaphore) -> PocResult:
    config = CrawlerRunConfig(css_selector="#main-content", cache_mode=CacheMode.BYPASS)
    async with semaphore:
        try:
            result = await crawler.arun(url=url, config=config)
        except Exception as exc:  # noqa: BLE001 - report any crawl failure
            return PocResult(url=url, ok=False, error=str(exc))

    if not result.success:
        return PocResult(url=url, ok=False, error=f"status={result.status_code}")

    markdown = result.markdown.raw_markdown
    cleaned = False
    try:
        markdown = clean_main_content(markdown)
        cleaned = True
    except NotCleanable as exc:
        return PocResult(url=url, ok=False, error=f"not cleanable: {exc.reason}")

    slug = slugify(url, prefix)
    out_path = out_dir / f"{slug}.md"
    content = build_frontmatter(url, capability, markdown) + markdown
    out_path.write_text(content, encoding="utf-8")
    return PocResult(url=url, ok=True, path=out_path, cleaned=cleaned)


async def run(capabilities: list[str], concurrency: int, limit: int | None) -> list[PocResult]:
    semaphore = asyncio.Semaphore(concurrency)
    results: list[PocResult] = []
    async with AsyncWebCrawler() as crawler:
        for capability in capabilities:
            prefix = CAPABILITY_PREFIXES[capability]
            urls_file = FILTERED_DIR / f"{capability}_urls.txt"
            urls = [u.strip() for u in urls_file.read_text(encoding="utf-8").splitlines() if u.strip()]
            sample = urls[:limit] if limit is not None else urls[:DEFAULT_SAMPLE_PER_CAPABILITY]

            out_dir = OUT_DIR / capability
            out_dir.mkdir(parents=True, exist_ok=True)

            tasks = [fetch_one(crawler, url, capability, prefix, out_dir, semaphore) for url in sample]
            capability_results = await asyncio.gather(*tasks)
            results.extend(capability_results)

            ok = sum(1 for r in capability_results if r.ok)
            print(f"[{capability}] {ok}/{len(capability_results)} ok")
            for r in capability_results:
                status = "ok" if r.ok else f"FAIL ({r.error})"
                print(f"  {r.url} -> {status}")
    return results


def compare_with_firecrawl(results: list[PocResult], capability: str, prefix: str) -> None:
    for r in results:
        if not r.ok or r.path is None:
            continue
        slug = slugify(r.url, prefix)
        firecrawl_path = RAW_DIR / capability / f"{slug}.md"
        if not firecrawl_path.exists():
            continue

        crawl4ai_body = "\n".join(r.path.read_text(encoding="utf-8").split("---\n", 2)[2].split("\n"))
        firecrawl_body = "\n".join(firecrawl_path.read_text(encoding="utf-8").split("---\n", 2)[2].split("\n"))

        def normalize(text: str) -> str:
            return " ".join(text.split())

        match = normalize(crawl4ai_body) == normalize(firecrawl_body)
        print(f"  {slug}: {'MATCH (normalized whitespace)' if match else 'DIFFERS'}"
              f"  [crawl4ai {len(crawl4ai_body)} chars vs firecrawl {len(firecrawl_body)} chars]")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--capability", action="append", choices=list(CAPABILITY_PREFIXES))
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--limit", type=int, default=None, help="URLs per capability (default: 2)")
    args = parser.parse_args()

    capabilities = args.capability or list(CAPABILITY_PREFIXES)
    results = asyncio.run(run(capabilities, args.concurrency, args.limit))

    total_ok = sum(1 for r in results if r.ok)
    print(f"\nTOTAL: {total_ok}/{len(results)} ok")

    print("\nComparación contra raw/ (Firecrawl, ya limpio):")
    offset = 0
    for capability in capabilities:
        prefix = CAPABILITY_PREFIXES[capability]
        n = args.limit if args.limit is not None else DEFAULT_SAMPLE_PER_CAPABILITY
        chunk = results[offset: offset + n]
        offset += n
        if chunk:
            print(f" {capability}:")
            compare_with_firecrawl(chunk, capability, prefix)

    if total_ok < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
