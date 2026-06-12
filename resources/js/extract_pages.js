function extractTotalPages(selector) {
  var nums = [];
  function search(doc) {
    var links = doc.querySelectorAll(selector);
    Array.from(links).forEach(function(el) {
      var val = el.getAttribute("data-page") || el.textContent;
      var n = parseInt(val, 10);
      if (Number.isInteger(n) && n > 0) nums.push(n);
    });
    Array.from(doc.querySelectorAll("iframe")).forEach(function(f) {
      try { if (f.contentDocument) search(f.contentDocument); } catch(e) {}
    });
  }
  search(document);
  return nums.length ? Math.max.apply(null, nums) : null;
}

function extractNextUrl(selector) {
  function search(doc) {
    var el = doc.querySelector(selector);
    if (el) return el.href || null;
    var iframes = doc.querySelectorAll("iframe");
    for (var i = 0; i < iframes.length; i++) {
      try { if (iframes[i].contentDocument) { var r = search(iframes[i].contentDocument); if (r) return r; } } catch(e) {}
    }
    return null;
  }
  return search(document);
}
