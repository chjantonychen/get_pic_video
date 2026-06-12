import json, urllib.parse
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
  var lastEl = null;
  function onHover(e) {
    if (lastEl) { lastEl.style.outline = ""; lastEl.style.background = ""; }
    e.target.style.outline = "3px solid #2196F3";
    e.target.style.outlineOffset = "2px";
    e.target.style.background = "rgba(33,150,243,0.15)";
    lastEl = e.target;
  }
  function onOut(e) { e.target.style.outline = ""; e.target.style.background = ""; }
  function onClick(e) {
    e.preventDefault(); e.stopPropagation();
    document.title = "__pick:" + encodeURIComponent(getSelector(e.target));
  }
  document.addEventListener("mouseover", onHover, true);
  document.addEventListener("mouseout", onOut, true);
  document.addEventListener("click", onClick, true);
  window.__disablePicker = function() {
    document.removeEventListener("mouseover", onHover, true);
    document.removeEventListener("mouseout", onOut, true);
    document.removeEventListener("click", onClick, true);
    document.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; el.style.background = ""; });
  };
  window.__validateSelector = function(css) {
    document.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; el.style.background = ""; });
    var els = document.querySelectorAll(css);
    if (els.length === 0) { document.title = "验证失败: 未找到匹配元素"; return 0; }
    els.forEach(function(el) { el.style.outline = "3px solid #4CAF50"; el.style.outlineOffset = "2px"; });
    document.title = "__validate:" + els.length;
    return els.length;
  };
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
        self._page.runJavaScript("""
document.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; el.style.background = ""; });
""")
