function extractMedia(css, attr) {
  var all = [];
  function search(doc) {
    var els = doc.querySelectorAll(css);
    Array.from(els).forEach(function(el) {
      all.push({
        url: el.getAttribute(attr) || el.src,
        type: el.tagName === "VIDEO" ? "video" : "image",
        alt: el.getAttribute("alt") || ""
      });
    });
    Array.from(doc.querySelectorAll("iframe")).forEach(function(f) {
      try { if (f.contentDocument) search(f.contentDocument); } catch(e) {}
    });
  }
  search(document);
  return all;
}
