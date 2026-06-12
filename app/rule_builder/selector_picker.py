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
  window.__disablePicker = function() {
    document.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; });
  };
  window.__validateSelector = function(css) {
    document.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; });
    var els = document.querySelectorAll(css);
    els.forEach(function(el) { el.style.outline = "3px solid #4CAF50"; el.style.outlineOffset = "2px"; });
    return els.length;
  };
  var hov = function(e) { e.target.style.outline = "3px solid #2196F3"; e.target.style.outlineOffset = "2px"; };
  var unhov = function(e) { e.target.style.outline = ""; };
  var pick = function(e) {
    e.preventDefault(); e.stopPropagation();
    document.title = "__pick:" + encodeURIComponent(getSelector(e.target));
    document.removeEventListener("mouseover", hov, true);
    document.removeEventListener("mouseout", unhov, true);
    document.removeEventListener("click", pick, true);
  };
  document.addEventListener("mouseover", hov, true);
  document.addEventListener("mouseout", unhov, true);
  document.addEventListener("click", pick, true);
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
        self._page.runJavaScript("""document.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; });""")
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
