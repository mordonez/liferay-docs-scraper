#!/usr/bin/env python3
"""Save a manually-distilled page to distilled/{capability}/{slug}.md.

This project distills raw/{capability}/*.md pages under Claude Code /
subscription usage, NOT the paid Claude API -- there is no Batch API call
here. The actual distillation (applying the system prompt in
docs/distill_system_prompt.txt) is done by the coding agent itself, one
page at a time, reading raw/{capability}/{slug}.md and writing the
distilled Markdown body. This script only handles the mechanical part:
copying the original frontmatter, adding `distilled_at`, and appending the
"## Fuente" section with the source URL.

Usage:
    python scripts/save_distilled.py raw/search/foo.md --body-file /tmp/foo-distilled.md
    cat /tmp/foo-distilled.md | python scripts/save_distilled.py raw/search/foo.md
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DISTILLED_DIR = ROOT / "distilled"


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


def save(raw_path: Path, distilled_body: str) -> Path:
    original = raw_path.read_text(encoding="utf-8")
    fm, _body = split_frontmatter(original)
    capability = fm.get("capability", raw_path.parent.name)
    url = fm.get("url", "")

    distilled_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    frontmatter = "\n".join(
        [
            "---",
            f'url: "{url}"',
            f"capability: {capability}",
            f'fetched_at: "{fm.get("fetched_at", "")}"',
            f'content_hash: "{fm.get("content_hash", "")}"',
            f'distilled_at: "{distilled_at}"',
            "---",
            "",
        ]
    )

    body = distilled_body.rstrip() + "\n"
    if "## Fuente" not in body:
        body += f"\n## Fuente\n\n{url}\n"

    out_dir = DISTILLED_DIR / capability
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{raw_path.stem}.md"
    out_path.write_text(frontmatter + body, encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("raw_path", help="Path to the raw/{capability}/{slug}.md source file.")
    parser.add_argument(
        "--body-file", help="Path to a file with the distilled Markdown body. If omitted, reads from stdin.",
    )
    args = parser.parse_args()

    raw_path = Path(args.raw_path)
    if not raw_path.is_absolute():
        raw_path = ROOT / raw_path
    if not raw_path.exists():
        print(f"No existe: {raw_path}", file=sys.stderr)
        sys.exit(1)

    if args.body_file:
        distilled_body = Path(args.body_file).read_text(encoding="utf-8")
    else:
        distilled_body = sys.stdin.read()

    out_path = save(raw_path, distilled_body)
    print(f"Guardado: {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
