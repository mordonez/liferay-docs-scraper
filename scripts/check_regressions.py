#!/usr/bin/env python3
"""Flag suspicious content loss in raw/ after a crawl4ai refresh, using git.

Compares the working tree against a given git ref (default: HEAD, i.e. the
last commit) for every raw/**/*.md file: files that shrank a lot (body text,
not counting frontmatter) are flagged for manual review, since that's the
signature of a broken/partial extraction overwriting a good one -- as
opposed to the expected cosmetic size drift between Firecrawl's and
crawl4ai's Markdown conversion (a few percent either way).

Usage:
    python3 scripts/check_regressions.py [--ref HEAD] [--shrink-threshold 0.5]
"""

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def body_len(text: str) -> int:
    """Length of the file excluding the YAML frontmatter block."""
    parts = text.split("---\n", 2)
    body = parts[2] if len(parts) == 3 else text
    return len(body)


def git_show(ref: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def changed_raw_files(ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", ref, "--", "raw/"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return [line for line in result.stdout.splitlines() if line.endswith(".md")]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--shrink-threshold", type=float, default=0.5,
                         help="Flag files whose body shrank below this fraction of the original.")
    args = parser.parse_args()

    changed = changed_raw_files(args.ref)
    print(f"Archivos .md cambiados en raw/ vs {args.ref}: {len(changed)}")

    suspicious = []
    for rel_path in changed:
        full_path = ROOT / rel_path
        old_text = git_show(args.ref, rel_path)
        if old_text is None:
            continue  # new file, nothing to compare
        if not full_path.exists():
            continue  # deleted/moved (e.g. quarantined), handled separately

        new_text = full_path.read_text(encoding="utf-8")
        old_len = body_len(old_text)
        new_len = body_len(new_text)
        if old_len == 0:
            continue
        ratio = new_len / old_len
        if ratio < args.shrink_threshold:
            suspicious.append((rel_path, old_len, new_len, ratio))

    if suspicious:
        print(f"\nSOSPECHOSOS ({len(suspicious)}) -- perdieron más del "
              f"{(1 - args.shrink_threshold) * 100:.0f}% del contenido:")
        for rel_path, old_len, new_len, ratio in sorted(suspicious, key=lambda x: x[3]):
            print(f"  {rel_path}: {old_len} -> {new_len} chars ({ratio:.0%})")
    else:
        print("\nNinguno por debajo del umbral de encogimiento -- sin señales de pérdida de contenido.")


if __name__ == "__main__":
    main()
