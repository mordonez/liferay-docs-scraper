#!/usr/bin/env python3
"""Weekly from-scratch refresh of the learn.liferay.com/w/dxp corpus, crawl4ai-only.

No Firecrawl involved anywhere in this script -- it replaces both the old
`firecrawl map` discovery step and scripts/extract_content.py's scraping step
with a single crawl4ai deep crawl:

  - A BFS deep crawl starts at /w/dxp/index and follows every internal link
    under /w/dxp/*. crawl4ai extracts links from the FULL page regardless of
    css_selector, so this single crawl gets us both (a) the complete current
    set of URLs on the site (what `firecrawl map` used to give us) and (b)
    each page's clean #main-content Markdown (what extract_content.py used to
    fetch separately) in one visit per page.
  - Each page is classified with scripts/filter_urls.py's classify_url (same
    capability prefixes + self-hosted prune rules as before) and, if in
    scope, cleaned with the same header-cut logic validated in
    scripts/poc_crawl4ai.py, then written to raw/{capability}/{slug}.md.
  - Because every run starts from zero, a page that existed last run but
    isn't found this run (removed from the site, or now out of scope/pruned)
    is *quarantined*: its file moves to raw/_removed/{capability}/{slug}.md
    instead of being deleted, and the move is logged to
    reports/filtered/removed_log.jsonl. If a capability's discovered count
    drops implausibly (crawl likely failed partway), quarantine for that
    capability is skipped and flagged for manual review instead of trusting
    a possibly-broken run.
  - reports/filtered/{capability}_urls.txt, self-hosted_pruned.txt and
    summary.json are regenerated from this run's live results, so they always
    reflect the current corpus (same format scripts/filter_urls.py produces).

Setup: see scripts/poc_crawl4ai.py header (crawl4ai + Playwright browsers in
a Python 3.13 venv). Run with that venv activated:
    python3 scripts/crawl4ai_pipeline.py
    python3 scripts/crawl4ai_pipeline.py --max-pages 200   # smaller test run
"""

import argparse
import asyncio
import json
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from clean_boilerplate import NotCleanable, find_header_cut
from extract_content import build_frontmatter, slugify
from filter_urls import (
    CAPABILITIES,
    SELF_HOSTED_PRUNE_RULES,
    classify_url,
    normalize,
)

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DomainFilter, FilterChain, URLPatternFilter

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
REMOVED_DIR = RAW_DIR / "_removed"
FILTERED_DIR = ROOT / "reports" / "filtered"
REMOVED_LOG = FILTERED_DIR / "removed_log.jsonl"

SEED_URL = "https://learn.liferay.com/w/dxp/index"
ALLOWED_DOMAIN = "learn.liferay.com"
URL_SCOPE_PATTERN = "*/w/dxp*"

DEFAULT_MAX_DEPTH = 12
DEFAULT_MAX_PAGES = 3000
# If a capability's freshly discovered URL count falls below this fraction of
# its previous count, treat the run as suspect and skip quarantining orphans
# for that capability rather than mass-deleting good content on a bad crawl.
QUARANTINE_SAFETY_RATIO = 0.5


@dataclass
class PageOutcome:
    url: str
    capability: str
    slug: str
    status: str  # "new" | "updated" | "unchanged" | "not_cleaned"


@dataclass
class RunStats:
    discovered_total: int = 0
    fetch_failed: list[str] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)
    pruned: list[tuple] = field(default_factory=list)
    outcomes: dict = field(default_factory=lambda: {name: [] for name in CAPABILITIES})


def clean_main_content(markdown: str) -> str:
    """Header-only chrome cut (breadcrumb/TOC before the real H1). No footer
    cut needed: css_selector="#main-content" already excludes the site
    footer, unlike Firecrawl's only_main_content output."""
    lines = markdown.split("\n")
    header_cut = find_header_cut(lines)
    cleaned_lines = lines[header_cut:]
    while cleaned_lines and cleaned_lines[-1].strip() == "":
        cleaned_lines.pop()
    return "\n".join(cleaned_lines) + "\n"


