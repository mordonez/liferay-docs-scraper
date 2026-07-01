#!/usr/bin/env python3
"""Classify raw/{capability}/*.md pages as "index" or "content".

An "index" page is one whose body (frontmatter stripped) is short and
consists mostly of links to subpages -- a navigation/TOC page with no
substantial technical content of its own. Everything else is "content".

Heuristic (no API calls, pure text analysis):
  - Strip Markdown link syntax down to visible text (`[text](url)` -> `text`)
    and strip heading/emphasis markup (`#`, `*`, `_`, backticks).
  - total_words: word count of that visible text.
  - link_ratio: fraction of those words that come from inside a Markdown
    link's link-text span.
  - "index" iff total_words < INDEX_MAX_WORDS and link_ratio >= INDEX_MIN_LINK_RATIO.

Writes reports/page_classification.json:
  {"index": [...], "content": [...]}
each entry: {"path": "raw/search/index.md", "capability": "search", "url": "...",
             "total_words": N, "link_ratio": 0.xx}

Prints a per-capability index vs content count summary.
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
REPORT_PATH = ROOT / "reports" / "page_classification.json"

INDEX_MAX_WORDS = 150
INDEX_MIN_LINK_RATIO = 0.5

LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
MARKUP_RE = re.compile(r"[#*_`\\]")


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


def analyze_body(body: str) -> tuple[int, float]:
    links = LINK_RE.findall(body)
    link_word_count = sum(len(text.split()) for text, _url in links)

    visible = LINK_RE.sub(lambda m: m.group(1), body)
    visible = MARKUP_RE.sub("", visible)
    total_words = len(visible.split())

    link_ratio = (link_word_count / total_words) if total_words else 0.0
    return total_words, link_ratio


def classify(total_words: int, link_ratio: float) -> str:
    if total_words < INDEX_MAX_WORDS and link_ratio >= INDEX_MIN_LINK_RATIO:
        return "index"
    return "content"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir", default=str(RAW_DIR), help="Root directory of raw/{capability}/*.md files."
    )
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    files = sorted(raw_dir.glob("*/*.md"))

    results = {"index": [], "content": []}
    per_capability = defaultdict(lambda: {"index": 0, "content": 0})

    for path in files:
        capability = path.parent.name
        text = path.read_text(encoding="utf-8")
        fm, body = split_frontmatter(text)
        total_words, link_ratio = analyze_body(body)
        label = classify(total_words, link_ratio)

        entry = {
            "path": str(path.relative_to(ROOT)),
            "capability": capability,
            "url": fm.get("url", ""),
            "total_words": total_words,
            "link_ratio": round(link_ratio, 3),
        }
        results[label].append(entry)
        per_capability[capability][label] += 1

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    total_index = len(results["index"])
    total_content = len(results["content"])
    print(f"Total archivos: {len(files)}")
    print(f"  index:   {total_index}")
    print(f"  content: {total_content}")
    print()
    print(f"{'capability':<15} {'index':>7} {'content':>9} {'total':>7}")
    for capability in sorted(per_capability):
        counts = per_capability[capability]
        total = counts["index"] + counts["content"]
        print(f"{capability:<15} {counts['index']:>7} {counts['content']:>9} {total:>7}")
    print()
    print(f"Guardado en {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
