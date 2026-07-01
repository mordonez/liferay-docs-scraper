# 0001: Use crawl4ai (self-hosted) for the entire discovery + extraction pipeline

- **Status:** Accepted
- **Date:** 2026-07-01
- **Scope:** `src/liferay_docs_scraper/pipeline.py`, `filter_urls.py`, `check_regressions.py` (paths as of this writing were `scripts/crawl4ai_pipeline.py` etc.; the project was later repackaged as an installable tool, see the repo's own history/later ADRs), the `raw/` docs folder and `reports/filtered/` manifests it produces.

## Context

The docs are a Markdown mirror of `learn.liferay.com/w/dxp/*` (all 14
capabilities: cloud, search, self-hosted, sites, security, development,
commerce, personalization, low-code, content-management-system,
digital-asset-management, integration, ai, getting-started), meant as
grounding material a Claude Code skill searches and cites when answering
Liferay DXP questions.

The project needs to **re-run the whole pipeline from scratch every week**
to pick up new pages, detect removed pages, and refresh changed content.
That recurring, unattended nature is why the tool choice and safety
behavior below matter more than they would for a one-off scrape.

### Starting point: Firecrawl

The pipeline originally used Firecrawl (`firecrawl map` for URL discovery,
then `firecrawl scrape` per URL for content, both via the already-authenticated
`firecrawl` CLI, no API key management needed). This worked, but:

- Firecrawl is a paid API with a monthly credit budget (1,000 credits/cycle
  observed) and a 2-concurrent-job cap on the plan in use. A single full run
  over ~1,000 URLs consumed nearly the entire monthly budget by itself —
  incompatible with running the pipeline **every week**.
- `only_main_content=true` still included the breadcrumb, sidebar TOC, a
  maintenance banner, and the full global site footer, requiring a
  post-hoc cleanup pass (`scripts/clean_boilerplate.py`) with its own
  regex-based header/footer cutting logic and a "give up, don't touch it"
  fallback for pages whose template didn't match the expected shape.

## Decision

Replace Firecrawl entirely with **crawl4ai**, a free, self-hosted,
Playwright-based crawler. It needs Python <=3.13 (its dependency chain did
not yet support the system's Python 3.14 at the time of writing) -- run
initially from an ad hoc virtualenv, later packaged properly as an
installable `uv`/PyPI tool (`uvx liferay-docs-scraper`), which resolves the
Python-version constraint automatically instead of requiring a manually
managed venv. `crawl4ai-setup` (installs the Playwright/Patchright Chromium
builds) is still a required one-time step either way.

A single `crawl4ai` **BFS deep crawl** (`BFSDeepCrawlStrategy`, seeded at
`/w/dxp/index`) now does both discovery and extraction in one pass per
page:

- crawl4ai extracts a page's outbound links from the **full page DOM**
  regardless of `css_selector` — confirmed by reading
  `content_scraping_strategy.py`'s `_process_element(url, body, ...)` call,
  which always receives the unfiltered `body`, not the `css_selector`-scoped
  `content_element`. This means the same fetch that gives us clean content
  also gives us the links needed to keep discovering the rest of the site;
  no separate "map" phase is needed.
- Each visited page is classified against `filter_urls.CAPABILITIES` (14
  capability path prefixes) plus the self-hosted-specific prune rules
  (`SELF_HOSTED_PRUNE_RULES`, for quarterly deprecation/breaking-change
  subpages and a couple of legacy install-doc trees that are out of scope).
  In-scope, unpruned pages are written to `raw/{capability}/{slug}.md`.

### Content selector: `.learn-article-content`, not `#main-content`

Firecrawl's cleanup problem (breadcrumb/TOC/banner/footer chrome mixed into
"main content") does not require a Firecrawl-specific fix — it was a
selector-precision problem. Inspecting the rendered DOM found that
`learn.liferay.com`'s article template renders:

- the maintenance banner and the global site footer as **siblings outside**
  `#main-content`,
- but the breadcrumb, sidebar TOC, and "Submit Feedback" button **inside**
  `#main-content`, alongside the real article,
- with the real article (title, body, Resource Type / Feature / Deployment
  Approach tags) isolated in a **nested** element carrying the class
  `.learn-article-content`.

Setting `css_selector=".learn-article-content"` instead of `"#main-content"`
therefore returns already-clean Markdown with no further processing needed.
This was verified **byte-for-byte identical** to the output of the old
regex-based header-cut logic on a sample page, and it even fixed the one
page template (a legacy Knowledge Base article) that the regex approach
couldn't handle and had to skip.

**Result:** all of `scripts/clean_boilerplate.py` (frontmatter-splitting,
header-cut regex, footer-cut regex, the `NotCleanable` fallback path, and
its whole CLI) became dead code and was deleted. `crawl4ai_pipeline.py`
does not need a chrome-stripping step at all.

### Link-following exclusions: `ContentTypeFilter`, not a hand-written extension list

An early full run picked up several bogus entries in `raw/` — `.zip`,
`.js`, and `.png` asset links (referenced *from* doc pages, e.g. sample
downloads and screenshots) that got treated as if they were HTML pages,
producing empty garbage files. The first fix was a hand-written
`URLPatternFilter(patterns=["*.zip", "*.js", "*.png", ...], reverse=True)`
covering 11 extensions.

That list was replaced with crawl4ai's built-in
`ContentTypeFilter(allowed_types=["text/html"])`, which ships an 80+
extension → MIME-type map and checks the resource type properly instead of
guessing from a URL suffix — including malformed cases like
`...icon-actions.pngmd` (a mangled relative-link join our extension list
would have missed).

### Discovery strategy considered and rejected: sitemap-based `AsyncUrlSeeder` / `DomainMapper`

crawl4ai also ships `AsyncUrlSeeder` (bulk URL discovery from a sitemap or
Common Crawl) and `DomainMapper` (8-source domain reconnaissance: sitemap,
Common Crawl, Wayback Machine, crt.sh, robots.txt, RSS/Atom feeds, homepage
link extraction, and common-path probing). Both were evaluated as a
possible replacement for the BFS crawl, since BFS is inherently limited to
pages reachable by link-following from the seed and did miss some live
pages (see "known limitation" below).

Rejected for this site: `learn.liferay.com/sitemap.xml` is a **sitemap
index** of 72 per-CMS-layout sub-sitemaps (organized by the page-builder's
internal layout IDs, not by the KB article tree), and the sub-sitemaps
sampled were empty. This structure doesn't map usefully onto the `/w/dxp/*`
KB content this project needs, so sitemap-based seeding would add
complexity without solving the coverage gap. `DomainMapper`'s extra
sources (Wayback, crt.sh, Common Crawl) are aimed at discovering unknown
subdomains/hosts, which isn't relevant to a single, well-known host — using
it here would just be slower for no benefit. BFS deep crawling remains the
right tool for this site.

### Reliability hardening

Two content-integrity bug classes surfaced during the first full 14-capability
run, neither of which crawl4ai itself flags as a failure (`result.success`
is `True` in both cases):

1. **Client-side error banner instead of real content** ("An unexpected
   error occurred.") — a transient render/server hiccup.
2. **Wrong or truncated content** — one page briefly returned a *sibling*
   page's content (session/concurrency mixup); another was cut off
   mid-section (incomplete render).

Mitigations, in order of where they act:

- `wait_for=f"css:{CONTENT_SELECTOR}"` on every fetch: poll for the article
  container to exist in the DOM before extracting, instead of capturing at
  a fixed point in the load sequence. Verified to add no measurable latency.
  This should reduce (not necessarily eliminate) class 2 above; it doesn't
  address class 1, and a session-mixup like the sibling-content case isn't
  a DOM-readiness problem at all.
- `is_broken_content()`: flags a body under 30 characters or containing
  the known error-banner text, and triggers up to 2 isolated re-fetches
  (`refetch_single_page`, outside the deep crawl, with backoff) before
  giving up. If still broken, the page is **never written** — an existing
  good file is left untouched rather than overwritten with garbage, and the
  URL is reported under "fetch failures" for manual attention.
- `check_regressions.py` (`check-regressions` as an installed entry point),
  run **after** every pipeline run, diffs
  every changed `raw/**/*.md` body (frontmatter excluded) against a given
  git ref (default `HEAD`) and flags:
  - **shrinkage** below 50% of the previous size (default
    `--shrink-threshold`) — this is what actually caught the truncated
    "wrong sibling content" case in review, since that page's body wasn't
    short or error-banner text, just *wrong*, which the inline checks above
    cannot detect (they have no notion of "what this URL is supposed to
    contain" — only git history does).
  - **growth** beyond 3x the previous size (default `--growth-threshold`)
    — added as a safety net for the one failure mode the selector-based
    approach introduces: if `.learn-article-content` ever fails to match on
    some future page, crawl4ai's scraping strategy falls back to the whole
    page body instead of raising, which would show up as an abnormally
    *large* file rather than a short one.

  **This two-sided check only exists because git is now initialized in
  this repo and every pipeline run is committed.** Before git was
  introduced (partway through the migration, after some content had
  already been overwritten with no way back), there was no way to answer
  "did this run silently corrupt something" other than manual URL-by-URL
  spot checks. Every future run should be followed by
  `check_regressions.py` and a commit before starting the next one.

### Removed-content handling: verify-before-quarantine, never hard-delete

Because every run starts from zero, a page that existed after the last run
but wasn't found this run is ambiguous: it could be genuinely removed from
the site, or it could simply be a page BFS didn't re-discover this time
(still reachable directly by URL, just no longer linked from wherever the
crawl reached). The first full run treated "not rediscovered" as "removed"
and quarantined (moved to `raw/_removed/{capability}/`, logged to
`reports/filtered/removed_log.jsonl`) 21 pages — **all 21 turned out to
still be live** (manually verified with direct `curl` requests). This was
a real near-miss: nothing was permanently lost only because quarantine
moves files instead of deleting them, but it was a false-positive rate of
100% on that first attempt.

Fixed with `is_confirmed_gone(url)`: before quarantining any orphan
candidate, do a direct `HEAD` request (via `urllib.request`, no browser)
straight to that URL. Only a confirmed `404`/`410` gets quarantined.
**Any other outcome — 200, a different error, a timeout, a network hiccup
on our end — is treated as "not confirmed," and the file is left in place**
and reported separately ("still alive, BFS coverage gap") for manual
review. As of this writing, 21 pages remain in that "known-live-but-currently-unlinked"
state every run — a real, small, accepted gap in BFS coverage, not a bug to
chase further given the sitemap-seeding alternative was rejected above.

Additionally, if a capability's in-scope page count drops below 50% of its
previous count (`QUARANTINE_SAFETY_RATIO`), quarantine is skipped
*entirely* for that capability and flagged for manual review — protecting
against a partially-failed crawl run being mistaken for mass content
removal.

### Scope: all 14 capabilities, not just 6

The pipeline originally targeted 6 of the 14 capabilities listed on
`/w/dxp/index` (cloud, search, self-hosted, sites, security, development),
matching a Firecrawl-era credit budget that made processing all ~1,900
pages impractical. Once crawl4ai removed the cost constraint, scope was
expanded to all 14 (`filter_urls.CAPABILITIES` now lists all of them;
`OUT_OF_SCOPE_PREFIXES` is empty). The BFS crawl already visited every page
under `/w/dxp/*` regardless of capability scope (needed it to know what to
exclude), so widening scope did not meaningfully increase crawl time — it
only changed which already-fetched pages get persisted.

## Consequences

**Positive**

- No per-page cost and no concurrency cap tied to a paid plan — the
  pipeline can run in full every week indefinitely.
- Cleaner content at the source (CSS selector) instead of post-hoc regex
  cleanup — less code, and it fixed a page template regex cutting
  couldn't handle.
- Full 14-capability coverage, not a 6-capability subset chosen for cost
  reasons.
- The Firecrawl-era scraping scripts (`extract_content.py`, `poc_crawl4ai.py`,
  `clean_boilerplate.py`) and the one-time `reports/dxp_urls.json`
  Firecrawl-map dump were deleted as dead weight, leaving just
  `pipeline.py`, `filter_urls.py`, and `check_regressions.py`.

**Negative / accepted risks**

- Requires ~350MB of downloaded Chromium browser builds (`crawl4ai-setup`)
  and a <=3.13 Python interpreter -- an operational dependency Firecrawl (a
  hosted API) didn't have. Packaging as a `uv`-installable tool later made
  the interpreter-version part of this a non-issue (`uv` fetches the right
  Python automatically), but the browser download is inherent to
  self-hosted, headless-browser crawling and isn't going away.
- Self-hosted headless-browser crawling surfaced content-integrity bugs
  (error banners reported as success, cross-page content mixups,
  truncated renders) that a hosted, more mature scraping API might handle
  internally. Mitigated as described above, but not eliminated with
  certainty — `check_regressions.py` after every run is a required step,
  not an optional nicety.
- BFS link-following has a small, accepted coverage gap (~1% of pages,
  currently 21) for pages that are live but unlinked from anywhere our
  crawl reaches. These are never silently dropped (verify-before-quarantine
  keeps them in place) but they also don't get refreshed automatically;
  periodic manual review of the "still alive" report is needed.
- The BFS crawl visits every page under `/w/dxp/*` (~1,900+) even though
  only pages matching a known capability prefix get persisted — some
  wasted rendering work compared to a hypothetically perfect targeted
  crawl, judged acceptable since it's free and still fast (tens of minutes,
  not hours).

## Lessons learned (for future runs / future migrations like this one)

1. **Initialize version control *before* running anything that overwrites
   a docs folder in place, not after.** This repo had no git history when the
   first full crawl4ai run started; by the time `git init` happened
   (prompted by the user asking "shouldn't we have backed this up first?"),
   a large fraction of `raw/` had already been overwritten with no way to
   recover the pre-migration (Firecrawl) content. Nothing was lost in the
   end (the new content was verified equivalent), but it was luck, not
   process, that made that true.
2. **"Not rediscovered by a link-following crawl" is not proof of
   removal.** Verify with a direct request to the specific URL before
   taking any destructive/quarantine action based on absence.
3. **A tool reporting `success: True` is not proof the content is
   correct.** Both content-integrity bugs found here were fetches crawl4ai
   considered successful. Application-level validation (length/marker
   checks, and especially diffing against known-good history) is still
   necessary on top of the library's own success/failure signal.
4. **Prefer a precise CSS selector over post-hoc cleanup regex.** Spending
   time inspecting the actual rendered DOM (via a throwaway
   `BeautifulSoup` pass over `result.cleaned_html`) to find a tighter,
   purpose-built class (`.learn-article-content`) eliminated an entire
   category of custom cleanup code, rather than making that code more
   robust.
5. **Prefer a library's built-in filter over a hand-maintained list**
   when one exists and fits (`ContentTypeFilter` vs. a manually maintained
   file-extension list) — it's both less code and more correct.
6. **Re-evaluate "which tool for URL discovery" per-site, not in the
   abstract.** Sitemap-based seeding is the officially recommended
   "fast path" for bulk discovery in crawl4ai's own docs, but this
   specific site's sitemap structure (CMS-layout-based, not
   content-tree-based) made it a worse fit than BFS deep crawling despite
   BFS's own coverage gap.

## Follow-ups (explicitly deferred, not part of this decision)

- No cron/scheduled job has been configured yet to actually run this
  weekly and unattended — `pipeline.py` is ready for that, but wiring up
  the recurring execution was intentionally left as a separate, explicit
  step requiring its own confirmation.
- The 21 "known-live-but-unlinked" pages are not being actively
  re-fetched; they need either periodic manual attention or a future
  decision on whether to seed them explicitly (e.g., a small hardcoded
  seed list) so they participate in the diffing/refresh cycle like
  everything else.
- A separate, later decision dropped the distillation phase entirely
  (manual, one-page-at-a-time summarization didn't scale to the docs'
  size) rather than leaving it "unrelated and unaffected" as originally
  assumed here -- the Claude Code skill this docs folder feeds reads `raw/`
  directly instead. `classify_pages.py`'s navigation-vs-content heuristic
  survived that change: it's now used inline by this pipeline to route
  pure navigation/TOC pages to `raw/_navigation/{capability}/` instead of
  `raw/{capability}/`, rather than as input to a distillation step.
