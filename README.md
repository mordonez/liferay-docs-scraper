# liferay-docs-scraper

Scrape `learn.liferay.com/w/dxp/*` into local Markdown, then let Claude Code
answer Liferay DXP questions by searching those files. No bundled Liferay
content, no embeddings, no vector DB.

[![PyPI](https://img.shields.io/pypi/v/liferay-docs-scraper.svg)](https://pypi.org/project/liferay-docs-scraper/)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://pypi.org/project/liferay-docs-scraper/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Quickstart

From zero to asking Liferay questions in Claude Code:

```bash
# 1. One-time browser setup for crawl4ai/Playwright
uvx --from crawl4ai crawl4ai-setup

# 2. Scrape the official Liferay DXP docs (~30-40 min)
uvx liferay-docs-scraper

# 3. Install the Claude Code skill in your project
npx skills add mordonez/liferay-docs-scraper --skill liferay-expert -a claude-code

# 4. Check that docs and skill are ready
uvx --from liferay-docs-scraper liferay-docs-scraper-doctor
```

Then ask Claude Code something like:

> How do I configure synonym sets in Liferay Search?

The skill searches the local Markdown, reads the matching page, and cites the
source URL from that file's frontmatter.

Keep `-a claude-code` in the install command. It avoids interactive installer
edge cases where the skill can appear installed but not land in
`.claude/skills/`.

## What this repo does not do

- It does not ship Liferay documentation text. The package contains the scraper
  and skill only; each user fetches their own local copy from
  `learn.liferay.com`.
- It does not use embeddings, RAG infrastructure, or a vector database. The
  skill uses normal file search and reads Markdown directly.
- It does not scrape automatically from the skill. If docs are missing, the
  skill tells you what command to run instead of starting a long crawl in the
  middle of a conversation.

## Requirements

- Python 3.10-3.13
- [`uv`](https://docs.astral.sh/uv/)
- Node/npm for `npx skills add`

`crawl4ai` drives Playwright, so run this once before the first scrape:

```bash
uvx --from crawl4ai crawl4ai-setup
```

## Scraper Reference

Run the official-docs scraper:

```bash
uvx liferay-docs-scraper
```

It crawls `https://learn.liferay.com/w/dxp/index` with crawl4ai's BFS crawler,
keeps URLs under `/w/dxp/*`, extracts `.learn-article-content`, classifies each
page into one of 14 Liferay capabilities, and writes Markdown to one shared
docs directory.

Default docs directory:

```text
~/.liferay-docs
```

Override it when needed:

```bash
export LIFERAY_DOCS_DIR="$PWD/.liferay-docs"
uvx liferay-docs-scraper
```

Directory layout:

```text
~/.liferay-docs/
  raw/{capability}/*.md
  raw/_navigation/{capability}/*.md
  raw/_removed/{capability}/*.md
  reports/filtered/
```

Useful commands:

```bash
# Smaller smoke run
uvx liferay-docs-scraper --max-pages 200

# Check local docs and current-project skill installation
uvx --from liferay-docs-scraper liferay-docs-scraper-doctor
```

The scraper writes files atomically, retries page fetches through crawl4ai,
uses bounded concurrency, and exits non-zero if page fetches or the crawl stream
fail. If the crawl is interrupted, already written pages remain usable, but the
run is marked failed and orphan quarantine is skipped so a partial crawl cannot
move good pages to `raw/_removed/`.

## Community Articles

Optional, larger, and lower-authority:

```bash
uvx --from liferay-docs-scraper liferay-docs-scraper-community
```

This fetches Liferay community How-To and Troubleshooting articles from
`learn.liferay.com/kb-article/*`. It writes them separately:

```text
raw/community-howto/{capability}/*.md
raw/community-troubleshooting/{capability}/*.md
```

Many community articles are not tagged with a capability by the site; those go
to `_uncategorized/`. The `liferay-expert` skill treats community content as a
secondary source and says so in answers.

Useful options:

```bash
uvx --from liferay-docs-scraper liferay-docs-scraper-community --resource-type howto
uvx --from liferay-docs-scraper liferay-docs-scraper-community --limit 100
```

## Skill Reference

Install into the current project:

```bash
npx skills add mordonez/liferay-docs-scraper --skill liferay-expert -a claude-code
```

Manual install also works: copy `skills/liferay-expert/SKILL.md` to:

```text
.claude/skills/liferay-expert/SKILL.md
```

The skill resolves docs exactly like the scraper:

1. `$LIFERAY_DOCS_DIR`, if set.
2. `~/.liferay-docs`, otherwise.

When answering, it searches `raw/{capability}/*.md`, reads the best matching
files, and cites their `url:` frontmatter. It skips `raw/_navigation/` unless
there is no better source.

## Development

```bash
uv sync --group dev
uv run ruff check .
uv run pytest
uv build
```

CI runs lint, tests, and package build on Python 3.10, 3.11, 3.12, and 3.13.
It does not run a real scrape. Release publishing is documented in
[`docs/release.md`](docs/release.md).

## License

[MIT](LICENSE) applies to this tool and skill only. Liferay documentation
content remains Liferay's content and is fetched locally by each user.
