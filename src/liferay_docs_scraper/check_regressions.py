#!/usr/bin/env python3
"""Flag suspicious content changes in raw/ after a crawl4ai refresh, using git.

Compares the working tree against a given git ref (default: HEAD, i.e. the
last commit) for every raw/**/*.md file:
  - Shrank a lot (body text, not counting frontmatter): the signature of a
    broken/partial fetch overwriting a good page.
  - Grew a lot: the signature of CONTENT_SELECTOR failing to match and
    crawl4ai falling back to the whole page (breadcrumb/nav/footer chrome
    and all) instead of raising an error.

Operates on filter_urls.resolve_docs_dir() (the same shared docs location
the scraper writes to and the skill reads from), not the current directory.

Usage:
    uvx --from liferay-docs-scraper check-regressions [--ref HEAD] [--shrink-threshold 0.5] [--growth-threshold 3.0]
"""

import argparse
import subprocess

from .filter_urls import resolve_docs_dir

ROOT = resolve_docs_dir()


def body_len(text: str) -> int:
    """Length of the file excluding the YAML frontmatter block."""
    parts = text.split("---\n", 2)
    body = parts[2] if len(parts) == 3 else text
    return len(body)


def is_git_repo() -> bool:
    """True only if ROOT is inside a git work tree AND has at least one
    commit -- a freshly `git init`-ed dir with no commits yet has no HEAD
    to diff against either."""
    inside_work_tree = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if inside_work_tree.returncode != 0:
        return False
    has_head = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=ROOT, capture_output=True, text=True,
    )
    return has_head.returncode == 0


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


def run_check(ref: str = "HEAD", shrink_threshold: float = 0.5, growth_threshold: float = 3.0) -> bool:
    """Print the regression report; return True iff something looked suspicious.

    No-ops (returns False) if resolve_docs_dir() isn't a git repo yet -- there's
    nothing to diff against on a first-ever run. `git init` it once to start
    getting this check on subsequent runs."""
    if not is_git_repo():
        print(f"{ROOT} no es un repo git todavía -- nada que comparar, se omite "
              "la verificación de regresiones. `git init` ahí una vez para "
              "activarla en corridas futuras.")
        return False

    changed = changed_raw_files(ref)
    print(f"Archivos .md cambiados en raw/ vs {ref}: {len(changed)}")

    shrunk, grew = [], []
    for rel_path in changed:
        full_path = ROOT / rel_path
        old_text = git_show(ref, rel_path)
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
        if ratio < shrink_threshold:
            shrunk.append((rel_path, old_len, new_len, ratio))
        elif ratio > growth_threshold:
            grew.append((rel_path, old_len, new_len, ratio))

    if shrunk:
        print(f"\nSOSPECHOSOS ({len(shrunk)}) -- perdieron más del "
              f"{(1 - shrink_threshold) * 100:.0f}% del contenido:")
        for rel_path, old_len, new_len, ratio in sorted(shrunk, key=lambda x: x[3]):
            print(f"  {rel_path}: {old_len} -> {new_len} chars ({ratio:.0%})")
    else:
        print("\nNinguno por debajo del umbral de encogimiento -- sin señales de pérdida de contenido.")

    if grew:
        print(f"\nSOSPECHOSOS ({len(grew)}) -- crecieron más de {growth_threshold:.0f}x "
              f"(posible fallback a la página completa sin selector):")
        for rel_path, old_len, new_len, ratio in sorted(grew, key=lambda x: -x[3]):
            print(f"  {rel_path}: {old_len} -> {new_len} chars ({ratio:.1f}x)")

    return bool(shrunk or grew)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--shrink-threshold", type=float, default=0.5,
                         help="Flag files whose body shrank below this fraction of the original.")
    parser.add_argument("--growth-threshold", type=float, default=3.0,
                         help="Flag files whose body grew beyond this multiple of the original.")
    args = parser.parse_args()
    run_check(args.ref, args.shrink_threshold, args.growth_threshold)


if __name__ == "__main__":
    main()
