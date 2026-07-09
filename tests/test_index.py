import json

from liferay_docs_scraper import index


def test_build_search_index_includes_official_and_community_docs(tmp_path):
    raw_dir = tmp_path / "raw"
    reports_dir = tmp_path / "reports" / "filtered"
    official = raw_dir / "search" / "synonym-sets.md"
    community = raw_dir / "community-howto" / "_uncategorized" / "fix.md"
    official.parent.mkdir(parents=True)
    community.parent.mkdir(parents=True)
    official.write_text(
        '---\nurl: "https://learn.liferay.com/w/dxp/search/synonym-sets"\n'
        'capability: search\nfetched_at: "2026-07-09T10:00:00Z"\n---\n'
        "# Synonym Sets\n\n## Configure synonyms\n",
        encoding="utf-8",
    )
    community.write_text(
        '---\nurl: "https://learn.liferay.com/kb-article/fix"\n'
        'source_type: community-howto\ncapability: uncategorized\n---\n'
        "# Fix Search\n\nBody\n",
        encoding="utf-8",
    )

    count = index.build_search_index(raw_dir, reports_dir)

    assert count == 2
    entries = [
        json.loads(line)
        for line in (reports_dir / "search_index.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert entries[0]["source_type"] == "official"
    assert entries[0]["title"] == "Synonym Sets"
    assert entries[0]["path"] == "raw/search/synonym-sets.md"
    assert entries[1]["source_type"] == "community-howto"


def test_detect_anomalies_reports_short_error_and_size_change(tmp_path):
    previous = index.ContentSnapshot(body_chars=1000, body_words=100)

    anomalies = index.detect_anomalies(
        path=tmp_path / "raw" / "search" / "page.md",
        url="https://learn.liferay.com/w/dxp/search/page",
        source_type="official",
        capability="search",
        body="An unexpected error occurred.",
        previous=previous,
    )

    kinds = {item["kind"] for item in anomalies}
    assert {"short_body", "error_marker", "missing_title", "body_shrank"} <= kinds
