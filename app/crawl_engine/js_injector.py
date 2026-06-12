import json
import os

class JSInjector:
    def __init__(self):
        self._scripts = {}
        base = os.path.join(os.path.dirname(__file__), "..", "..", "resources", "js")
        for name in ["extract_links", "extract_media", "extract_pages"]:
            with open(os.path.join(base, f"{name}.js")) as f:
                self._scripts[name] = f.read()

    def get_script(self, name: str) -> str:
        return self._scripts.get(name, "")

    def build_extract_links_js(self, selector: str, attribute: str) -> str:
        return f"{self._scripts['extract_links']}\nextractLinks({json.dumps(selector)}, {json.dumps(attribute)});"

    def build_extract_media_js(self, css: str, attr: str) -> str:
        return f"{self._scripts['extract_media']}\nextractMedia({json.dumps(css)}, {json.dumps(attr)});"
