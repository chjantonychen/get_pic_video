import os, time, random
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtCore import QObject, pyqtSignal
from app.models import DownloadProgress

class Downloader(QObject):
    progressUpdated = pyqtSignal(DownloadProgress)
    downloadComplete = pyqtSignal()
    downloadError = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self._config = config
        self._pool = None
        self._paused = False
        self._cancelled = False

    def start(self, media_urls: list, save_dir: str):
        self._cancelled = False
        self._paused = False
        threads = self._config.get("download_threads", 10)
        self._pool = ThreadPoolExecutor(max_workers=threads)
        total = len(media_urls)
        completed = 0
        failed = 0
        futures = []
        for item in media_urls:
            if self._cancelled:
                break
            url = item["url"] if isinstance(item, dict) else item
            fname = self._safe_filename(os.path.basename(url.split("?")[0]))
            fpath = os.path.join(save_dir, fname)
            future = self._pool.submit(self._download_file, url, fpath)
            futures.append(future)
        for f in as_completed(futures):
            if self._cancelled:
                break
            while self._paused and not self._cancelled:
                time.sleep(0.5)
            try:
                f.result()
                completed += 1
            except Exception as e:
                failed += 1
                self.downloadError.emit(str(e))
            self.progressUpdated.emit(DownloadProgress(
                total, completed, failed, "", 0, 0, 0))
        self.downloadComplete.emit()
        if self._pool:
            self._pool.shutdown(wait=False)

    def _download_file(self, url: str, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        delay = self._config.get("delay_min", 1)
        delay_max = self._config.get("delay_max", 3)
        time.sleep(random.uniform(delay, delay_max))
        headers = {"User-Agent": self._random_ua()} if self._config.get("random_ua") else {}
        resume = self._config.get("resume_enabled", True)
        if resume and os.path.exists(path):
            existing = os.path.getsize(path)
            headers["Range"] = f"bytes={existing}-"
            resp = requests.get(url, headers=headers, stream=True, timeout=30)
            if resp.status_code == 206:
                mode = "ab"
            else:
                mode = "wb"
        else:
            resp = requests.get(url, headers=headers, stream=True, timeout=30)
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
        self._paused = True

    def resume(self):
        self._paused = False

    def cancel(self):
        self._cancelled = True
