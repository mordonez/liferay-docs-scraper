# Low-Value Candidate Pages — Analysis Report

**Purpose:** Identify pages in `raw/{capability}/*.md` that likely add little value to a Claude Code
skill acting as a Liferay DXP expert consultant, so a human can decide what to deprioritize or
exclude before that skill is built. This is a **read-only analysis**. Nothing under `raw/`,
`reports/filtered/`, or any pipeline script was modified. The only artifact touched is a re-run of
`scripts/classify_pages.py` (itself read-only against `raw/`), which refreshed
`reports/page_classification.json` from 1009 files (stale, 6-capability snapshot) to the full
current corpus of **1870 files across 14 capabilities**.

Corpus snapshot at analysis time: 1870 `.md` files in `raw/{ai, cloud, commerce,
content-management-system, development, digital-asset-management, getting-started, integration,
low-code, personalization, search, security, self-hosted, sites}`. `raw/_removed/` exists but is
empty (0 files).

---

## 1. Pure navigation/index pages (no unique technical content)

**Criterion:** `scripts/classify_pages.py`'s heuristic — strip Markdown link syntax to visible
text, strip heading/emphasis markup, then compute `total_words` (words in visible text) and
`link_ratio` (fraction of those words that come from inside a link's link-text span). A page is
classified `"index"` iff `total_words < 150` **and** `link_ratio >= 0.5`. This flags pages that are
mostly a table-of-contents/list of links to subpages, with little original prose.

I re-ran the script (unmodified) against the full `raw/` tree (previously it only covered 1009
files from the original 6-capability snapshot). New full-corpus result:

- **Total files: 1870 → index: 93, content: 1777**

Spot-checked several borderline entries (e.g. `raw/commerce/order-management-order-workflows.md`
at 149 words / 0.53 ratio, `raw/security/administration-configuring-liferay.md` at 94 words / 0.798
ratio, `raw/content-management-system/deprecated-content-features.md` at 130 words / 0.677 ratio) —
all confirmed to be genuine hub/TOC pages with at most 1-2 sentences of orienting prose followed by
a list of subpage links. The heuristic holds up well on manual review.

**Count: 93 files (4.97% of corpus).** Full list, grouped by capability:

### cloud (3)
- `raw/cloud/reference.md` — https://learn.liferay.com/w/dxp/cloud/reference
- `raw/cloud/support-and-troubleshooting.md` — https://learn.liferay.com/w/dxp/cloud/support-and-troubleshooting
- `raw/cloud/tuning-security-settings-information-security-and-liferay-cloud.md` — https://learn.liferay.com/w/dxp/cloud/tuning-security-settings/information-security-and-liferay-cloud

### commerce (13)
- `raw/commerce/add-ons-and-connectors-tradecentric-formerly-punchout2go.md` — https://learn.liferay.com/w/dxp/commerce/add-ons-and-connectors/tradecentric-formerly-punchout2go
- `raw/commerce/add-ons-and-connectors.md` — https://learn.liferay.com/w/dxp/commerce/add-ons-and-connectors
- `raw/commerce/get-help.md` — https://learn.liferay.com/w/dxp/commerce/get-help
- `raw/commerce/order-management-order-workflows.md` — https://learn.liferay.com/w/dxp/commerce/order-management/order-workflows
- `raw/commerce/order-management-orders.md` — https://learn.liferay.com/w/dxp/commerce/order-management/orders
- `raw/commerce/order-management-subscriptions.md` — https://learn.liferay.com/w/dxp/commerce/order-management/subscriptions
- `raw/commerce/order-management.md` — https://learn.liferay.com/w/dxp/commerce/order-management
- `raw/commerce/pricing-configuring-taxes.md` — https://learn.liferay.com/w/dxp/commerce/pricing/configuring-taxes
- `raw/commerce/product-management-creating-and-managing-products.md` — https://learn.liferay.com/w/dxp/commerce/product-management/creating-and-managing-products
- `raw/commerce/product-management.md` — https://learn.liferay.com/w/dxp/commerce/product-management
- `raw/commerce/starting-a-store.md` — https://learn.liferay.com/w/dxp/commerce/starting-a-store
- `raw/commerce/store-management-configuring-shipping-methods.md` — https://learn.liferay.com/w/dxp/commerce/store-management/configuring-shipping-methods
- `raw/commerce/store-management.md` — https://learn.liferay.com/w/dxp/commerce/store-management

### content-management-system (3)
- `raw/content-management-system/blogs-highlighting-recent-bloggers.md` — https://learn.liferay.com/w/dxp/content-management-system/blogs/highlighting-recent-bloggers
- `raw/content-management-system/deprecated-content-features.md` — https://learn.liferay.com/w/dxp/content-management-system/deprecated-content-features
- `raw/content-management-system/web-content-web-content-templates.md` — https://learn.liferay.com/w/dxp/content-management-system/web-content/web-content-templates

### development (20)
- `raw/development/customizing-liferays-look-and-feel-themes-bundling-resources.md` — https://learn.liferay.com/w/dxp/development/customizing-liferays-look-and-feel/themes/bundling-resources
- `raw/development/developing-page-fragments-reference.md` — https://learn.liferay.com/w/dxp/development/developing-page-fragments/reference
- `raw/development/tooling-other-tools-liferay-npm-bundler-bundler-migration-guide-migrating-bundler-projects-intro.md` — https://learn.liferay.com/w/dxp/development/tooling/other-tools/liferay-npm-bundler/bundler-migration-guide/migrating-bundler-projects-intro
- `raw/development/tooling-other-tools-liferay-npm-bundler-bundler-migration-guide.md` — https://learn.liferay.com/w/dxp/development/tooling/other-tools/liferay-npm-bundler/bundler-migration-guide
- `raw/development/tooling-other-tools-liferay-npm-bundler.md` — https://learn.liferay.com/w/dxp/development/tooling/other-tools/liferay-npm-bundler
- `raw/development/tooling-poshi-test-automation-poshi-basics-poshi-layers.md` — https://learn.liferay.com/w/dxp/development/tooling/poshi-test-automation/poshi-basics/poshi-layers
- `raw/development/tooling-reference.md` — https://learn.liferay.com/w/dxp/development/tooling/reference
- `raw/development/traditional-java-based-development-core-frameworks-configuration-framework.md` — https://learn.liferay.com/w/dxp/development/traditional-java-based-development/core-frameworks/configuration-framework
- `raw/development/traditional-java-based-development-core-frameworks-dependency-injection.md` — https://learn.liferay.com/w/dxp/development/traditional-java-based-development/core-frameworks/dependency-injection
- `raw/development/traditional-java-based-development-core-frameworks-servlets.md` — https://learn.liferay.com/w/dxp/development/traditional-java-based-development/core-frameworks/servlets
- `raw/development/traditional-java-based-development-core-frameworks.md` — https://learn.liferay.com/w/dxp/development/traditional-java-based-development/core-frameworks
- `raw/development/traditional-java-based-development-data-frameworks-cache.md` — https://learn.liferay.com/w/dxp/development/traditional-java-based-development/data-frameworks/cache
- `raw/development/traditional-java-based-development-data-frameworks-data-scopes.md` — https://learn.liferay.com/w/dxp/development/traditional-java-based-development/data-frameworks/data-scopes
- `raw/development/traditional-java-based-development-data-frameworks-expando-framework.md` — https://learn.liferay.com/w/dxp/development/traditional-java-based-development/data-frameworks/expando-framework
- `raw/development/traditional-java-based-development-data-frameworks.md` — https://learn.liferay.com/w/dxp/development/traditional-java-based-development/data-frameworks
- `raw/development/traditional-java-based-development-developing-a-web-application-using-bean-portlet-reference.md` — https://learn.liferay.com/w/dxp/development/traditional-java-based-development/developing-a-web-application/using-bean-portlet/reference
- `raw/development/traditional-java-based-development-developing-a-web-application-using-jsf-reference.md` — https://learn.liferay.com/w/dxp/development/traditional-java-based-development/developing-a-web-application/using-jsf/reference
- `raw/development/traditional-java-based-development-developing-a-web-application-using-react.md` — https://learn.liferay.com/w/dxp/development/traditional-java-based-development/developing-a-web-application/using-react
- `raw/development/traditional-java-based-development-developing-a-web-application.md` — https://learn.liferay.com/w/dxp/development/traditional-java-based-development/developing-a-web-application
- `raw/development/traditional-java-based-development-extending-liferay.md` — https://learn.liferay.com/w/dxp/development/traditional-java-based-development/extending-liferay

### digital-asset-management (5)
- `raw/digital-asset-management/developer-guide.md` — https://learn.liferay.com/w/dxp/digital-asset-management/developer-guide
- `raw/digital-asset-management/devops.md` — https://learn.liferay.com/w/dxp/digital-asset-management/devops
- `raw/digital-asset-management/publishing-and-sharing.md` — https://learn.liferay.com/w/dxp/digital-asset-management/publishing-and-sharing
- `raw/digital-asset-management/uploading-and-managing.md` — https://learn.liferay.com/w/dxp/digital-asset-management/uploading-and-managing
- `raw/digital-asset-management/videos.md` — https://learn.liferay.com/w/dxp/digital-asset-management/videos

### integration (7)
- `raw/integration/headless-apis-commerce-apis-order-management-apis.md` — https://learn.liferay.com/w/dxp/integration/headless-apis/commerce-apis/order-management-apis
- `raw/integration/headless-apis-commerce-apis-product-management-apis.md` — https://learn.liferay.com/w/dxp/integration/headless-apis/commerce-apis/product-management-apis
- `raw/integration/headless-apis-commerce-apis.md` — https://learn.liferay.com/w/dxp/integration/headless-apis/commerce-apis
- `raw/integration/headless-apis-content-management-apis.md` — https://learn.liferay.com/w/dxp/integration/headless-apis/content-management-apis
- `raw/integration/headless-apis-object-apis.md` — https://learn.liferay.com/w/dxp/integration/headless-apis/object-apis
- `raw/integration/headless-apis-user-management-apis.md` — https://learn.liferay.com/w/dxp/integration/headless-apis/user-management-apis
- `raw/integration/index.md` — https://learn.liferay.com/w/dxp/integration

### low-code (10)
- `raw/low-code/forms-creating-and-managing-forms.md` — https://learn.liferay.com/w/dxp/low-code/forms/creating-and-managing-forms
- `raw/low-code/forms-developer-guide.md` — https://learn.liferay.com/w/dxp/low-code/forms/developer-guide
- `raw/low-code/index.md` — https://learn.liferay.com/w/dxp/low-code
- `raw/low-code/objects-creating-and-managing-objects-using-system-objects-with-custom-objects.md` — https://learn.liferay.com/w/dxp/low-code/objects/creating-and-managing-objects/using-system-objects-with-custom-objects
- `raw/low-code/objects-integrating-objects-with-third-party-services-using-google-sheets-with-objects.md` — https://learn.liferay.com/w/dxp/low-code/objects/integrating-objects-with-third-party-services/using-google-sheets-with-objects
- `raw/low-code/objects-integrating-objects-with-third-party-services.md` — https://learn.liferay.com/w/dxp/low-code/objects/integrating-objects-with-third-party-services
- `raw/low-code/workflow-designing-and-managing-workflows.md` — https://learn.liferay.com/w/dxp/low-code/workflow/designing-and-managing-workflows
- `raw/low-code/workflow-developer-guide.md` — https://learn.liferay.com/w/dxp/low-code/workflow/developer-guide
- `raw/low-code/workflow-using-workflows.md` — https://learn.liferay.com/w/dxp/low-code/workflow/using-workflows
- `raw/low-code/workflow.md` — https://learn.liferay.com/w/dxp/low-code/workflow

### personalization (5)
- `raw/personalization/analytics-cloud-optimization.md` — https://learn.liferay.com/w/dxp/personalization/analytics-cloud/optimization
- `raw/personalization/analytics-cloud-reference.md` — https://learn.liferay.com/w/dxp/personalization/analytics-cloud/reference
- `raw/personalization/analytics-cloud-troubleshooting.md` — https://learn.liferay.com/w/dxp/personalization/analytics-cloud/troubleshooting
- `raw/personalization/analytics-cloud-workspace-settings.md` — https://learn.liferay.com/w/dxp/personalization/analytics-cloud/workspace-settings
- `raw/personalization/analytics-cloud.md` — https://learn.liferay.com/w/dxp/personalization/analytics-cloud

### search (9)
- `raw/search/developer-guide.md` — https://learn.liferay.com/w/dxp/search/developer-guide
- `raw/search/getting-started.md` — https://learn.liferay.com/w/dxp/search/getting-started
- `raw/search/index.md` — https://learn.liferay.com/w/dxp/search
- `raw/search/installing-and-upgrading-a-search-engine-solr.md` — https://learn.liferay.com/w/dxp/search/installing-and-upgrading-a-search-engine/solr
- `raw/search/liferay-enterprise-search-cross-cluster-replication.md` — https://learn.liferay.com/w/dxp/search/liferay-enterprise-search/cross-cluster-replication
- `raw/search/search-administration-and-tuning.md` — https://learn.liferay.com/w/dxp/search/search-administration-and-tuning
- `raw/search/search-pages-and-widgets-search-results.md` — https://learn.liferay.com/w/dxp/search/search-pages-and-widgets/search-results
- `raw/search/search-pages-and-widgets-working-with-search-pages.md` — https://learn.liferay.com/w/dxp/search/search-pages-and-widgets/working-with-search-pages
- `raw/search/search-pages-and-widgets.md` — https://learn.liferay.com/w/dxp/search/search-pages-and-widgets

### security (11)
- `raw/security/administration-configuring-liferay-common-tasks.md` — https://learn.liferay.com/w/dxp/security-and-administration/administration/configuring-liferay/common-tasks
- `raw/security/administration-configuring-liferay-configuration-files-and-factories.md` — https://learn.liferay.com/w/dxp/security-and-administration/administration/configuring-liferay/configuration-files-and-factories
- `raw/security/administration-configuring-liferay-security-settings.md` — https://learn.liferay.com/w/dxp/security-and-administration/administration/configuring-liferay/security-settings
- `raw/security/administration-configuring-liferay.md` — https://learn.liferay.com/w/dxp/security-and-administration/administration/configuring-liferay
- `raw/security/administration-data-integration.md` — https://learn.liferay.com/w/dxp/security-and-administration/administration/data-integration
- `raw/security/administration-file-storage-other-file-store-types.md` — https://learn.liferay.com/w/dxp/security-and-administration/administration/file-storage/other-file-store-types
- `raw/security/administration-installing-and-managing-apps-managing-apps.md` — https://learn.liferay.com/w/dxp/security-and-administration/administration/installing-and-managing-apps/managing-apps
- `raw/security/security-configuring-sso.md` — https://learn.liferay.com/w/dxp/security-and-administration/security/configuring-sso
- `raw/security/users-and-permissions-managing-user-data-consent-management-platform-integration.md` — https://learn.liferay.com/w/dxp/security-and-administration/users-and-permissions/managing-user-data/consent-management-platform-integration
- `raw/security/users-and-permissions-roles-and-permissions.md` — https://learn.liferay.com/w/dxp/security-and-administration/users-and-permissions/roles-and-permissions
- `raw/security/users-and-permissions-user-groups.md` — https://learn.liferay.com/w/dxp/security-and-administration/users-and-permissions/user-groups

### self-hosted (3)
- `raw/self-hosted/cloud-native-experience-cne-cloud-provider-ready.md` — https://learn.liferay.com/w/dxp/self-hosted-installation-and-upgrades/cloud-native-experience/cne-cloud-provider-ready
- `raw/self-hosted/cloud-native-experience-cne-reference.md` — https://learn.liferay.com/w/dxp/self-hosted-installation-and-upgrades/cloud-native-experience/cne-reference
- `raw/self-hosted/installing-liferay-on-a-local-server-installing-liferay-on-an-application-server.md` — https://learn.liferay.com/w/dxp/self-hosted-installation-and-upgrades/installing-liferay-on-a-local-server/installing-liferay-on-an-application-server

### sites (4)
- `raw/sites/creating-pages-page-fragments-and-widgets-using-widgets-configuring-widgets.md` — https://learn.liferay.com/w/dxp/sites/creating-pages/page-fragments-and-widgets/using-widgets/configuring-widgets
- `raw/sites/creating-pages-page-fragments-and-widgets.md` — https://learn.liferay.com/w/dxp/sites/creating-pages/page-fragments-and-widgets
- `raw/sites/site-appearance-style-books-developer-guide.md` — https://learn.liferay.com/w/dxp/sites/site-appearance/style-books/developer-guide
- `raw/sites/site-appearance-style-books.md` — https://learn.liferay.com/w/dxp/sites/site-appearance/style-books

**Note:** `ai`, `getting-started`, and `commerce`'s deepest subfolders had zero or very few index
hits — `ai` has only 2 files total (both substantive), `getting-started` has 7 files (all
substantive, none flagged).

---

## 2. Legacy community "How To" Knowledge Base articles with disclaimer boilerplate

**Criterion (as briefed):** community-contributed "How To" articles carrying a disclaimer
containing phrases like *"How To articles are not official guidelines"*, *"Legacy Article"*,
*"FastTrack"*, *"published without a requirement for independent editing or verification"*.

**Search performed:** case-insensitive grep across all of `raw/**/*.md` for each of the above
phrases individually, plus broader nets (`disclaimer`, `legacy article`, `fasttrack`/`fast track`,
`unofficial`, `not official guideline`, `independent editing`, `editorial`, `contributed`,
`knowledge base article`, and filename patterns `*how-to*` / `*howto*`).

**Result: 0 matches.** None of the target disclaimer phrases, nor close variants, appear anywhere
in the current `raw/` tree. The handful of incidental hits on loosely related terms (`editorial`,
`contributed`, `knowledge base article`) were manual-checked and are all normal technical prose
about Liferay's own Knowledge Base *application* (a CMS feature) or about "contributed fragment
sets" in the Fragments developer docs — unrelated to community How-To content.

**Interpretation:** This corpus (`crawl4ai`-based mirror of `learn.liferay.com/w/dxp/*`, per
`docs/adr/ADR-0001`) appears to be scoped to *official* Liferay Learn documentation only. The
community-contributed "How To" KB articles (which live on `community.liferay.com` /
`liferay.dev`, a different site) were evidently never in scope for this crawl, or were filtered out
upstream before reaching `raw/`. The 3 examples the requester recalls from an earlier ingestion may
have come from a prior corpus generation (the git history shows this repo was rebuilt from scratch
with a crawl4ai pipeline — commit `13bf80b "Expand corpus to all 14 learn.liferay.com/w/dxp
capabilities"` — and no trace of a Firecrawl-era artifact or "_removed" content remains;
`raw/_removed/` exists but is empty). **Category count: 0 files.** No action needed for this
category; flagging as a non-finding for completeness.

---

## 3. Version-specific changelog / "what's new" / "breaking changes" pages

**Criterion:** release-note style content tied to a specific product version/quarter — useful for
"catching up on changes" but lower value for an "expert reference" skill that should answer
version-agnostic "how do I do X" questions. Broadened slightly beyond the literal `whats-new-in-*`
filename pattern named in the brief to include the same genre found nearby (breaking-changes and
release-notes pages), since they share the same low-durability, point-in-time nature.

**Search performed:** filename glob for `*whats-new*`, `*release-notes*`, `*changelog*`,
`*new-features*`, `*breaking-changes*`; content grep for "What's New" headings; each match manually
read to confirm it's genuinely version-pinned changelog content (not just a page that happens to
mention "release notes" in passing, e.g. `raw/search/getting-started.md` and
`raw/search/index.md` were excluded — they only reference "release notes" as a pointer elsewhere).

