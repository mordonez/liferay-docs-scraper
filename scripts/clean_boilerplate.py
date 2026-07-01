#!/usr/bin/env python3
"""Strip repeated site chrome from already-extracted learn.liferay.com Markdown.

Every page scraped by scripts/extract_content.py carries the same template
noise: a maintenance banner, breadcrumbs, and a sidebar/TOC block before the
real content, plus a global site footer (nav, social links, cookie banner)
after it. This is purely structural, deterministic cleanup -- no rewriting or
summarizing of the actual page content.

Detected anchors (validated against all 105 raw/search/*.md files):
  - Header: the first Markdown H1 heading of the form "# [Title](url)" marks
    where real content starts. Everything before it (within the body, after
    frontmatter) is chrome.
  - Footer: the line "[Liferay.com](https://www.liferay.com/)" marks the
    start of the global site footer. It and everything after it (through EOF)
    is chrome.

Firecrawl's HTML->Markdown conversion sometimes appends a trailing "\\" to
lines in files that contain certain nested lists/code blocks; anchors are
matched with an optional trailing backslash to account for that.

If either anchor is missing from a file, the file is left untouched and
reported separately -- no partial/best-effort cutting.
"""

import argparse
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HEADER_H1_RE = re.compile(r"^# \[.*\]\([^)]*\)\s*\\?\s*$")
FOOTER_RE = re.compile(r"^\[Liferay\.com\]\(https://www\.liferay\.com/\)\s*\\?\s*$")


class NotCleanable(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def split_frontmatter(text: str) -> tuple[list[str], list[str]]:
    lines = text.split("\n")
    if not lines or lines[0] != "---":
        raise NotCleanable("no opening '---' frontmatter delimiter")
    try:
        closing_offset = lines[1:].index("---")
    except ValueError:
        raise NotCleanable("no closing '---' frontmatter delimiter")
    closing_idx = closing_offset + 1
    frontmatter = lines[: closing_idx + 1]
    body = lines[closing_idx + 1 :]
    return frontmatter, body


def find_header_cut(body: list[str]) -> int:
    for i, line in enumerate(body):
        if HEADER_H1_RE.match(line):
            return i
    raise NotCleanable("no H1 heading anchor found (unexpected page template)")


def find_footer_cut(body: list[str], after: int) -> int:
    for i in range(after, len(body)):
        if FOOTER_RE.match(body[i].strip()):
            return i
    raise NotCleanable("no site-footer anchor found (unexpected page template)")


def clean_body(markdown: str) -> str:
    """Strip the header/footer site chrome from a raw scraped Markdown body
    (no frontmatter). Shared by clean_boilerplate.py (post-hoc cleanup) and
    extract_content.py (cleaning inline right after scraping).

    Raises NotCleanable if the expected header/footer anchors aren't found --
    callers should keep the original text untouched in that case.
    """
    body = markdown.split("\n")
    header_cut = find_header_cut(body)
    footer_cut = find_footer_cut(body, after=header_cut)

    cleaned_body_lines = body[header_cut:footer_cut]
    # drop trailing blank lines left right before the footer anchor
    while cleaned_body_lines and cleaned_body_lines[-1].strip() == "":
        cleaned_body_lines.pop()

    return "\n".join(cleaned_body_lines) + "\n"


def rebuild_frontmatter(frontmatter: list[str], new_hash: str) -> list[str]:
    rebuilt = []
    for line in frontmatter:
        if line.startswith("content_hash:"):
            rebuilt.append(f'content_hash: "sha256:{new_hash}"')
        else:
            rebuilt.append(line)
    return rebuilt


def clean_text(text: str) -> str:
    """Return the cleaned file text, or raise NotCleanable if unsafe to touch."""
    frontmatter, body = split_frontmatter(text)
    cleaned_body = clean_body("\n".join(body))
    new_hash = hashlib.sha256(cleaned_body.encode("utf-8")).hexdigest()
    new_frontmatter = rebuild_frontmatter(frontmatter, new_hash)

    return "\n".join(new_frontmatter) + "\n" + cleaned_body


def clean_file(path: Path, dry_run: bool) -> tuple[str, str | None]:
    """Return (status, reason). status is 'cleaned', 'skipped', or 'unchanged'."""
    original = path.read_text(encoding="utf-8")
    try:
        cleaned = clean_text(original)
    except NotCleanable as exc:
        return "skipped", exc.reason

    if cleaned == original:
        return "unchanged", None

    if not dry_run:
        path.write_text(cleaned, encoding="utf-8")
    return "cleaned", None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target", nargs="?", default="raw",
        help="File or directory to clean (recursively, for directories). Default: raw/",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing files.")
    args = parser.parse_args()

    target_path = (ROOT / args.target) if not Path(args.target).is_absolute() else Path(args.target)
    if target_path.is_file():
        files = [target_path]
    else:
        files = sorted(target_path.rglob("*.md"))

    cleaned, unchanged, skipped = [], [], []
    for f in files:
        status, reason = clean_file(f, dry_run=args.dry_run)
        if status == "cleaned":
            cleaned.append(f)
        elif status == "unchanged":
            unchanged.append(f)
        else:
            skipped.append((f, reason))

    print(f"Total archivos: {len(files)}")
    print(f"Limpiados: {len(cleaned)}")
    print(f"Sin cambios (ya limpios o vacíos): {len(unchanged)}")
    print(f"No limpiados automáticamente (revisar a mano): {len(skipped)}")
    if skipped:
        for f, reason in skipped:
            print(f"  - {f.relative_to(ROOT)}: {reason}")


if __name__ == "__main__":
    main()
