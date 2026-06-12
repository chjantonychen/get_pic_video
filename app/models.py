from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SelectorRule:
    css: str
    attribute: str
    wait_selector: str = ""
    lazy_scroll: bool = False

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
