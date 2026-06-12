(function() {
  function getElementSelector(el) {
    var path = [];
    while (el && el.nodeType === 1) {
      var sel = el.tagName.toLowerCase();
      if (el.id) { path.unshift("#" + el.id); break; }
      if (el.className && typeof el.className === "string" && el.className.trim()) {
        var cls = el.className.trim().split(/\s+/).filter(function(c) { return c; })[0];
        sel += "." + cls;
      }
      var parent = el.parentElement;
      if (parent) {
        var idx = Array.from(parent.children).indexOf(el) + 1;
        sel += ":nth-child(" + idx + ")";
      }
      path.unshift(sel);
      el = parent;
    }
    return path.join(" > ");
  }

  window.__enablePicker = function() {
    document.addEventListener("mouseover", function __hover(e) {
      e.target.style.outline = "3px solid #2196F3";
      e.target.style.outlineOffset = "2px";
    }, true);
    document.addEventListener("mouseout", function __unhover(e) {
      e.target.style.outline = "";
    }, true);
    document.addEventListener("click", function __pick(e) {
      e.preventDefault();
      e.stopPropagation();
      var sel = getElementSelector(e.target);
      e.target.style.cssText += "outline: 3px solid #4CAF50 !important; outline-offset: 2px;";
      document.removeEventListener("mouseover", __hover, true);
      document.removeEventListener("mouseout", __unhover, true);
      document.removeEventListener("click", __pick, true);
      if (window.__pickerBridge) {
        __pickerBridge.onElementPicked(sel);
      }
    }, true);
  };

  window.__disablePicker = function() {
    document.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; });
  };

  window.__validateSelector = function(css) {
    document.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; });
    var els = document.querySelectorAll(css);
    els.forEach(function(el) { el.style.outline = "3px solid #4CAF50"; el.style.outlineOffset = "2px"; });
    return els.length;
  };
})();
