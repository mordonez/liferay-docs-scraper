# liferay-docs-scraper

Scrape `learn.liferay.com/w/dxp/*` into local Markdown and install a
`liferay-expert` Claude Code skill that answers Liferay DXP questions from
those files.

The goal is simple: when you ask Claude Code about Liferay DXP, it should read
the current docs you fetched locally, cite the source URL, and avoid guessing
from model memory. No bundled Liferay content, no embeddings, no vector DB.

![Demo of liferay-docs-scraper in Codex](docs/assets/liferay-doc-demo.gif)

[Download the MP4 demo](docs/assets/liferay-doc-demo.mp4)

[Project page](https://mordonez.github.io/liferay-docs-scraper/) ·
[PyPI package](https://pypi.org/project/liferay-docs-scraper/) · Python
3.10-3.13 · [MIT license](LICENSE)

## Quickstart

From zero to asking Liferay questions in Claude Code:

```bash
# 1. One-time browser setup for crawl4ai/Playwright
uvx --from crawl4ai crawl4ai-setup

# 2. Scrape the official Liferay DXP docs into ~/.liferay-docs
uvx liferay-docs-scraper

# 3. Install the Claude Code skill in your current project
npx skills add mordonez/liferay-docs-scraper --skill liferay-expert -a claude-code

# 4. Verify docs freshness, reports, and skill installation
uvx --from liferay-docs-scraper liferay-docs-scraper-doctor
```

Then ask Claude Code something like:

> How do I configure synonym sets in Liferay Search?

The skill searches your local Markdown, reads the best matching pages, and
cites the original `learn.liferay.com` URL from each file's frontmatter.

Keep `-a claude-code` in the install command. It avoids interactive installer
edge cases where the skill can appear installed but not land in
`.claude/skills/`.

## Requirements

- Python 3.10-3.13
- [`uv`](https://docs.astral.sh/uv/)
- Node/npm for `npx skills add`

`crawl4ai` uses Playwright. Run the browser setup once per machine before the
first scrape:

```bash
uvx --from crawl4ai crawl4ai-setup
```

## How It Works

```mermaid
flowchart LR
  A[learn.liferay.com] --> B[crawl4ai BFS crawl]
  B --> C[local Markdown in ~/.liferay-docs]
  C --> D[search_index.jsonl and anomalies.jsonl]
  C --> E[liferay-expert Claude Code skill]
  D --> E
  E --> F[cited Liferay answers]
```

The official scraper starts at
`https://learn.liferay.com/w/dxp/index` and uses crawl4ai's BFS deep crawler to
follow internal `/w/dxp/*` links. For each page, it extracts the article body,
classifies the URL into a Liferay capability, and writes Markdown locally.

The scraper is intentionally boring:

- It fetches from the live Liferay docs when you run it; this package does not
  redistribute Liferay documentation text.
- It writes to one shared docs directory, so every project can use the same
  corpus.
- It retries through crawl4ai, writes files atomically, and exits non-zero when
  the crawl or page fetches fail.
- It never starts a long scrape from inside the skill. If docs are missing, the
  skill tells you which command to run.

## Where Files Go

By default, everything is written under:

```text
~/.liferay-docs
```

Use `LIFERAY_DOCS_DIR` when you want a repo-local or custom corpus:

```bash
export LIFERAY_DOCS_DIR="$PWD/.liferay-docs"
uvx liferay-docs-scraper
uvx --from liferay-docs-scraper liferay-docs-scraper-doctor
```

Layout:

```text
~/.liferay-docs/
  raw/{capability}/*.md
  raw/_navigation/{capability}/*.md
  raw/_removed/{capability}/*.md
  raw/community-howto/{capability}/*.md
  raw/community-troubleshooting/{capability}/*.md
  reports/filtered/
    search_index.jsonl
    anomalies.jsonl
    summary.json
    *_urls.txt
```

`raw/{capability}/*.md` is the main official-docs corpus the skill reads first.
`raw/_navigation/` keeps table-of-contents/navigation pages out of normal
answers while preserving them. `raw/_removed/` holds pages only after the
scraper directly confirms their original URL is gone.

## Refreshing Official Docs

Run the scraper again whenever you want fresh docs:

```bash
uvx liferay-docs-scraper
```

A normal full run usually takes tens of minutes. For a smoke test:

```bash
uvx liferay-docs-scraper --max-pages 200
```

Useful options:

```bash
uvx liferay-docs-scraper --max-depth 12
uvx liferay-docs-scraper --max-pages 3000
```

Each full run starts from the current site state. If a previously known page is
not rediscovered by BFS, the scraper checks that page directly before moving it
to `raw/_removed/`. If the page is still alive, it refreshes it directly and
records the BFS coverage gap in the reports.

## Community Articles

Community articles are optional, larger, and lower-authority than the official
DXP docs:

```bash
uvx --from liferay-docs-scraper liferay-docs-scraper-community
```

This fetches Liferay community How-To and Troubleshooting articles from
`learn.liferay.com/kb-article/*`. They are stored separately:

```text
raw/community-howto/{capability}/*.md
raw/community-troubleshooting/{capability}/*.md
```

Many community articles have no usable capability tag, so they go to
`_uncategorized/`. The skill treats community content as secondary evidence and
says so when citing it.

Useful commands:

```bash
# Only How-To articles
uvx --from liferay-docs-scraper liferay-docs-scraper-community --resource-type howto

# Smaller test run per resource type
uvx --from liferay-docs-scraper liferay-docs-scraper-community --limit 100
```

Community scraping can take much longer than the official-docs scrape because
it fetches thousands of additional articles.

## Installing The Skill

Install `liferay-expert` into each Claude Code project where you want Liferay
help:

```bash
npx skills add mordonez/liferay-docs-scraper --skill liferay-expert -a claude-code
```

Manual install also works: place the skill file at:

```text
.claude/skills/liferay-expert/SKILL.md
```

The skill resolves docs the same way the scraper does:

1. `$LIFERAY_DOCS_DIR`, if set.
2. `~/.liferay-docs`, otherwise.

When answering, it searches `reports/filtered/search_index.jsonl` when present,
falls back to normal file search under `raw/`, reads Markdown files directly,
and cites the `url:` frontmatter. Official docs are preferred over community
articles when both cover the same topic.

## Doctor

Use the doctor when something feels off:

```bash
uvx --from liferay-docs-scraper liferay-docs-scraper-doctor
```

It checks:

- Which docs directory is active.
- Whether official Markdown exists.
- How many community Markdown files exist.
- The official-docs freshness window.
- Search index and anomaly report entry counts.
- Whether `.claude/skills/liferay-expert/SKILL.md` exists in the current
  project.

To inspect a different project directory:

```bash
uvx --from liferay-docs-scraper liferay-docs-scraper-doctor --project-dir /path/to/project
```

The doctor does not scrape docs and does not install the skill. It only reports
status and prints the next command to run.

## Reports

The scraper writes agent-facing reports under `reports/filtered/`.

`search_index.jsonl` is a local retrieval index. Each JSON line includes title,
source URL, source type, capability, file path, headings, and `fetched_at`. The
skill uses it first because it is faster and cleaner than searching every
Markdown file.

`anomalies.jsonl` is an informational scrape-quality report. It flags signals
like very short bodies, missing titles, known error markers, unusually large
pages, and large body-size swings versus the previous local copy. It does not
mean a page is unusable; it means the page may deserve a quick check before you
trust or cite it heavily.

`summary.json` records the latest run counts, crawl failures, direct refreshes,
coverage gaps, and search index size.

## Troubleshooting

**`crawl4ai` or browser errors on the first run**

Run the Playwright setup again:

```bash
uvx --from crawl4ai crawl4ai-setup
```

**Claude Code says the skill is missing**

Run the install command from the project where you are using Claude Code:

```bash
npx skills add mordonez/liferay-docs-scraper --skill liferay-expert -a claude-code
```

Then verify:

```bash
uvx --from liferay-docs-scraper liferay-docs-scraper-doctor
```

**Claude Code says docs are missing**

Check whether you are using a custom docs directory:

```bash
echo "$LIFERAY_DOCS_DIR"
```

If it is empty, the skill expects `~/.liferay-docs`. If it points somewhere
else, run the scraper with that same environment variable.

**Docs are stale**

Refresh official docs:

```bash
uvx liferay-docs-scraper
```

The doctor warns when official docs are older than about seven days.

**A scrape stops partway through**

Rerun the same command. Already written Markdown remains usable, but a failed
run exits non-zero and avoids treating untouched pages as removed.

**Community answers feel weaker than official docs**

That is expected. Community How-To and Troubleshooting articles are useful for
practical cases and errors, but the skill should label them as community
content and prefer official docs when official docs answer the question.

## Development

```bash
uv sync --group dev
uv run ruff check .
uv run --with pytest python -m pytest
uv build
```

Run `uv sync --group dev` once before local development so the project and dev
tools are installed into uv's project environment. The pytest command uses
`python -m pytest` with `--with pytest` because older or unsynced uv
environments can fail to find the `pytest` console script even when Python can
run the module.

CI runs lint, tests, and package build on Python 3.10, 3.11, 3.12, and 3.13.
It does not run a real scrape. Release publishing is documented in
[`docs/release.md`](docs/release.md).

## License

[MIT](LICENSE) applies to this tool and skill only. Liferay documentation
content remains Liferay's content and is fetched locally by each user.
