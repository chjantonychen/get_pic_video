import json, urllib.parse
from PyQt5.QtCore import QObject, pyqtSignal

GET_SELECTOR_JS = """
function getivGetSelector(el) {
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
"""

ENABLE_PICKER_JS = """
window.__lastPicked = null;
window.__onHover = function(e) {
  if (window.__lastEl) { window.__lastEl.style.outline = ""; window.__lastEl.style.background = ""; }
  e.target.style.outline = "3px solid #2196F3";
  e.target.style.outlineOffset = "2px";
  e.target.style.background = "rgba(33,150,243,0.15)";
  window.__lastEl = e.target;
};
window.__onOut = function(e) { e.target.style.outline = ""; e.target.style.background = ""; };
window.__onPick = function(e) {
  e.preventDefault();
  e.stopPropagation();
  document.title = "__pick:" + encodeURIComponent(getivGetSelector(e.target));
};
document.addEventListener("mouseover", window.__onHover, true);
document.addEventListener("mouseout", window.__onOut, true);
document.addEventListener("click", window.__onPick, true);
window.__getivPickerActive = true;
"""

DISABLE_PICKER_JS = """
if (window.__getivPickerActive) {
  document.removeEventListener("mouseover", window.__onHover, true);
  document.removeEventListener("mouseout", window.__onOut, true);
  document.removeEventListener("click", window.__onPick, true);
  document.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; el.style.background = ""; });
  window.__getivPickerActive = false;
}
"""

VALIDATE_JS = """
(function(css) {
  document.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; el.style.background = ""; });
  var els = document.querySelectorAll(css);
  els.forEach(function(el) { el.style.outline = "3px solid #4CAF50"; el.style.outlineOffset = "2px"; });
  return els.length;
})
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
        self._page.runJavaScript(GET_SELECTOR_JS)
        self._page.runJavaScript(ENABLE_PICKER_JS)

    def disable(self):
        self._enabled = False
        self._page.runJavaScript(DISABLE_PICKER_JS)

    def reenable(self):
        if self._enabled:
            self._page.runJavaScript(GET_SELECTOR_JS)
            self._page.runJavaScript(ENABLE_PICKER_JS)

    def _on_title_changed(self, title):
        if title.startswith("__pick:"):
            selector = urllib.parse.unquote(title[7:])
            self.elementPicked.emit(selector)

    def validate_selector(self, css: str, callback):
        safe_css = json.dumps(css)
        self._page.runJavaScript(f"({VALIDATE_JS})({safe_css})", callback)

    def clear_highlights(self):
        self._page.runJavaScript("""document.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; el.style.background = ""; });""")
