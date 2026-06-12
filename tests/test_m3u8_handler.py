import pytest
from app.download_engine.m3u8_handler import M3U8Handler

def test_parse_ts_urls_relative():
    h = M3U8Handler()
    content = "#EXTM3U\n#EXTINF:3,\nseg1.ts\nseg2.ts\n"
    urls = h._parse_ts_urls(content, "http://example.com/video/")
    assert urls == ["http://example.com/video/seg1.ts", "http://example.com/video/seg2.ts"]

def test_parse_ts_urls_absolute():
    h = M3U8Handler()
    content = "#EXTM3U\nhttp://cdn.com/seg1.ts\nhttp://cdn.com/seg2.ts\n"
    urls = h._parse_ts_urls(content, "http://example.com/")
    assert urls == ["http://cdn.com/seg1.ts", "http://cdn.com/seg2.ts"]