def read_existing_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.startswith("content_hash:"):
                return line.strip()
    return None


def build_deep_crawl_config(max_depth: int, max_pages: int) -> CrawlerRunConfig:
    filter_chain = FilterChain([
        DomainFilter(allowed_domains=[ALLOWED_DOMAIN]),
        URLPatternFilter(patterns=[URL_SCOPE_PATTERN]),
    ])
    strategy = BFSDeepCrawlStrategy(
        max_depth=max_depth, filter_chain=filter_chain, max_pages=max_pages, include_external=False,
    )
    return CrawlerRunConfig(
        deep_crawl_strategy=strategy,
        css_selector="#main-content",
        cache_mode=CacheMode.BYPASS,
        stream=True,
        verbose=False,
    )


async def run_crawl(max_depth: int, max_pages: int) -> RunStats:
    stats = RunStats()
    config = build_deep_crawl_config(max_depth, max_pages)

    async with AsyncWebCrawler() as crawler:
        stream = await crawler.arun(url=SEED_URL, config=config)
        async for result in stream:
            url = normalize(result.url)

            if not result.success:
                stats.fetch_failed.append(url)
                continue

            stats.discovered_total += 1
            classification = classify_url(url)
            capability = classification["capability"]

            if capability is None:
                if not classification["known_out_of_scope"]:
                    stats.unmatched.append(url)
                continue

            if classification["prune_reason"] is not None:
                stats.pruned.append((url, classification["prune_reason"]))
                continue

            prefix = CAPABILITIES[capability]
            slug = slugify(url, prefix)
            out_dir = RAW_DIR / capability
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{slug}.md"

            markdown = result.markdown.raw_markdown
            try:
                markdown = clean_main_content(markdown)
            except NotCleanable:
                status = "not_cleaned"
                content = build_frontmatter(url, capability, markdown) + markdown
                out_path.write_text(content, encoding="utf-8")
                stats.outcomes[capability].append(PageOutcome(url, capability, slug, status))
                continue

            new_content = build_frontmatter(url, capability, markdown) + markdown
            old_hash_line = read_existing_hash(out_path)
            existed_before = out_path.exists()
            out_path.write_text(new_content, encoding="utf-8")
            new_hash_line = read_existing_hash(out_path)

            if not existed_before:
                status = "new"
            elif old_hash_line == new_hash_line:
                status = "unchanged"
            else:
                status = "updated"
            stats.outcomes[capability].append(PageOutcome(url, capability, slug, status))

    return stats


def quarantine_orphans(stats: RunStats) -> dict:
    """Move raw/{capability}/*.md files that this run didn't touch to
    raw/_removed/{capability}/, unless the capability's count dropped so
    much it looks like a broken run rather than real removals."""
    quarantined: dict[str, list[str]] = {name: [] for name in CAPABILITIES}
    skipped_capabilities: list[str] = []

    for capability in CAPABILITIES:
        out_dir = RAW_DIR / capability
        if not out_dir.exists():
            continue

        # A "not_cleaned" page still got its file (re)written this run, so it
        # counts as present -- only files untouched this run are orphans.
        current_slugs = {o.slug for o in stats.outcomes[capability]}
        on_disk = {p.stem for p in out_dir.glob("*.md")}
        orphans = on_disk - current_slugs

        previous_count = len(on_disk)
        new_count = len(current_slugs)
        if previous_count > 0 and new_count < QUARANTINE_SAFETY_RATIO * previous_count:
            skipped_capabilities.append(capability)
            continue

        if not orphans:
            continue

        removed_dir = REMOVED_DIR / capability
        removed_dir.mkdir(parents=True, exist_ok=True)
        removed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with REMOVED_LOG.open("a", encoding="utf-8") as log:
            for slug in sorted(orphans):
                src = out_dir / f"{slug}.md"
                dst = removed_dir / f"{slug}.md"
                shutil.move(str(src), str(dst))
                quarantined[capability].append(slug)
                log.write(json.dumps({"capability": capability, "slug": slug, "removed_at": removed_at}) + "\n")

    return {"quarantined": quarantined, "skipped_capabilities": skipped_capabilities}


