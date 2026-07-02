---
name: liferay-expert
description: Answer Liferay DXP technical questions by searching and reading locally scraped documentation (hundreds of pages across 14 capabilities, mirrored from learn.liferay.com/w/dxp). Use when the user asks how something works in Liferay DXP, wants configuration/troubleshooting steps, or asks about a specific capability (search, commerce, sites, security, self-hosted installation/upgrades, development, cloud, low-code, content management, digital asset management, personalization, integration, AI, or getting started).
---

# Liferay Expert

Ground every Liferay DXP answer in the scraped docs — don't answer from
memory alone when this skill applies. Find the actual doc, read it, cite it.

## Step 1: find the docs

The docs live in one shared location, not in whatever project you're
currently in (so it isn't duplicated per-project). Resolve it once per
conversation:

- If `$LIFERAY_DOCS_DIR` is set, use that.
- Otherwise use the default: `~/.liferay-docs` (same name on macOS, Linux, and
  Windows -- the leading dot only actually hides it from a plain listing on
  macOS/Linux; on Windows it's just part of the folder name).

Call this `$DOCS_DIR` below. It should contain a `raw/` subfolder.

## Step 2: is it there, and is it fresh?

- **No `raw/` under `$DOCS_DIR`?** Tell the user to run the scraper once
  (takes ~30-40 min, hits learn.liferay.com directly):
  ```
  uvx --from crawl4ai crawl4ai-setup   # one-time, installs Playwright browsers
  uvx liferay-docs-scraper
  ```
  Don't launch this yourself mid-conversation — it's long-running and the
  user should choose when to wait for it.
- **`raw/` exists?** Check a few files' `fetched_at` frontmatter. If it's
  more than ~7 days old, mention the docs may be stale and that
  `uvx liferay-docs-scraper` refreshes them (still answer with what's
  there — don't block on refreshing).

## Step 3: search and answer

1. Pick the likely capability folder(s) from the map below.
2. `grep -ril "<keyword>" $DOCS_DIR/raw/<capability>/*.md` — try 2-3 keyword
   variants. Ignore any hits under `raw/_navigation/` (TOC-only, no unique
   content).
3. Read the matching file(s) in full with the Read tool.
4. Answer grounded in what you read. Always cite the source: the file's
   frontmatter `url:` field.
5. **Official docs came up empty or thin, especially for a "how do I..." or
   "getting this error..." question?** Try the community content next:
   `grep -ril "<keyword>" $DOCS_DIR/raw/community-howto/<capability>/*.md
   $DOCS_DIR/raw/community-troubleshooting/<capability>/*.md` (also check
   `.../community-{howto,troubleshooting}/_uncategorized/*.md` — many of
   these articles aren't tagged with a capability at all). If a capability
   isn't obvious, community-troubleshooting articles are usually titled
   after the exact error message, so grepping the error text directly
   works well.
6. Nothing matches anywhere? Say so — try another capability or keyword
   before giving up, don't guess at an answer.

**Citing community content:** always say explicitly that it's community-
contributed, not official Liferay documentation (e.g. "According to a
community How-To article: ..."), still citing the source URL. Prefer an
official-docs answer over a community one when both cover the same
question — the frontmatter's `source_type:` field tells you which is
which (`source_type: community-howto` / `community-troubleshooting` vs.
no `source_type` field at all for official docs).

## Capability map

| Folder | Covers |
|---|---|
| `search` | Elasticsearch/OpenSearch/Solr, indexing, reindexing modes, search blueprints, facets, semantic search |
| `commerce` | Storefronts, pricing, orders, inventory, product catalogs, payments |
| `development` | Client extensions, service builder, APIs, theming, traditional Java dev, tooling |
| `sites` | Pages, site settings, page fragments, navigation, content pages |
| `low-code` | Objects, forms, workflow |
| `security` | Administration, permissions, users, SSO, virtual instances |
| `self-hosted` | Installation, upgrades, cloud-native experience (CNE), JVM tuning |
| `content-management-system` | Web content, blogs, documents, translations, tags/categories |
| `integration` | Headless/REST APIs, OAuth2, webhooks |
| `cloud` | Liferay Cloud/PaaS config, networking, scaling, migration |
| `digital-asset-management` | Documents and media, DAM DevOps, AI image generation |
| `personalization` | Segmentation, experiences (A/B testing), Analytics Cloud |
| `ai` | AI integrations (only 2 pages) |
| `getting-started` | Onboarding, Docker quick start, basic navigation |

When the right capability isn't obvious, grep 2-3 likely candidates rather
than guessing one and stopping.

## Notes

- All paths above (`raw/...`, `reports/...`) are relative to `$DOCS_DIR` from
  Step 1, not the current project directory.
- `raw/_navigation/{capability}/` = TOC-only pages, excluded on purpose —
  skip them, their linked subpages exist as real files elsewhere.
- `raw/_removed/{capability}/` = pages no longer on the live site. Only use
  as a last resort, and say explicitly that the source may be outdated.
- The docs refresh on demand via `uvx liferay-docs-scraper` (rerun weekly if
  you want to stay current); each file's `fetched_at` frontmatter tells you how
  current it is.
- `reports/filtered/{capability}_urls.txt` lists every in-scope URL per
  capability if you need to browse available topics without grepping content.
- `raw/community-howto/` and `raw/community-troubleshooting/` are a separate,
  much larger (~4,800 pages) set of community-contributed recipes and
  troubleshooting articles from learn.liferay.com/kb-article/*, fetched by
  `uvx --from liferay-docs-scraper liferay-docs-scraper-community` (a
  separate, multi-hour command -- not part of the weekly official-docs
  refresh, and not required for this skill to work at all). Same
  capability folder names as the official docs, plus a `_uncategorized/`
  bucket for articles the site itself didn't tag with a capability. Lower
  authority than official docs -- see Step 3.
