import os, subprocess, tempfile, requests, shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

class M3U8Handler:
    def __init__(self, ffmpeg_path: str = "ffmpeg", log_callback=None):
        self._ffmpeg = ffmpeg_path
        self._log = log_callback or (lambda msg: None)

    def _log_msg(self, msg):
        try: self._log(msg)
        except: pass

    def download_and_convert(self, m3u8_url: str, output_path: str) -> str:
        self._log_msg(f"M3U8: 下载索引 {m3u8_url[:60]}")
        base = os.path.dirname(m3u8_url)
        resp = requests.get(m3u8_url, timeout=30)
        resp.raise_for_status()
        content = resp.text
        ts_urls = self._parse_ts_urls(content, base)
        self._log_msg(f"M3U8: 解析到 {len(ts_urls)} 个TS分段")
        tmpdir = tempfile.mkdtemp(prefix="getiv_")
        try:
            ts_files = self._download_segments(ts_urls, tmpdir)
            mp4_path = output_path
            if not mp4_path.endswith(".mp4"):
                mp4_path += ".mp4"
            self._concat_to_mp4(ts_files, mp4_path)
            self._log_msg(f"M3U8: 完成 -> {mp4_path}")
        finally:
            self._cleanup(tmpdir)
            self._log_msg("M3U8: 临时文件已清理")
        return mp4_path

    def _parse_ts_urls(self, m3u8_content: str, base_url: str) -> list[str]:
        urls = []
        for line in m3u8_content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                if line.startswith("http"):
                    urls.append(line)
                else:
                    urls.append(base_url.rstrip("/") + "/" + line.lstrip("/"))
        return urls

    def _download_segments(self, ts_urls: list[str], tmpdir: str) -> list[str]:
        files = []
        total = len(ts_urls)
        completed = 0
        self._log_msg(f"M3U8: 开始下载 {total} 个TS分段")
        with ThreadPoolExecutor(max_workers=10) as pool:
            def dl(i, url):
                r = requests.get(url, timeout=30)
                r.raise_for_status()
                path = os.path.join(tmpdir, f"seg_{i:04d}.ts")
                with open(path, "wb") as f:
                    f.write(r.content)
                return path
            futures = {pool.submit(dl, i, u): i for i, u in enumerate(ts_urls)}
            for f in as_completed(futures):
                files.append(f.result())
                completed += 1
        files.sort()
        self._log_msg(f"M3U8: TS分段下载完成 ({completed}/{total})")
        return files

    def _concat_to_mp4(self, ts_files: list[str], output: str):
        self._log_msg(f"M3U8: ffmpeg合并 {len(ts_files)} 个分段 -> MP4")
        list_path = os.path.join(os.path.dirname(ts_files[0]), "concat.txt")
        with open(list_path, "w") as f:
            for tf in ts_files:
                f.write(f"file '{tf}'\n")
        subprocess.run([
            self._ffmpeg, "-f", "concat", "-safe", "0",
            "-i", list_path, "-c", "copy", "-y", output
        ], check=True, capture_output=True, timeout=300)
        size = os.path.getsize(output) if os.path.exists(output) else 0
        self._log_msg(f"M3U8: ffmpeg完成 ({size/1024/1024:.1f}MB)")

    def _cleanup(self, tmpdir: str):
        shutil.rmtree(tmpdir, ignore_errors=True)
