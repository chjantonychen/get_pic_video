import json

from PyQt5.QtCore import QObject, pyqtSignal
from app.crawl_engine.js_injector import JSInjector
from app.models import SiteRule

class Crawler(QObject):
    paginationFound = pyqtSignal(list)
    linksFound = pyqtSignal(list)
    mediaFound = pyqtSignal(list)
    pageCount = pyqtSignal(int)
    crawlError = pyqtSignal(str)

    def __init__(self, page):
        super().__init__()
        self._page = page
        self._js = JSInjector()

    def extract_detail_links(self, rule: SiteRule):
        sr = rule.page_list
        if sr.url_pattern:
            js = self._js.build_extract_links_by_pattern_js(sr.url_pattern)
        else:
            js = self._js.build_extract_links_js(sr.css, sr.attribute)
        self._page.runJavaScript(js, self.linksFound.emit)

    def extract_pagination(self, rule: SiteRule):
        if not rule.pagination:
            return
        sr = rule.pagination
        if sr.url_pattern:
            js = self._js.build_extract_links_by_pattern_js(sr.url_pattern)
        else:
            js = self._js.build_extract_links_js(sr.css, sr.attribute)
        self._page.runJavaScript(js, self.paginationFound.emit)

    def extract_media(self, rule: SiteRule, media_type: str = "image"):
        sr = rule.detail_images if media_type == "image" else rule.detail_videos
        if not sr:
            return
        js = self._js.build_extract_media_js(sr.css, sr.attribute)
        self._page.runJavaScript(js, self.mediaFound.emit)

    def extract_total_pages(self, rule: SiteRule):
        if not rule.pagination:
            return
        if rule.pagination.url_pattern:
            return
        js = self._js.get_script("extract_pages")
        js += f"\nextractTotalPages({json.dumps(rule.pagination.css)});"
        self._page.runJavaScript(js, self.pageCount.emit)
