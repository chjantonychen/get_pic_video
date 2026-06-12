import json, os

DEFAULT_CONFIG = {
    "download_threads": 10,
    "save_path": "",
    "speed_limit": 0,
    "resume_enabled": True,
    "delay_min": 1,
    "delay_max": 3,
    "random_ua": True,
    "proxy_list": [],
    "ffmpeg_path": "ffmpeg",
    "page_timeout": 30,
    "js_retries": 3,
    "rules": []
}

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return dict(DEFAULT_CONFIG)

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