**Count: 6 files (0.32% of corpus).**

### cloud (1)
- `raw/cloud/reference-breaking-changes.md` — https://learn.liferay.com/w/dxp/cloud/reference/breaking-changes

### commerce (3)
- `raw/commerce/installation-and-upgrades-3-0-release-notes.md` — https://learn.liferay.com/w/dxp/commerce/installation-and-upgrades/3-0-release-notes
- `raw/commerce/installation-and-upgrades-3-0-breaking-changes.md` — https://learn.liferay.com/w/dxp/commerce/installation-and-upgrades/3-0-breaking-changes
- `raw/commerce/installation-and-upgrades-4-0-breaking-changes.md` — https://learn.liferay.com/w/dxp/commerce/installation-and-upgrades/4-0-breaking-changes

### search (2)
- `raw/search/getting-started-whats-new-in-search-for-73.md` — https://learn.liferay.com/w/dxp/search/getting-started/whats-new-in-search-for-73
- `raw/search/getting-started-whats-new-in-search-for-74.md` — https://learn.liferay.com/w/dxp/search/getting-started/whats-new-in-search-for-74

**Related but NOT included here (borderline, needs human judgement):** the
`deprecations-and-breaking-changes-reference` family under `self-hosted` and
`content-management-system`. Most of the per-quarter breaking-change subpages were already pruned
at ingestion time (`reports/filtered/summary.json` shows 46 URLs excluded under the
"deprecations-and-breaking-changes-reference subpage" rule, plus 14+14 for two CNE cloud-provider
variants and 5 for "installing earlier Liferay versions"). What remains in `raw/` are the *index*
pages for these families (`raw/self-hosted/upgrading-liferay-deprecations-and-breaking-changes-reference.md`,
already captured in Category 1) and the "deprecated but still supported" feature docs
(`raw/content-management-system/deprecated-content-features*.md`, 19 files — Message Boards and
Wiki documentation). Those 19 files describe features still present in the product (in Maintenance
Mode), not point-in-time changelogs, so they were deliberately **not** flagged here — a Liferay
expert may still legitimately need to answer "how do wikis work in DXP" for a customer running an
older/maintained instance. Worth a human's separate look if disk/context budget is tight.

