import os, json, urllib.parse
from PyQt5.QtCore import QObject, pyqtSignal

PICKER_JS = """
(function() {
  function getSelector(el) {
    var p = [];
    while (el && el.nodeType === 1) {
      var s = el.tagName.toLowerCase();
      if (el.id) { p.unshift("#" + el.id); break; }
      if (el.className && typeof el.className === "string" && el.className.trim()) {
        s += "." + el.className.trim().split(/\\s+/)[0];
      }
      var parent = el.parentElement;
      if (parent) { s += ":nth-child(" + (Array.from(parent.children).indexOf(el) + 1) + ")"; }
      p.unshift(s);
      el = parent;
    }
    return p.join(" > ");
  }
  var style = document.createElement("style");
  style.id = "getiv-picker-style";
  style.textContent = "*:hover { outline: 3px solid #2196F3 !important; outline-offset: 2px !important; }";
  document.head.appendChild(style);
  window.__disablePicker = function() {
    var s = document.getElementById("getiv-picker-style");
    if (s) s.remove();
  };
  window.__validateSelector = function(css) {
    document.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; });
    var els = document.querySelectorAll(css);
    els.forEach(function(el) { el.style.outline = "3px solid #4CAF50"; el.style.outlineOffset = "2px"; });
    return els.length;
  };
  document.addEventListener("click", function __pick(e) {
    e.preventDefault(); e.stopPropagation();
    document.title = "__pick:" + encodeURIComponent(getSelector(e.target));
    document.removeEventListener("click", __pick, true);
  }, true);
})();
"""

class SelectorPicker(QObject):
    elementPicked = pyqtSignal(str)

    def __init__(self, page):
        super().__init__()
        self._page = page
        self._enabled = False
        page.titleChanged.connect(self._on_title_changed)

    def enable(self):
        self._enabled = True
        self._page.runJavaScript(PICKER_JS)

    def disable(self):
        self._enabled = False
        self._page.runJavaScript("__disablePicker();")

    def reenable(self):
        if self._enabled:
            self._page.runJavaScript(PICKER_JS)

    def _on_title_changed(self, title):
        if title.startswith("__pick:"):
            selector = urllib.parse.unquote(title[7:])
            self.elementPicked.emit(selector)

    def validate_selector(self, css: str, callback):
        safe_css = json.dumps(css)
        self._page.runJavaScript(f"__validateSelector({safe_css})", callback)

    def clear_highlights(self):
        self._page.runJavaScript("""document.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; });""")
