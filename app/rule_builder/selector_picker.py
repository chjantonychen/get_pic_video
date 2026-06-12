import json, urllib.parse
from PyQt5.QtCore import QObject, pyqtSignal

# Attribute candidates to auto-detect from elements
ATTR_CANDIDATES = ["src", "href", "data-src", "data-original", "data-lazy", "data-srcset", "poster"]

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
function getivElementAttrs(el) {
  var candidates = ["src","href","data-src","data-original","data-lazy","data-srcset","poster"];
  var found = [];
  for (var i = 0; i < candidates.length; i++) {
    var v = el.getAttribute(candidates[i]);
    if (v) found.push(candidates[i]);
  }
  return found.join(",");
}
"""

ENABLE_PICKER_JS = """
(function() {
  function inject(doc) {
    if (!doc || doc.__getivActive) return;
    doc.__getivActive = true;
    doc.__lastEl = null;
    doc.__onHover = function(e) {
      if (doc.__lastEl) { doc.__lastEl.style.outline = ""; doc.__lastEl.style.background = ""; }
      e.target.style.outline = "3px solid #2196F3";
      e.target.style.outlineOffset = "2px";
      e.target.style.background = "rgba(33,150,243,0.15)";
      doc.__lastEl = e.target;
    };
    doc.__onOut = function(e) { e.target.style.outline = ""; e.target.style.background = ""; };
    doc.__onPick = function(e) {
      e.preventDefault(); e.stopPropagation();
      var sel = getivGetSelector(e.target);
      var attrs = getivElementAttrs(e.target);
      document.title = "__pick:" + encodeURIComponent(sel + "|" + attrs);
    };
    doc.addEventListener("mouseover", doc.__onHover, true);
    doc.addEventListener("mouseout", doc.__onOut, true);
    doc.addEventListener("click", doc.__onPick, true);
    Array.from(doc.querySelectorAll("iframe")).forEach(function(f) {
      try { if (f.contentDocument) inject(f.contentDocument); } catch(e) {}
    });
  }
  inject(document);
  // Retry for dynamically loaded iframe content
  var retries = [2, 4, 8];
  retries.forEach(function(s) { setTimeout(function() { inject(document); }, s * 1000); });
})();
"""

DISABLE_PICKER_JS = """
(function() {
  function disable(doc) {
    if (!doc.__getivActive) return;
    doc.__getivActive = false;
    doc.removeEventListener("mouseover", doc.__onHover, true);
    doc.removeEventListener("mouseout", doc.__onOut, true);
    doc.removeEventListener("click", doc.__onPick, true);
    doc.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; el.style.background = ""; });
    Array.from(doc.querySelectorAll("iframe")).forEach(function(f) {
      try { if (f.contentDocument) disable(f.contentDocument); } catch(e) {}
    });
  }
  disable(document);
})();
"""

VALIDATE_JS = """
(function(win, css) {
  function count(d) {
    d.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; el.style.background = ""; });
    var n = d.querySelectorAll(css).length;
    d.querySelectorAll(css).forEach(function(el) { el.style.outline = "3px solid #4CAF50"; el.style.outlineOffset = "2px"; });
    Array.from(d.querySelectorAll("iframe")).forEach(function(f) {
      try { if (f.contentDocument) n += count(f.contentDocument); } catch(e) {}
    });
    return n;
  }
  return count(win.document);
})
"""

class SelectorPicker(QObject):
    elementPicked = pyqtSignal(str)

    def __init__(self, page):
        super().__init__()
        self._page = page
        self._enabled = False
        page.titleChanged.connect(self._on_title_changed)
        page.loadFinished.connect(self._on_page_loaded)

    def _on_page_loaded(self, ok):
        if self._enabled:
            self._page.runJavaScript(GET_SELECTOR_JS)
            self._page.runJavaScript(ENABLE_PICKER_JS)

    def enable(self):
        self._enabled = True
        self._page.runJavaScript(GET_SELECTOR_JS)
        self._page.runJavaScript(ENABLE_PICKER_JS)

    def disable(self):
        self._enabled = False
        self._page.runJavaScript(DISABLE_PICKER_JS)

    def _on_title_changed(self, title):
        if title.startswith("__pick:"):
            raw = urllib.parse.unquote(title[7:])
            parts = raw.split("|", 1)
            selector = parts[0]
            attrs = parts[1].split(",") if len(parts) > 1 and parts[1] else []
            self.elementPicked.emit(json.dumps({"selector": selector, "attrs": attrs}))

    def validate_selector(self, css: str, callback):
        safe_css = json.dumps(css)
        self._page.runJavaScript(f"({VALIDATE_JS})(window, {safe_css})", callback)

    def clear_highlights(self):
        self._page.runJavaScript("""
(function() {
  function clear(doc) {
    doc.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; el.style.background = ""; });
    Array.from(doc.querySelectorAll("iframe")).forEach(function(f) {
      try { if (f.contentDocument) clear(f.contentDocument); } catch(e) {}
    });
  }
  clear(document);
})();
""")
