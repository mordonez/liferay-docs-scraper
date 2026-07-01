#!/usr/bin/env python3
"""Weekly from-scratch refresh of the learn.liferay.com/w/dxp corpus, crawl4ai-only.

A single crawl4ai deep crawl handles both URL discovery and content
extraction:

  - A BFS deep crawl starts at /w/dxp/index and follows every internal link
    under /w/dxp/*. crawl4ai extracts links from the FULL page regardless of
    css_selector, so this single crawl gets us both (a) the complete current
    set of URLs on the site and (b) each page's Markdown scoped to
    CONTENT_SELECTOR, in one visit per page. That selector (see below) is
    precise enough that no further chrome-stripping is needed -- what
    crawl4ai returns is already the final page content.
  - Each page is classified with scripts/filter_urls.py's classify_url
    (capability prefixes + self-hosted prune rules) and, if in scope,
    written to raw/{capability}/{slug}.md.
  - Because every run starts from zero, a page that existed last run but
    isn't found this run (removed from the site, or now out of scope/pruned)
    is a *candidate* for quarantine -- but BFS link-following can miss a page
    that's still live (no longer linked from anywhere our crawl reached,
    while still resolving directly), so before quarantining anything we do a
    direct HTTP check on each candidate's own URL. Only a confirmed non-200
    gets quarantined (moved to raw/_removed/{capability}/{slug}.md, logged to
    reports/filtered/removed_log.jsonl); anything that still responds, or
    that we simply couldn't reach to check, is left in place and flagged for
    manual review instead. If a capability's discovered count drops
    implausibly (crawl likely failed partway), quarantine for that capability
    is skipped entirely and flagged for manual review instead of trusting a
    possibly-broken run.
  - reports/filtered/{capability}_urls.txt, self-hosted_pruned.txt and
    summary.json are regenerated from this run's live results, so they always
    reflect the current corpus (same format scripts/filter_urls.py produces).

Setup (crawl4ai needs Python <=3.13 and its own Playwright browsers):
    python3.13 -m venv .venv-crawl4ai
    source .venv-crawl4ai/bin/activate
    pip install crawl4ai
    crawl4ai-setup

Run (from repo root, with that venv activated):
    python3 scripts/crawl4ai_pipeline.py
    python3 scripts/crawl4ai_pipeline.py --max-pages 200   # smaller test run
"""

import argparse
import asyncio
import json
import shutil
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from filter_urls import (
    CAPABILITIES,
    SELF_HOSTED_PRUNE_RULES,
    build_frontmatter,
    classify_url,
    normalize,
    slugify,
)

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, ContentTypeFilter, DomainFilter, FilterChain, URLPatternFilter

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
REMOVED_DIR = RAW_DIR / "_removed"
FILTERED_DIR = ROOT / "reports" / "filtered"
REMOVED_LOG = FILTERED_DIR / "removed_log.jsonl"

SEED_URL = "https://learn.liferay.com/w/dxp/index"
ALLOWED_DOMAIN = "learn.liferay.com"
URL_SCOPE_PATTERN = "*/w/dxp*"
# learn.liferay.com's article template puts the breadcrumb, sidebar TOC, and
# the actual article body all inside #main-content, with the maintenance
# banner and global footer outside it. .learn-article-content is scoped
# tighter still: just the title, body, and resource-type tags -- no
# breadcrumb/TOC/"Submit Feedback" chrome to strip afterward.
CONTENT_SELECTOR = ".learn-article-content"

DEFAULT_MAX_DEPTH = 12
DEFAULT_MAX_PAGES = 3000
# If a capability's freshly discovered URL count falls below this fraction of
# its previous count, treat the run as suspect and skip quarantining orphans
# for that capability rather than mass-deleting good content on a bad crawl.
QUARANTINE_SAFETY_RATIO = 0.5

# Some fetches render a client-side error banner instead of the real page
# (transient rendering/server hiccup) -- crawl4ai still reports these as a
# "successful" fetch, so we have to catch it ourselves and retry.
ERROR_MARKERS = ["An unexpected error occurred."]
MIN_ACCEPTABLE_BODY_LENGTH = 30
CONTENT_RETRY_ATTEMPTS = 3
CONTENT_RETRY_DELAY_SECONDS = 3.0


@dataclass
class PageOutcome:
    url: str
    capability: str
    slug: str
    status: str  # "new" | "updated" | "unchanged"


@dataclass
class RunStats:
    discovered_total: int = 0
    fetch_failed: list[str] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)
    pruned: list[tuple] = field(default_factory=list)
    outcomes: dict = field(default_factory=lambda: {name: [] for name in CAPABILITIES})


def read_existing_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.startswith("content_hash:"):
                return line.strip()
    return None


def is_broken_content(markdown: str) -> bool:
    """Detect a client-side error banner or a suspiciously empty fetch."""
    stripped = markdown.strip()
    if len(stripped) < MIN_ACCEPTABLE_BODY_LENGTH:
        return True
    return any(marker in stripped for marker in ERROR_MARKERS)


