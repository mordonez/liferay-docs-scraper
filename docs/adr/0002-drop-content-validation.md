# 0002: Drop content validation entirely -- the scraper only fetches and saves

- **Status:** Accepted
- **Date:** 2026-07-02
- **Supersedes:** the "Reliability hardening" section of
  [`0001-crawl4ai-based-corpus-pipeline.md`](0001-crawl4ai-based-corpus-pipeline.md)
- **Scope:** `src/liferay_docs_scraper/pipeline.py`, deleted `check_regressions.py`

## Context

ADR-0001 documented two content-integrity bugs found during real testing,
both cases where crawl4ai reported a fetch as successful (`result.success
== True`) but the content was actually wrong: a client-side error banner
instead of the real page, and (rarer) a page returning a *different* page's
content or getting cut off mid-render. It added two layers of protection:

1. An inline check (`is_broken_content()`): flag an empty/error-banner body,
   retry up to twice, and if still broken, leave any existing good file
   untouched rather than overwriting it with garbage.
2. `check_regressions.py`: after each run, if the docs directory happened
   to be a git repo, diff every changed file's body against the last
   commit and flag anything that shrank by more than half or grew more
   than 3x -- the only mechanism that could catch the "wrong but
   plausible-looking" content case, since that's not detectable from a
   single fetch in isolation.

In practice, (2) required understanding and maintaining a second git
repository living inside a personal data cache folder (`~/liferay-docs`),
which was confusing enough that it came up unprompted as "I don't
understand why this needs git" from direct user feedback, even after two
rounds of trying to de-emphasize and clarify it (making it fully optional,
renaming "corpus" to "docs", moving the explanation to an "optional, for
extra safety" callout). The friction of explaining and maintaining it kept
outweighing how rarely it actually mattered.

## Decision

Remove all content validation from the scraper. Delete
`check_regressions.py` entirely, delete `is_broken_content()` and the
retry-on-broken-content logic from `pipeline.py`. The tool now does exactly
one thing: fetch each in-scope page and write whatever crawl4ai returns,
no quality judgment applied.

This was an explicit, informed trade-off, not an oversight: the two bug
classes from ADR-0001 are real and can recur (headless-browser crawling
under concurrency has no strong guarantee against them), and removing
validation means a future occurrence will silently land in `~/liferay-docs`
undetected, and the `liferay-expert` skill could cite it as fact. The
decision to accept that risk in exchange for a simpler tool was made with
that trade-off stated plainly, not assumed away.

## What's still in place (not part of this decision)

Two mechanisms that look superficially similar were deliberately kept,
because they protect against a different, more fundamental risk than
content correctness -- **losing or misclassifying pages entirely**:

- `is_confirmed_gone()` / verify-before-quarantine: before treating a page
  as removed from the site, it does a direct HTTP check on that specific
  URL rather than trusting BFS non-rediscovery alone (which had a 100%
  false-positive rate the one time it was tried without this check, per
  ADR-0001). This is about *whether a page still exists*, not whether its
  fetched text is correct.
- `QUARANTINE_SAFETY_RATIO`: skip quarantining an entire capability if its
  page count implausibly dropped, protecting against a partially-failed
  crawl being mistaken for mass content removal.

Both stay because getting them wrong is destructive (losing pages that are
still live) in a way that "this one page's text might be subtly wrong"
isn't -- and neither requires git or any extra setup, so neither carried
the complexity cost this ADR is about removing.

## Consequences

**Positive**

- One fewer file, one fewer CLI entry point (`check-regressions` removed
  from `pyproject.toml`), no more "why does my docs folder need to be a
  git repo" question for anyone using this tool.
- `pipeline.py` is simpler to read: fetch, classify, write. No retry
  loop, no error-marker list, no git subprocess calls.

**Negative / accepted risk**

- If a page's content silently comes back wrong (confirmed to happen, not
  hypothetical), nothing in this tool will detect it. It will sit in
  `~/liferay-docs` as if it were correct until someone happens to notice,
  and the `liferay-expert` skill will cite it without any indication it
  might be unreliable.
- Anyone who wants the old safety net back can still `git init`
  `~/liferay-docs` and run `git diff` by hand after a refresh to spot
  large swings -- the mechanism wasn't complicated, just no longer
  built into the tool.

## Lesson learned

A safety net that requires explaining a whole extra concept (a second git
repo, in a data folder, that the user never asked for) to justify catching
a failure mode that occurred twice in one large test run is a legitimate
thing to cut, even though the failure mode is real. "This is correct and
thorough" and "this is worth the complexity" are different questions, and
repeated user confusion about the same feature across multiple rounds of
clarification is a strong signal the answer to the second question is no.
