import pytest
from app.crawl_engine.js_injector import JSInjector

def test_build_extract_links_js():
    inj = JSInjector()
    js = inj.build_extract_links_js("a.link", "href")
    assert "extractLinks" in js
    assert "a.link" in js
    assert "href" in js

def test_build_extract_media_js():
    inj = JSInjector()
    js = inj.build_extract_media_js("img.lazy", "data-src")
    assert "extractMedia" in js
    assert "img.lazy" in js
