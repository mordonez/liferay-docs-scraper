# liferay-docs-scraper

Scrapes `learn.liferay.com/w/dxp/*` into a local, clean Markdown corpus
(`raw/{capability}/*.md`) and ships a Claude Code skill (`liferay-expert`)
that answers Liferay DXP questions by searching and citing that corpus.

**This repo does not ship Liferay's documentation.** It ships the code that
scrapes it, and a skill that reads whatever you scrape locally. Each user
builds and refreshes their own copy directly from learn.liferay.com.

## Quickstart

This is the actual first-run experience, in order.

**1. Install the skill into whatever project you're working in:**

```bash
npx skills add <owner>/liferay-docs-scraper --skill liferay-expert -a claude-code
```

(No GitHub remote to point at yet? `npx skills add` also accepts a local
path, e.g. `npx skills add /path/to/liferay-docs-scraper --skill liferay-expert`,
useful for testing before you publish anywhere.) You'll see:

```
◇  Installed 1 skill ───────────────────╮
│                                       │
│  ✓ liferay-expert (copied)            │
│    → ./.claude/skills/liferay-expert  │
│                                       │
├───────────────────────────────────────╯
```

**2. Ask Claude Code a Liferay question**, e.g. "how do I configure a
synonym set in Liferay search?"

**3. First time, there's no corpus yet.** The skill checks for one (see
"Step 1/2" in `skills/liferay-expert/SKILL.md`), doesn't find it, and tells
you to run:

```bash
uvx --from crawl4ai crawl4ai-setup   # one-time, installs Playwright browsers
uvx liferay-docs-scraper             # ~30-40 min, scrapes learn.liferay.com
```

It won't run this for you automatically -- it's long enough that you should
choose when to kick it off, not have it block your first question.

**4. Ask again.** Now the skill finds the corpus, greps the `search`
capability, reads `search-administration-and-tuning-synonym-sets.md`, and
answers grounded in that page -- citing
`https://learn.liferay.com/w/dxp/search/search-administration-and-tuning/synonym-sets`
as the source.

From here on, the corpus is shared across every project where you've
installed the skill (see "OS default location" below) -- you only run the
scraper once, not per-project, and only again when you want to refresh it.

## Reference: the scraper in detail

Requires Python 3.10-3.13 (crawl4ai's Playwright dependency doesn't yet
support 3.14) and [uv](https://docs.astral.sh/uv/).

```bash
# One-time: installs the Playwright/Chromium browser crawl4ai drives
uvx --from crawl4ai crawl4ai-setup

# From anywhere -- the corpus does NOT go in your current directory:
uvx --python 3.13 --from liferay-docs-scraper liferay-docs-scraper
```

This takes roughly 30-40 minutes (BFS deep crawl of ~1900 pages across 14
capabilities) and writes to one shared, per-user location (so it's the same
corpus no matter which project you're in when the skill looks for it):

| OS | Default location |
|---|---|
| macOS | `~/Library/Application Support/liferay-docs/` |
| Linux | `~/.local/share/liferay-docs/` (or `$XDG_DATA_HOME/liferay-docs`) |
| Windows | `%LOCALAPPDATA%\liferay-docs\` |

Set `LIFERAY_DOCS_DIR` to override (e.g. to keep a project-local copy instead).

Inside that directory:

- `raw/{capability}/*.md` — the corpus, one file per page
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
npx skills add https://github.com/<you>/liferay-docs-scraper/tree/main/skills/liferay-expert
```

Or just copy `skills/liferay-expert/SKILL.md` into `.claude/skills/liferay-expert/`
in any project. Claude Code picks it up automatically; the skill itself
resolves `$LIFERAY_DOCS_DIR` (or the OS default above) to find the corpus,
so it works the same regardless of which project you installed it into.

## Why no bundled docs, no embeddings, no vector DB

See `docs/adr/` for the full reasoning. Short version: the corpus is
Liferay's copyrighted documentation text -- distributing the *tool* that
scrapes public pages is a different, much lower-risk thing than a third
party redistributing that text at scale. Plain grep + Read over ~1800
well-organized Markdown files is fast enough that no search index is needed;
add one later if that stops being true.