def build_deep_crawl_config(max_depth: int, max_pages: int) -> CrawlerRunConfig:
    filter_chain = FilterChain([
        DomainFilter(allowed_domains=[ALLOWED_DOMAIN]),
        URLPatternFilter(patterns=[URL_SCOPE_PATTERN]),
        ContentTypeFilter(allowed_types=["text/html"]),
    ])
    strategy = BFSDeepCrawlStrategy(
        max_depth=max_depth, filter_chain=filter_chain, max_pages=max_pages, include_external=False,
    )
    return CrawlerRunConfig(
        deep_crawl_strategy=strategy,
        css_selector=CONTENT_SELECTOR,
        wait_for=f"css:{CONTENT_SELECTOR}",
        cache_mode=CacheMode.BYPASS,
        stream=True,
        verbose=False,
    )


async def refetch_single_page(crawler: AsyncWebCrawler, url: str) -> str | None:
    """Re-fetch one URL outside the deep crawl (used when the deep crawl's
    copy looked broken). Returns the page's Markdown, or None if every
    attempt still looks broken."""
    single_config = CrawlerRunConfig(
        css_selector=CONTENT_SELECTOR, wait_for=f"css:{CONTENT_SELECTOR}", cache_mode=CacheMode.BYPASS,
    )
    for attempt in range(1, CONTENT_RETRY_ATTEMPTS):
        await asyncio.sleep(CONTENT_RETRY_DELAY_SECONDS * attempt)
        result = await crawler.arun(url=url, config=single_config)
        if result.success and not is_broken_content(result.markdown.raw_markdown):
            return result.markdown.raw_markdown
    return None


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
            if is_broken_content(markdown):
                markdown = await refetch_single_page(crawler, url)
                if markdown is None:
                    # Never overwrite a good existing file with a broken
                    # fetch -- leave it as-is and flag for a manual retry.
                    stats.fetch_failed.append(url)
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


def read_url_from_file(path: Path) -> str | None:
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.startswith("url:"):
                return line.strip().removeprefix("url:").strip().strip('"')
    return None


def is_confirmed_gone(url: str, timeout: float = 10.0) -> bool:
    """True only if the URL itself, fetched directly (no BFS involved),
    confirms it's actually gone (404/410). Any other outcome -- 200, a
    different error, a timeout, a network hiccup on our end -- is NOT treated
    as confirmation, since BFS link-following can miss pages that are still
    live but just unlinked from wherever our crawl reached this run."""
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return False  # any successful response means it's still there
    except urllib.error.HTTPError as exc:
        return exc.code in (404, 410)
    except Exception:  # noqa: BLE001 - network errors on our side aren't proof of anything
        return False


def quarantine_orphans(stats: RunStats) -> dict:
    """Move raw/{capability}/*.md files that this run didn't touch to
    raw/_removed/{capability}/ -- but only after directly confirming the
    URL is actually gone (see is_confirmed_gone). Orphans that turn out to
    still be live, or that we couldn't check, are left in place and reported
    separately so a human can look into the crawl's coverage gap."""
    quarantined: dict[str, list[str]] = {name: [] for name in CAPABILITIES}
    still_alive: dict[str, list[str]] = {name: [] for name in CAPABILITIES}
    skipped_capabilities: list[str] = []

    for capability in CAPABILITIES:
        out_dir = RAW_DIR / capability
        if not out_dir.exists():
            continue

        # Only files untouched by this run's outcomes are orphans.
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
        for slug in sorted(orphans):
            src = out_dir / f"{slug}.md"
            url = read_url_from_file(src)
            if url is None or not is_confirmed_gone(url):
                still_alive[capability].append(slug)
                continue

            dst = removed_dir / f"{slug}.md"
            shutil.move(str(src), str(dst))
            quarantined[capability].append(slug)
            with REMOVED_LOG.open("a", encoding="utf-8") as log:
                log.write(json.dumps({"capability": capability, "slug": slug, "url": url, "removed_at": removed_at}) + "\n")

    return {"quarantined": quarantined, "still_alive": still_alive, "skipped_capabilities": skipped_capabilities}


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

    print("\nPor capability (nuevas / actualizadas / sin cambios):")
    total_in_scope = 0
    for capability, outcomes in stats.outcomes.items():
        new = sum(1 for o in outcomes if o.status == "new")
        updated = sum(1 for o in outcomes if o.status == "updated")
        unchanged = sum(1 for o in outcomes if o.status == "unchanged")
        total_in_scope += len(outcomes)
        print(f"  {capability:12s}: {len(outcomes):4d} total  "
              f"({new} nuevas, {updated} actualizadas, {unchanged} sin cambios)")
    print(f"\nTotal en scope: {total_in_scope}")

    print(f"\nSelf-hosted podadas: {len(stats.pruned)}")

    quarantined = quarantine_result["quarantined"]
    total_quarantined = sum(len(v) for v in quarantined.values())
    print(f"\nEn cuarentena (URL verificada como caída, HTTP 404/410): {total_quarantined}")
    for capability, slugs in quarantined.items():
        if slugs:
            print(f"  {capability}: {len(slugs)}")
            for slug in slugs:
                print(f"    - {slug}")

    still_alive = quarantine_result["still_alive"]
    total_still_alive = sum(len(v) for v in still_alive.values())
    if total_still_alive:
        print(f"\nNo redescubiertas por el BFS pero SIGUEN VIVAS (no se tocaron, revisar cobertura del crawl): {total_still_alive}")
        for capability, slugs in still_alive.items():
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
