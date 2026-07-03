from liferay_docs_scraper.classify_pages import analyze_body, classify


def test_short_link_heavy_page_is_navigation():
    words, ratio = analyze_body("[Search](search.md) [Indexing](indexing.md)")

    assert classify(words, ratio) == "index"


def test_substantial_text_page_is_content():
    body = " ".join(["This page explains indexing configuration in detail."] * 40)
    words, ratio = analyze_body(body)

    assert classify(words, ratio) == "content"
