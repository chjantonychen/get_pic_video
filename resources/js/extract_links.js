function extractLinks(selector, attribute) {
  var all = [];
  function search(doc) {
    var els = doc.querySelectorAll(selector);
    Array.from(els).forEach(function(el) {
      all.push({
        url: el.getAttribute(attribute) || el.href || el.src,
        text: (el.textContent || "").trim().slice(0, 100)
      });
    });
    Array.from(doc.querySelectorAll("iframe")).forEach(function(f) {
      try { if (f.contentDocument) search(f.contentDocument); } catch(e) {}
    });
  }
  search(document);
  return all;
}
