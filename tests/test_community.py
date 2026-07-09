import asyncio
from types import SimpleNamespace

import pytest

from liferay_docs_scraper import community


def configure_community_dirs(monkeypatch, tmp_path):
    monkeypatch.setattr(community, "ROOT", tmp_path)
    monkeypatch.setattr(community, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(community, "FILTERED_DIR", tmp_path / "reports" / "filtered")


def test_safe_slug_decodes_and_caps_long_percent_encoded_url():
    url = "https://learn.liferay.com/kb-article/" + ("%C3%A1" * 200)

    slug = community.safe_slug(url)

    assert len(slug.encode("utf-8")) <= 150
    assert "/" not in slug


def test_build_frontmatter_quotes_tag_values():
    frontmatter = community.build_frontmatter(
        'https://learn.liferay.com/kb-article/page?x="quoted"',
        "community-howto",
        "search",
        {"Capability": 'Search "Advanced"', "Feature": "Indexing: Blueprints"},
        "body",
    )

    assert 'url: "https://learn.liferay.com/kb-article/page?x=\\"quoted\\""' in frontmatter
    assert 'capability_tag_raw: "Search \\"Advanced\\""' in frontmatter
    assert 'feature: "Indexing: Blueprints"' in frontmatter


def test_extract_article_links_keeps_absolute_kb_article_urls_only():
    html = """
    <a href="https://learn.liferay.com/kb-article/how-to-fix-search"></a>
    <a href="/kb-article/relative"></a>
    <a href="https://example.com/kb-article/nope"></a>
    """

    assert community.extract_article_links(html) == {
        "https://learn.liferay.com/kb-article/how-to-fix-search"
    }


def test_discover_article_urls_raises_when_listing_fetch_fails():
    class FakeCrawler:
        async def arun(self, url, config):
            return SimpleNamespace(success=False)

    with pytest.raises(RuntimeError, match="search listing page .* failed"):
        asyncio.run(community.discover_article_urls(FakeCrawler(), "33317328"))


def test_discover_article_urls_stops_when_no_new_links():
    html = """
    <html><body>
      <a href="https://learn.liferay.com/kb-article/how-to-fix-search"></a>
      <a href="https://learn.liferay.com/kb-article/how-to-fix-search"></a>
    </body></html>
    """

    class FakeCrawler:
        async def arun(self, url, config):
            return SimpleNamespace(success=True, html=html)

    assert asyncio.run(community.discover_article_urls(FakeCrawler(), "33317328")) == [
        "https://learn.liferay.com/kb-article/how-to-fix-search"
    ]


def test_discover_article_urls_honors_limit_without_paging_further():
    html = """
    <html><body>
      <a href="https://learn.liferay.com/kb-article/a"></a>
      <a href="https://learn.liferay.com/kb-article/b"></a>
    </body></html>
    """

    class FakeCrawler:
        def __init__(self):
            self.calls = 0

        async def arun(self, url, config):
            self.calls += 1
            return SimpleNamespace(success=True, html=html)

    crawler = FakeCrawler()

    assert asyncio.run(community.discover_article_urls(crawler, "33317328", limit=1)) == [
        "https://learn.liferay.com/kb-article/a"
    ]
    assert crawler.calls == 1


def test_run_resource_type_records_stream_crash(monkeypatch, tmp_path):
    configure_community_dirs(monkeypatch, tmp_path)

    class FakeCrawler:
        async def arun_many(self, urls, config):
            raise RuntimeError("browser crashed")

    async def fake_discover(crawler, resource_type_id, limit=None):
        return ["https://learn.liferay.com/kb-article/a"]

    monkeypatch.setattr(community, "discover_article_urls", fake_discover)

    stats = asyncio.run(community.run_resource_type(FakeCrawler(), "howto", "33317328", "community-howto"))

    assert stats.crawl_errors == ["browser crashed"]
    assert stats.discovered_total == 1


def test_main_exits_nonzero_when_run_all_reports_failure(monkeypatch):
    async def fake_run_all(resource_type_filter, limit):
        return True

    monkeypatch.setattr(community, "run_all", fake_run_all)
    monkeypatch.setattr("sys.argv", ["liferay-docs-scraper-community"])

    with pytest.raises(SystemExit) as exc_info:
        community.main()

    assert exc_info.value.code == 1


def test_main_rejects_non_positive_limit(monkeypatch):
    monkeypatch.setattr("sys.argv", ["liferay-docs-scraper-community", "--limit", "0"])

    with pytest.raises(SystemExit) as exc_info:
        community.main()

    assert exc_info.value.code == 2
