#!/usr/bin/env python3
"""Extract clean Markdown for each capability's URL list via the Firecrawl CLI.

Reads reports/filtered/{capability}_urls.txt and writes one Markdown file per
URL to raw/{capability}/{slug}.md, with YAML frontmatter (url, capability,
fetched_at, content_hash). Shells out to the already-authenticated `firecrawl`
CLI (`firecrawl scrape -f markdown --only-main-content --json <url>`) instead
of managing an API key directly.

Each scraped page also gets its repeated site chrome (maintenance banner,
breadcrumbs, sidebar TOC, global footer) stripped inline via
clean_boilerplate.clean_body, so raw/ already holds clean Markdown -- no
separate cleanup pass needed for newly extracted capabilities.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from clean_boilerplate import NotCleanable, clean_body
from filter_urls import CAPABILITIES as CAPABILITY_PREFIXES

ROOT = Path(__file__).resolve().parent.parent
FILTERED_DIR = ROOT / "reports" / "filtered"
RAW_DIR = ROOT / "raw"

# Firecrawl account concurrency limit observed via `firecrawl --status`
# (2 parallel scrape jobs) -- going higher just queues on the API side.
DEFAULT_CONCURRENCY = 2
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_DELAY = 3.0
SCRAPE_TIMEOUT_SECONDS = 90


@dataclass
class ScrapeResult:
    url: str
    ok: bool
    path: Path | None = None
    error: str | None = None
    attempts: int = 0
    cleaned: bool = False
    clean_skip_reason: str | None = None


def slugify(url: str, prefix: str) -> str:
    path = urlparse(url).path
    remainder = path[len(prefix):].strip("/")
    if not remainder:
        return "index"
    return remainder.replace("/", "-")


def run_scrape_cli(url: str) -> dict:
    proc = subprocess.run(
        [
            "firecrawl", "scrape",
            "-f", "markdown",
            "--only-main-content",
            "--json",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=SCRAPE_TIMEOUT_SECONDS,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"CLI exit {proc.returncode}: {proc.stderr.strip()[:300]}")

    stdout = proc.stdout.strip()
    brace_idx = stdout.find("{")
    if brace_idx == -1:
        raise RuntimeError(f"no JSON in CLI output: {stdout[:200]}")

    data = json.loads(stdout[brace_idx:])
    markdown = data.get("markdown")
    if not markdown or not markdown.strip():
        status = data.get("metadata", {}).get("statusCode")
        raise RuntimeError(f"empty markdown (statusCode={status})")
    return data


def scrape_with_retries(url: str, max_retries: int, retry_delay: float) -> tuple[dict | None, str | None, int]:
    last_error = None
    for attempt in range(1, max_retries + 2):  # first try + retries
        try:
            data = run_scrape_cli(url)
            return data, None, attempt
        except subprocess.TimeoutExpired:
            last_error = f"timeout after {SCRAPE_TIMEOUT_SECONDS}s"
        except Exception as exc:  # noqa: BLE001 - want to capture and retry any failure
            last_error = str(exc)
        if attempt <= max_retries:
            time.sleep(retry_delay * attempt)
    return None, last_error, max_retries + 1


def build_frontmatter(url: str, capability: str, markdown: str) -> str:
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    lines = [
        "---",
        f'url: "{url}"',
        f"capability: {capability}",
        f"fetched_at: \"{fetched_at}\"",
        f"content_hash: \"sha256:{content_hash}\"",
        "---",
        "",
    ]
    return "\n".join(lines)


def process_url(url: str, capability: str, prefix: str, out_dir: Path,
                 max_retries: int, retry_delay: float, force: bool) -> ScrapeResult:
    slug = slugify(url, prefix)
    out_path = out_dir / f"{slug}.md"

    if out_path.exists() and not force:
        return ScrapeResult(url=url, ok=True, path=out_path, attempts=0)

    data, error, attempts = scrape_with_retries(url, max_retries, retry_delay)
    if error is not None:
        return ScrapeResult(url=url, ok=False, error=error, attempts=attempts)

    markdown = data["markdown"]
    cleaned = False
    clean_skip_reason = None
    try:
        markdown = clean_body(markdown)
        cleaned = True
    except NotCleanable as exc:
        clean_skip_reason = exc.reason

    content = build_frontmatter(url, capability, markdown) + markdown
    out_path.write_text(content, encoding="utf-8")
    return ScrapeResult(
        url=url, ok=True, path=out_path, attempts=attempts,
        cleaned=cleaned, clean_skip_reason=clean_skip_reason,
    )


def extract_capability(capability: str, concurrency: int, max_retries: int,
                        retry_delay: float, force: bool, limit: int | None) -> list[ScrapeResult]:
    prefix = CAPABILITY_PREFIXES[capability]
    urls_file = FILTERED_DIR / f"{capability}_urls.txt"
    urls = [u.strip() for u in urls_file.read_text(encoding="utf-8").splitlines() if u.strip()]
    if limit is not None:
        urls = urls[:limit]

    out_dir = RAW_DIR / capability
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[ScrapeResult] = []
    print(f"[{capability}] {len(urls)} URLs, concurrency={concurrency}, max_retries={max_retries}")

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {
            pool.submit(process_url, url, capability, prefix, out_dir, max_retries, retry_delay, force): url
            for url in urls
        }
        done = 0
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            done += 1
            status = "ok" if result.ok else f"FAIL ({result.error})"
            print(f"  [{done}/{len(urls)}] {result.url} -> {status}")

    return results


def print_summary(capability: str, results: list[ScrapeResult]) -> None:
    ok = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]
    not_cleaned = [r for r in ok if r.attempts > 0 and not r.cleaned]
    print(f"\n=== {capability}: {len(ok)} ok / {len(failed)} failed (of {len(results)}) ===")
    print(f"    limpieza automática: {sum(1 for r in ok if r.attempts > 0 and r.cleaned)} ok / {len(not_cleaned)} sin limpiar")
    if failed:
        print("Fallos:")
        for r in failed:
            print(f"  - {r.url}: {r.error}")
    if not_cleaned:
        print("No limpiados automáticamente (plantilla inesperada, revisar a mano):")
        for r in not_cleaned:
            print(f"  - {r.url}: {r.clean_skip_reason}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--capability", action="append", choices=list(CAPABILITY_PREFIXES),
        help="Capability to process (repeatable). Default: all.",
    )
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--retry-delay", type=float, default=DEFAULT_RETRY_DELAY)
    parser.add_argument("--force", action="store_true", help="Re-scrape URLs even if output file already exists.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N URLs (for piloting).")
    args = parser.parse_args()

    capabilities = args.capability or list(CAPABILITY_PREFIXES)

    all_results: dict[str, list[ScrapeResult]] = {}
    for capability in capabilities:
        results = extract_capability(
            capability, args.concurrency, args.max_retries, args.retry_delay, args.force, args.limit,
        )
        all_results[capability] = results
        print_summary(capability, results)

    total_ok = sum(1 for rs in all_results.values() for r in rs if r.ok)
    total_failed = sum(1 for rs in all_results.values() for r in rs if not r.ok)
    print(f"\nTOTAL: {total_ok} ok / {total_failed} failed")

    if total_failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