---

## 4. Extremely short / thin stub pages (non-navigation)

**Criterion:** pages classified `"content"` by `classify_pages.py` (i.e., NOT meeting the
`index` link-ratio threshold) but with very low word counts — in practice these turned out to be
one-paragraph intros to a single subpage link, functionally indistinguishable from a nav stub
despite falling just under the `link_ratio >= 0.5` cutoff (their one link's anchor text is short
relative to the total prose).

**Threshold used:** `total_words < 40` among `"content"`-labeled pages. Read all 8 matches in full
to confirm — every one is a single sentence or two of generic framing text followed by exactly one
link to a "real" subpage (e.g. `raw/commerce/developer-guide-catalog.md`, 29 words: *"Liferay comes
with four product types out-of-the-box. But you can leverage the extension point to add a new
product type of your own."* + one link to "Adding a New Product Type"). The genuinely useful
content lives one level down in the linked subpage, which is captured separately in the corpus.

**Count: 8 files (0.43% of corpus).**

### commerce (5)
- `raw/commerce/developer-guide-catalog.md` (29 words) — https://learn.liferay.com/w/dxp/commerce/developer-guide/catalog
- `raw/commerce/developer-guide-content.md` (39 words) — https://learn.liferay.com/w/dxp/commerce/developer-guide/content
- `raw/commerce/developer-guide-managing-inventory.md` (29 words) — https://learn.liferay.com/w/dxp/commerce/developer-guide/managing-inventory
- `raw/commerce/developer-guide-promotions.md` (30 words) — https://learn.liferay.com/w/dxp/commerce/developer-guide/promotions
- `raw/commerce/order-management-order-importer.md` (37 words) — https://learn.liferay.com/w/dxp/commerce/order-management/order-importer

### integration (3)
- `raw/integration/headless-apis-commerce-apis-inventory-management-apis.md` (19 words) — https://learn.liferay.com/w/dxp/integration/headless-apis/commerce-apis/inventory-management-apis
- `raw/integration/headless-apis-commerce-apis-pricing-apis.md` (37 words) — https://learn.liferay.com/w/dxp/integration/headless-apis/commerce-apis/pricing-apis
- `raw/integration/headless-apis-commerce-apis-store-management-apis.md` (19 words) — https://learn.liferay.com/w/dxp/integration/headless-apis/commerce-apis/store-management-apis

All 8 are effectively "mini-index" pages that just missed the Category-1 threshold. Given how thin
they are, a human reviewer may reasonably choose to fold them into Category 1's treatment rather
than handle them separately.

---

## 5. True or near-duplicate pages across capability folders

**Criterion:** same/near-identical content appearing under two different capability paths (should
not happen given URL-based dedup at ingestion, per the corpus design — this section verifies that).

**Method:** (a) compared `content_hash` from frontmatter across all 1870 files for exact
collisions; (b) extracted the H1 title from every file's body and grouped files by identical title
across *different* capability directories, then manually diffed the bodies of any suspicious
cross-capability title match.

**Result:**
- **(a) Exact `content_hash` collisions: 0.** URL-based dedup is working as intended — no file is
  byte-identical to another.
- **(b) Same-title, cross-capability groups found: 6** — but all are false positives on manual
  inspection:
  - "Getting Started", "Reference", "Developer Guide" — generic section titles reused by many
    unrelated capability subtrees (e.g. `raw/cloud/reference.md` vs.
    `raw/development/tooling-reference.md` vs. `raw/self-hosted/reference.md`); bodies are
    unrelated to each other.
  - "Search" — `raw/commerce/creating-store-content-commerce-storefront-pages-search.md` (a
    storefront search-page config guide) vs. `raw/search/index.md` (the Search capability's own
    landing/index page) — unrelated content, same word only.
  - "Introduction to the Admin Account" —
    `raw/commerce/starting-a-store-introduction-to-the-admin-account.md` (262 words, Commerce admin
    user) vs. `raw/getting-started/introduction-to-the-admin-account.md` (597 words, general DXP
    admin user) — diffed in full; overlapping topic and structure but materially different prose,
    different product scope (Commerce vs. core DXP), and the getting-started version is more than
    2x longer with different steps (setup wizard credentials, production-use warning). Legitimately
    two different docs for two different audiences, not a duplicate.
  - "Multi-Factor Authentication" —
    `raw/personalization/analytics-cloud-reference-multi-factor-authentication.md` (295 words,
    specific to Analytics Cloud's own login MFA) vs.
    `raw/security/security-multi-factor-authentication.md` (93 words, general DXP instance MFA
    config) — diffed in full; completely different content, different product surface.

**Count: 0 true duplicates.** No action needed for this category. This is a good signal that the
URL-based dedup and per-capability partitioning are working correctly.

---

## 6. Other patterns (marketing language, generic pitches)

**Criterion:** any other clear "not useful for a technical expert" pattern noticed while sampling —
applied conservatively, only flagging with concrete evidence.

**Search performed:** grepped for common marketing/fluff phrasing across `raw/`: "unlock the
power", "seamlessly", "why choose Liferay", "next-generation", "cutting-edge", "empower your",
"game-chang(ing)", "revolutioniz(e)", "unparalleled", "best-in-class", "industry-leading".

**Result:** Almost nothing. Only "seamlessly" (9 hits) and "empower your" (2 hits) appear at all,
and in every case they're a single incidental phrase embedded in otherwise substantive technical
prose (e.g. `raw/security/index.md`: *"...empower your users to build the sites you have in
mind"* — one clause inside a real index page already captured in Category 1). No page in the
corpus reads as a pure marketing pitch or "why choose Liferay" style page.

**Count: 0 additional pages flagged.** This confirms the ingestion pipeline's chrome/marketing
stripping (per the task's framing that this was "already solved") is holding up — the corpus reads
as consistently technical throughout the ~30 files sampled directly during this analysis.

---

## Overall Summary and Recommendation

| Category | Count | % of corpus (1870) |
|---|---|---|
| 1. Pure navigation/index pages | 93 | 4.97% |
| 2. Legacy "How To" disclaimer articles | 0 | 0% |
| 3. Version-specific changelog/release-notes/breaking-changes | 6 | 0.32% |
| 4. Thin stub pages (non-nav) | 8 | 0.43% |
| 5. True/near-duplicates | 0 | 0% |
| 6. Marketing/pitch pages | 0 | 0% |
| **Total flagged (categories 1+3+4, no overlap)** | **107** | **~5.7%** |

**Overall recommendation:** Roughly **5.7% of the corpus** (107 of 1870 files) is a reasonable
low-value-candidate pool, and it is concentrated almost entirely in **Category 1 (navigation/index
pages)**. This is the safest category to act on first for three reasons: (1) it has the clearest,
most mechanically verifiable criterion (word count + link ratio, already spot-checked against
several borderline cases and holding up); (2) the "real" content these pages point to is preserved
elsewhere in the corpus as separate files, so excluding the index page itself loses no unique
information — at most it loses a bit of "table of contents" framing that a RAG/retrieval-based
skill likely doesn't need anyway (the skill can reconstruct navigation from capability/slug
structure); and (3) it's by far the largest bucket (93 of the 107 flagged files), so it gives the
best size-to-effort payoff.

Category 4 (8 thin stub pages) is a natural next candidate — same underlying rationale as Category
1, just below the strict threshold; a human could simply lower `INDEX_MIN_LINK_RATIO` slightly or
manually fold these into the Category-1 exclusion set.

Category 3 (6 version-pinned changelog pages) should be a **separate, deliberate decision** rather
than auto-excluded: they're low value for "how do I configure X today" questions but genuinely
useful if the expert skill is ever asked "what changed in 7.4 search" or "what breaks when I
upgrade Commerce to 4.0" — a plausible query for a consultant-style skill. Recommend keeping them
but tagging them distinctly (e.g. in frontmatter or a manifest) so retrieval can deprioritize them
unless the query is explicitly about version history/upgrades.

Categories 2, 5, and 6 produced **no matches** in the current corpus — either the source material
genuinely doesn't contain that noise (5, 6) or the disclaimed community content the requester
recalled from a prior ingestion pass simply isn't in scope for this official-docs-only crawl (2).
No action is needed for these three categories.
