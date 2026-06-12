import os, time, random, threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtCore import QObject, pyqtSignal
from app.models import DownloadProgress

class Downloader(QObject):
    progressUpdated = pyqtSignal(DownloadProgress)
    downloadComplete = pyqtSignal()
    downloadError = pyqtSignal(str)

    def __init__(self, config, m3u8_handler=None):
        super().__init__()
        self._config = config
        self._m3u8_handler = m3u8_handler
        self._pool = None
        self._pause_event = threading.Event()
        self._cancel_event = threading.Event()
        self._pause_event.set()
        self._running = False

    @property
    def is_running(self):
        return self._running

    @property
    def is_paused(self):
        return not self._pause_event.is_set()

    def start(self, media_urls: list, save_dir: str):
        self._cancel_event.clear()
        self._pause_event.set()
        self._running = True
        threads = self._config.get("download_threads", 10)
        self._pool = ThreadPoolExecutor(max_workers=threads)
        total = len(media_urls)
        completed = 0
        failed = 0
        futures = []
        try:
            for item in media_urls:
                if self._cancel_event.is_set():
                    break
                url = item["url"] if isinstance(item, dict) else item
                fname = self._safe_filename(os.path.basename(url.split("?")[0]))
                fpath = os.path.join(save_dir, fname)
                future = self._pool.submit(self._download_file, url, fpath)
                futures.append(future)
            for f in as_completed(futures):
                if self._cancel_event.is_set():
                    break
                self._pause_event.wait()
                try:
                    f.result()
                    completed += 1
                except Exception as e:
                    failed += 1
                    self.downloadError.emit(str(e))
                self.progressUpdated.emit(DownloadProgress(
                    total, completed, failed, "", 0, 0, 0))
            self.downloadComplete.emit()
        finally:
            self._running = False
            if self._pool:
                self._pool.shutdown(wait=False)

    def _download_file(self, url: str, path: str):
        if self._m3u8_handler and '.m3u8' in url.lower():
            mp4_path = path.rsplit('.', 1)[0] + '.mp4' if not path.endswith('.mp4') else path
            self._m3u8_handler.download_and_convert(url, mp4_path)
            if os.path.exists(mp4_path) and path != mp4_path and os.path.exists(path):
                os.remove(path)
            return
        self._http_download(url, path)

    def _http_download(self, url: str, path: str):
        if self._cancel_event.is_set():
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        delay = self._config.get("delay_min", 1)
        delay_max = self._config.get("delay_max", 3)
        time.sleep(random.uniform(delay, delay_max))
        headers = {"User-Agent": self._random_ua()} if self._config.get("random_ua") else {}
        proxies = None
        proxy_list = self._config.get("proxy_list", [])
        if proxy_list:
            proxy = random.choice(proxy_list)
            proxies = {"http": proxy, "https": proxy}
        timeout = self._config.get("page_timeout", 30)
        resume = self._config.get("resume_enabled", True)
        resp = requests.get(url, headers=headers, stream=True, timeout=timeout, proxies=proxies)
        if resume and os.path.exists(path) and resp.status_code == 206:
            mode = "ab"
        else:
            resp.raise_for_status()
            mode = "wb"
        with open(path, mode) as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    def _safe_filename(self, name: str) -> str:
        illegal = '<>:"/\\|?*'
        for c in illegal:
            name = name.replace(c, "_")
        return name or "download"

    def _random_ua(self) -> str:
        uas = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
        ]
        return random.choice(uas)

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def cancel(self):
        self._cancel_event.set()
        if self._pool:
            self._pool.shutdown(wait=False)
