function extractLinks(selector, attribute) {
  var els = document.querySelectorAll(selector);
  return Array.from(els).map(function(el) {
    return {
      url: el.getAttribute(attribute) || el.href || el.src,
      text: (el.textContent || "").trim().slice(0, 100)
    };
  });
}
