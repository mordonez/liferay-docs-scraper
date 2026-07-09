from types import SimpleNamespace

import pytest

from liferay_docs_scraper import pipeline


def configure_pipeline_dirs(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    monkeypatch.setattr(pipeline, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(pipeline, "REMOVED_DIR", tmp_path / "raw" / "_removed")
    monkeypatch.setattr(pipeline, "NAVIGATION_DIR", tmp_path / "raw" / "_navigation")
    monkeypatch.setattr(pipeline, "FILTERED_DIR", tmp_path / "reports" / "filtered")
    monkeypatch.setattr(pipeline, "REMOVED_LOG", tmp_path / "reports" / "filtered" / "removed_log.jsonl")


def crawl_result(url, markdown="This is substantial content. " * 40, success=True):
    return SimpleNamespace(
        url=url,
        success=success,
        markdown=SimpleNamespace(raw_markdown=markdown),
    )


def test_process_crawl_result_writes_content_page(monkeypatch, tmp_path):
    configure_pipeline_dirs(monkeypatch, tmp_path)
    stats = pipeline.RunStats()

    pipeline.process_crawl_result(
        crawl_result("https://learn.liferay.com/w/dxp/search/search-administration-and-tuning/synonym-sets"),
        stats,
    )

    out_path = tmp_path / "raw" / "search" / "search-administration-and-tuning-synonym-sets.md"
    assert out_path.exists()
    assert stats.outcomes["search"][0].status == "new"
    assert stats.outcomes["search"][0].is_navigation is False
    assert "content_hash:" in out_path.read_text(encoding="utf-8")


def test_process_crawl_result_moves_reclassified_navigation_page(monkeypatch, tmp_path):
    configure_pipeline_dirs(monkeypatch, tmp_path)
    stats = pipeline.RunStats()
    content_path = tmp_path / "raw" / "search" / "index.md"
    content_path.parent.mkdir(parents=True)
    content_path.write_text(
        '---\nurl: "https://learn.liferay.com/w/dxp/search"\ncontent_hash: "old"\n---\nold',
        encoding="utf-8",
    )

    pipeline.process_crawl_result(
        crawl_result("https://learn.liferay.com/w/dxp/search", "[A](a) [B](b) [C](c)"),
        stats,
    )

    assert not content_path.exists()
    assert (tmp_path / "raw" / "_navigation" / "search" / "index.md").exists()
    assert stats.outcomes["search"][0].is_navigation is True


def test_process_crawl_result_records_failed_and_missing_markdown(monkeypatch, tmp_path):
    configure_pipeline_dirs(monkeypatch, tmp_path)
    stats = pipeline.RunStats()

    pipeline.process_crawl_result(crawl_result("https://learn.liferay.com/w/dxp/search/fail", success=False), stats)
    pipeline.process_crawl_result(
        SimpleNamespace(url="https://learn.liferay.com/w/dxp/search/empty", success=True, markdown=None),
        stats,
    )

    assert stats.fetch_failed == [
        "https://learn.liferay.com/w/dxp/search/fail",
        "https://learn.liferay.com/w/dxp/search/empty",
    ]


def test_quarantine_is_skipped_after_fatal_crawl_error(monkeypatch, tmp_path):
    configure_pipeline_dirs(monkeypatch, tmp_path)
    old_path = tmp_path / "raw" / "search" / "old-page.md"
    old_path.parent.mkdir(parents=True)
    old_path.write_text('---\nurl: "https://learn.liferay.com/w/dxp/search/old-page"\n---\n', encoding="utf-8")

    stats = pipeline.RunStats(crawl_errors=["browser crashed"])
    result = pipeline.quarantine_orphans(stats)

    assert old_path.exists()
    assert result.quarantined["search"] == []
    assert "search" in result.skipped_capabilities


def test_quarantine_result_flattens_direct_refresh_urls():
    result = pipeline.QuarantineResult()
    result.direct_refresh_candidates["search"]["a"] = "https://learn.liferay.com/w/dxp/search/a"
    result.direct_refresh_candidates["sites"]["b"] = "https://learn.liferay.com/w/dxp/sites/b"

    assert result.direct_refresh_urls() == [
        "https://learn.liferay.com/w/dxp/search/a",
        "https://learn.liferay.com/w/dxp/sites/b",
    ]


def test_write_filtered_reports_includes_crawl_errors(monkeypatch, tmp_path):
    configure_pipeline_dirs(monkeypatch, tmp_path)
    stats = pipeline.RunStats(crawl_errors=["boom"])

    pipeline.write_filtered_reports(stats)

    summary = (tmp_path / "reports" / "filtered" / "summary.json").read_text(encoding="utf-8")
    assert '"crawl_error_count": 1' in summary
    assert '"boom"' in summary


def test_main_exits_nonzero_on_crawl_error(monkeypatch, tmp_path):
    configure_pipeline_dirs(monkeypatch, tmp_path)

    async def fake_run_crawl(max_depth, max_pages):
        return pipeline.RunStats(crawl_errors=["boom"])

    monkeypatch.setattr(pipeline, "run_crawl", fake_run_crawl)
    monkeypatch.setattr(pipeline, "quarantine_orphans", lambda stats: pipeline.QuarantineResult())
    monkeypatch.setattr(pipeline, "write_filtered_reports", lambda stats: None)
    monkeypatch.setattr(pipeline, "print_summary", lambda stats, quarantine_result: None)
    monkeypatch.setattr("sys.argv", ["liferay-docs-scraper"])

    with pytest.raises(SystemExit) as exc_info:
        pipeline.main()

    assert exc_info.value.code == 1
