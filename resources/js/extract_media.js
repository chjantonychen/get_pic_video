function extractMedia(css, attr) {
  var els = document.querySelectorAll(css);
  return Array.from(els).map(function(el) {
    return {
      url: el.getAttribute(attr) || el.src,
      type: el.tagName === "VIDEO" ? "video" : "image",
      alt: el.getAttribute("alt") || ""
    };
  });
}
