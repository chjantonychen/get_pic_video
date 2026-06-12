import os, re, threading

def safe_title(title: str) -> str:
    return (title or "untitled").strip().replace('/', '_').replace('\\', '_')[:80]

def save_dir(config: dict) -> str:
    return config.get("save_path") or os.path.join(os.getcwd(), "downloads")

def start_thread(target, args=(), daemon=True):
    threading.Thread(target=target, args=args, daemon=daemon).start()

def m3u8_urls_in_html(html: str) -> list[str]:
    return re.findall(r'https?://[^\s\'\"<>\\]+\.m3u8', html)
