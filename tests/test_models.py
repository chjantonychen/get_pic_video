import pytest
from app.models import SiteRule, SelectorRule, AntiCrawlConfig, CrawlResult, DownloadProgress

def test_site_rule_defaults():
    r = SiteRule(name="test", url_pattern="example.com", page_list=SelectorRule("a.link", "href"),
                 detail_images=SelectorRule("img", "src"))
    assert r.name == "test"
    assert r.pagination is None
    assert r.detail_videos is None
    assert r.anti_crawl.delay_range == (1, 3)

def test_crawl_result():
    r = CrawlResult(source_url="http://example.com", page_title="Test", detail_urls=["/a"], media_urls=[{"url": "x.jpg", "type": "image"}])
    assert len(r.media_urls) == 1
