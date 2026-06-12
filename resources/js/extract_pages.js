function extractTotalPages(selector) {
  var links = document.querySelectorAll(selector);
  var nums = Array.from(links).map(function(el) {
    var val = el.getAttribute("data-page") || el.textContent;
    return parseInt(val, 10);
  }).filter(function(n) { return Number.isInteger(n) && n > 0; });
  return nums.length ? Math.max.apply(null, nums) : null;
}

function extractNextUrl(selector) {
  var el = document.querySelector(selector);
  return el ? (el.href || null) : null;
}
