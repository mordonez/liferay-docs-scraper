#!/usr/bin/env python3
"""Check whether local docs and the Claude Code skill are ready to use."""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from .filter_urls import CAPABILITIES, resolve_docs_dir


@dataclass
class DoctorResult:
    docs_dir: Path
    official_docs_count: int
    skill_path: Path
    skill_installed: bool
    discovered_total: int | None = None

    @property
    def docs_ready(self) -> bool:
        return self.official_docs_count > 0

    @property
    def ok(self) -> bool:
        return self.docs_ready and self.skill_installed


def count_official_docs(raw_dir: Path) -> int:
    return sum(
        1
        for capability in CAPABILITIES
        for _path in (raw_dir / capability).glob("*.md")
    )


def read_discovered_total(docs_dir: Path) -> int | None:
    summary_path = docs_dir / "reports" / "filtered" / "summary.json"
    if not summary_path.exists():
        return None
    try:
        value = json.loads(summary_path.read_text(encoding="utf-8")).get("discovered_total")
    except (json.JSONDecodeError, OSError):
        return None
    return value if isinstance(value, int) else None


def inspect_installation(docs_dir: Path, project_dir: Path) -> DoctorResult:
    skill_path = project_dir / ".claude" / "skills" / "liferay-expert" / "SKILL.md"
    return DoctorResult(
        docs_dir=docs_dir,
        official_docs_count=count_official_docs(docs_dir / "raw"),
        discovered_total=read_discovered_total(docs_dir),
        skill_path=skill_path,
        skill_installed=skill_path.exists(),
    )


def print_result(result: DoctorResult) -> None:
    docs_status = "OK" if result.docs_ready else "MISSING"
    skill_status = "OK" if result.skill_installed else "MISSING"
    discovered = f", {result.discovered_total} discovered in last report" if result.discovered_total else ""

    print(f"Docs dir: {result.docs_dir}")
    print(f"Official docs: {docs_status} ({result.official_docs_count} markdown files{discovered})")
    print(f"Claude Code skill: {skill_status} ({result.skill_path})")

    if result.ok:
        print("Ready: ask Claude Code a Liferay DXP question in this project.")
        return

    print("\nNext steps:")
    if not result.docs_ready:
        print("  uvx --from crawl4ai crawl4ai-setup")
        print("  uvx liferay-docs-scraper")
    if not result.skill_installed:
        print("  npx skills add mordonez/liferay-docs-scraper --skill liferay-expert -a claude-code")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Project directory where .claude/skills/liferay-expert should exist (default: current directory).",
    )
    args = parser.parse_args()

    result = inspect_installation(resolve_docs_dir(), args.project_dir)
    print_result(result)
    if not result.ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
