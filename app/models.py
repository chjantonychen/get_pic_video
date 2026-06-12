from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SelectorRule:
    css: str = ""
    attribute: str = "href"
    url_pattern: str = ""
    wait_selector: str = ""
    lazy_scroll: bool = False

    @staticmethod
    def from_dict(d: dict) -> Optional['SelectorRule']:
        if not d:
            return None
        return SelectorRule(
            css=d.get("css", ""),
            attribute=d.get("attribute", "href"),
            url_pattern=d.get("url_pattern", ""),
            wait_selector=d.get("wait_selector", ""),
            lazy_scroll=d.get("lazy_scroll", False),
        )

@dataclass
class AntiCrawlConfig:
    delay_range: tuple = (1, 3)
    use_proxy: bool = False
    proxy_list: Optional[list[str]] = None
    random_user_agent: bool = True

@dataclass
class SiteRule:
    name: str
    url_pattern: str
    page_list: SelectorRule
    detail_images: SelectorRule
    pagination: Optional[SelectorRule] = None
    detail_videos: Optional[SelectorRule] = None
    next_button: Optional[SelectorRule] = None
    anti_crawl: AntiCrawlConfig = field(default_factory=AntiCrawlConfig)

    @staticmethod
    def from_config(cfg: dict) -> Optional['SiteRule']:
        if not cfg:
            return None
        return SiteRule(
            name=cfg["name"],
            url_pattern=cfg.get("url_pattern", ""),
            page_list=SelectorRule.from_dict(cfg.get("page_list")),
            detail_images=SelectorRule.from_dict(cfg.get("detail_images")),
            pagination=SelectorRule.from_dict(cfg.get("pagination")),
            detail_videos=SelectorRule.from_dict(cfg.get("detail_videos")),
            next_button=SelectorRule.from_dict(cfg.get("next_button")),
        )

@dataclass
class CrawlResult:
    source_url: str
    page_title: str
    detail_urls: list[str]
    media_urls: list[dict]

@dataclass
class DownloadProgress:
    total_files: int
    completed: int
    failed: int
    current_file: str
    bytes_downloaded: int
    total_bytes: int
    speed: float
