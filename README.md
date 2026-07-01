# liferay-docs-scraper

Scrape `learn.liferay.com/w/dxp/*` into a local Markdown copy of the docs, then answer
Liferay DXP questions in Claude Code by grepping and citing it — no
bundled docs, no embeddings, no vector DB.

[![PyPI](https://img.shields.io/pypi/v/liferay-docs-scraper.svg)](https://pypi.org/project/liferay-docs-scraper/)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://pypi.org/project/liferay-docs-scraper/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## What makes this different

- **No bundled copyrighted content.** This repo and the PyPI package ship
  only the scraping tool, never Liferay's documentation text. Each user
  scrapes their own local copy directly from learn.liferay.com. See
  [`docs/adr/0001-crawl4ai-based-corpus-pipeline.md`](docs/adr/0001-crawl4ai-based-corpus-pipeline.md)
  for the full reasoning on why that's the safer distribution model.
- **No embeddings, no vector DB.** Plain `grep` + `Read` over ~1,800
  well-organized Markdown files is fast enough — the `liferay-expert` skill
  just searches those docs directly.
- **One shared docs folder, not per-project.** The scraper writes to a single
  OS-appropriate per-user directory (resolved by `resolve_docs_dir()`), so
  every project that installs the skill reads the same docs instead of
  duplicating a ~30-40 minute scrape.

## How it works

1. **Scrape:** `uvx liferay-docs-scraper` runs a [crawl4ai](https://github.com/unclecode/crawl4ai)
   (free, self-hosted, Playwright-based) BFS crawl of `learn.liferay.com/w/dxp/*`
   and writes clean Markdown to `raw/{capability}/*.md`, one file per page,
   across 14 Liferay DXP capabilities.
2. **Install:** `npx skills add mordonez/liferay-docs-scraper --skill liferay-expert`
   drops the `liferay-expert` skill into any project's `.claude/skills/`.
3. **Ask:** Claude Code greps the docs for the relevant capability, reads
   the matching page(s), and answers — always citing the source URL from
   that file's frontmatter.

## Contents

- [Quickstart](#quickstart)
- [Reference: the scraper in detail](#reference-the-scraper-in-detail)
- [Reference: the skill in detail](#reference-the-skill-in-detail)

## Quickstart

The recommended order for a first-time setup: scrape, then install the
skill, then ask questions.

**1. Scrape the docs (one-time, ~30-40 min):**

```bash
uvx --from crawl4ai crawl4ai-setup   # one-time, installs Playwright browsers
uvx liferay-docs-scraper
```

Run this from anywhere -- it does not write into your current directory,
see "Reference: the scraper in detail" below for exactly where it goes.

**2. Install the skill into whatever project you're working in:**

```bash
npx skills add mordonez/liferay-docs-scraper --skill liferay-expert -a claude-code
```

You'll see:

```
◇  Installed 1 skill ───────────────────╮
│                                       │
│  ✓ liferay-expert (copied)            │
│    → ./.claude/skills/liferay-expert  │
│                                       │
├───────────────────────────────────────╯
```

**3. Ask Claude Code a Liferay question**, e.g. "how do I configure a
synonym set in Liferay search?" The skill finds the docs, greps the
`search` capability, reads `search-administration-and-tuning-synonym-sets.md`,
and answers grounded in that page -- citing
`https://learn.liferay.com/w/dxp/search/search-administration-and-tuning/synonym-sets`
as the source.

The docs are shared across every project where you install the skill (see
"OS default location" below), so step 1 is only ever needed once per
machine -- rerun it later just to refresh, not per-project.

**If you install the skill without doing step 1 first** (or the docs go
stale), it notices and tells you what to run rather than guessing or
answering ungrounded -- it never launches the ~30-40 min scrape on its own
mid-conversation. See "Step 1/2" in `skills/liferay-expert/SKILL.md` for
that check.

## Reference: the scraper in detail

Requires Python 3.10-3.13 (crawl4ai's Playwright dependency doesn't yet
support 3.14) and [uv](https://docs.astral.sh/uv/).

```bash
# One-time: installs the Playwright/Chromium browser crawl4ai drives
uvx --from crawl4ai crawl4ai-setup

# From anywhere -- the docs do NOT go in your current directory:
uvx liferay-docs-scraper
```

This takes roughly 30-40 minutes (BFS deep crawl of ~1900 pages across 14
capabilities) and writes to one shared, per-user location (so it's the same
docs no matter which project you're in when the skill looks for it):

| OS | Default location |
|---|---|
| macOS | `~/Library/Application Support/liferay-docs/` |
| Linux | `~/.local/share/liferay-docs/` (or `$XDG_DATA_HOME/liferay-docs`) |
| Windows | `%LOCALAPPDATA%\liferay-docs\` |

Set `LIFERAY_DOCS_DIR` to override (e.g. to keep a project-local copy instead).

Inside that directory:

- `raw/{capability}/*.md` — the docs, one file per page
- `raw/_navigation/{capability}/*.md` — pure TOC pages, kept but deprioritized
- `raw/_removed/{capability}/*.md` — pages confirmed gone from the live site
- `reports/filtered/` — URL manifests, self-hosted prune log, run summary

Re-run it anytime (weekly recommended) to refresh: it starts from zero every
time, so it naturally picks up new pages, updates changed ones, and
quarantines (never deletes) removed ones. If that directory is (or becomes)
a git repo -- worth doing once, purely as a local diffing tool, nothing needs
pushing anywhere -- it also runs `check-regressions` automatically afterward
and flags any file that shrank by more than half or grew more than 3x versus
the last commit (signals of a broken fetch); see
`docs/adr/0001-crawl4ai-based-corpus-pipeline.md` for why that check exists.

## Reference: the skill in detail

```bash
npx skills add mordonez/liferay-docs-scraper --skill liferay-expert
```

Or just copy `skills/liferay-expert/SKILL.md` into `.claude/skills/liferay-expert/`
in any project. Claude Code picks it up automatically; the skill itself
resolves `$LIFERAY_DOCS_DIR` (or the OS default above) to find the docs,
so it works the same regardless of which project you installed it into.

## License

[MIT](LICENSE) — applies to this tool and skill only, not to the Liferay
documentation text it helps you fetch (that stays Liferay's, and each user
scrapes their own local copy directly from learn.liferay.com).