def write_filtered_reports(stats: RunStats) -> None:
    FILTERED_DIR.mkdir(parents=True, exist_ok=True)

    for capability in CAPABILITIES:
        urls = sorted(o.url for o in stats.outcomes[capability])
        (FILTERED_DIR / f"{capability}_urls.txt").write_text("\n".join(urls) + "\n", encoding="utf-8")

    pruned_lines = [f"{url}\t# {reason}" for url, reason in sorted(stats.pruned)]
    (FILTERED_DIR / "self-hosted_pruned.txt").write_text(
        "\n".join(pruned_lines) + ("\n" if pruned_lines else ""), encoding="utf-8",
    )

    prune_counts = {label: 0 for label, _ in SELF_HOSTED_PRUNE_RULES}
    for _, reason in stats.pruned:
        prune_counts[reason] += 1

    summary = {
        "capabilities": {
            name: {"unique_urls": len(stats.outcomes[name])} for name in CAPABILITIES
        },
        "self_hosted_pruned": {"total": len(stats.pruned), "by_rule": prune_counts},
        "total_in_scope": sum(len(stats.outcomes[name]) for name in CAPABILITIES),
        "discovered_total": stats.discovered_total,
        "fetch_failed_count": len(stats.fetch_failed),
        "unmatched_count": len(stats.unmatched),
    }
    (FILTERED_DIR / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def print_summary(stats: RunStats, quarantine_result: dict) -> None:
    print(f"\nTotal descubierto bajo /w/dxp: {stats.discovered_total}")
    if stats.fetch_failed:
        print(f"Fallos de fetch: {len(stats.fetch_failed)}")
        for url in stats.fetch_failed:
            print(f"  - {url}")

    print("\nPor capability (nuevas / actualizadas / sin cambios / no limpiadas):")
    total_in_scope = 0
    for capability, outcomes in stats.outcomes.items():
        new = sum(1 for o in outcomes if o.status == "new")
        updated = sum(1 for o in outcomes if o.status == "updated")
        unchanged = sum(1 for o in outcomes if o.status == "unchanged")
        not_cleaned = sum(1 for o in outcomes if o.status == "not_cleaned")
        total_in_scope += len(outcomes)
        print(f"  {capability:12s}: {len(outcomes):4d} total  "
              f"({new} nuevas, {updated} actualizadas, {unchanged} sin cambios, {not_cleaned} no limpiadas)")
    print(f"\nTotal en scope: {total_in_scope}")

    print(f"\nSelf-hosted podadas: {len(stats.pruned)}")

    quarantined = quarantine_result["quarantined"]
    total_quarantined = sum(len(v) for v in quarantined.values())
    print(f"\nEn cuarentena (ya no existen/no encajan en scope): {total_quarantined}")
    for capability, slugs in quarantined.items():
        if slugs:
            print(f"  {capability}: {len(slugs)}")
            for slug in slugs:
                print(f"    - {slug}")

    if quarantine_result["skipped_capabilities"]:
        print("\nADVERTENCIA: cuarentena omitida por caída sospechosa de conteo "
              "(posible crawl incompleto), revisar a mano:")
        for capability in quarantine_result["skipped_capabilities"]:
            print(f"  - {capability}")

    if stats.unmatched:
        print(f"\nURLs raras (ni en scope ni en descartadas conocidas), {len(stats.unmatched)}:")
        for url in stats.unmatched:
            print(f"  {url}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    args = parser.parse_args()

    stats = asyncio.run(run_crawl(args.max_depth, args.max_pages))
    quarantine_result = quarantine_orphans(stats)
    write_filtered_reports(stats)
    print_summary(stats, quarantine_result)

    if stats.fetch_failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
