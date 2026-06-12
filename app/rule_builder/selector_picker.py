import os, json, urllib.parse
from PyQt5.QtCore import QObject, pyqtSignal

class SelectorPicker(QObject):
    elementPicked = pyqtSignal(str)

    def __init__(self, page):
        super().__init__()
        self._page = page
        self._enabled = False
        self._last_title = ""
        base = os.path.join(os.path.dirname(__file__), "..", "..", "resources", "js")
        with open(os.path.join(base, "selector_picker.js")) as f:
            self._js_code = f.read()
        page.titleChanged.connect(self._on_title_changed)

    def enable(self):
        self._enabled = True
        self._page.runJavaScript(self._js_code)
        self._page.runJavaScript("__enablePicker();")

    def disable(self):
        self._enabled = False
        self._page.runJavaScript("__disablePicker();")

    def reenable(self):
        if self._enabled:
            self.enable()

    def _on_title_changed(self, title):
        if title.startswith("__pick:"):
            selector = urllib.parse.unquote(title[7:])
            self.elementPicked.emit(selector)

    def validate_selector(self, css: str, callback):
        safe_css = json.dumps(css)
        self._page.runJavaScript(f"__validateSelector({safe_css})", callback)

    def clear_highlights(self):
        self._page.runJavaScript("""document.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; });""")
