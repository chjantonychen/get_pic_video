import json
import os

class JSInjector:
    def __init__(self):
        self._scripts = {}
        base = os.path.join(os.path.dirname(__file__), "..", "..", "resources", "js")
        for name in ["extract_links", "extract_media", "extract_pages"]:
            with open(os.path.join(base, f"{name}.js")) as f:
                self._scripts[name] = f.read()

    def get_script(self, name: str) -> str:
        return self._scripts.get(name, "")

    def build_extract_links_js(self, selector: str, attribute: str) -> str:
        return f"{self._scripts['extract_links']}\nextractLinks({json.dumps(selector)}, {json.dumps(attribute)});"

    def build_extract_links_by_pattern_js(self, url_pattern: str) -> str:
        if not url_pattern:
            return "[]"
        return f"""
(function() {{
  var all = [];
  var re = new RegExp({json.dumps(url_pattern)});
  function search(doc) {{
    Array.from(doc.querySelectorAll('a[href]')).forEach(function(el) {{
      var href = el.href;
      if (re.test(href)) all.push({{url: href, text: (el.textContent||'').trim().slice(0,100)}});
    }});
    Array.from(doc.querySelectorAll('iframe')).forEach(function(f) {{
      try {{ if (f.contentDocument) search(f.contentDocument); }} catch(e) {{}}
    }});
  }}
  search(document);
  return all;
}})();
"""

    def build_extract_media_js(self, css: str, attr: str) -> str:
        return f"{self._scripts['extract_media']}\nextractMedia({json.dumps(css)}, {json.dumps(attr)});"

    def build_extract_all_pages_js(self, selector: str) -> str:
        return f"""
(function() {{
  var result = [];
  var maxPage = 0, urlTemplate = '';
  function search(doc) {{
    Array.from(doc.querySelectorAll({json.dumps(selector)})).forEach(function(el) {{
      var text = (el.textContent || '').trim();
      var n = parseInt(text, 10);
      if (!isNaN(n) && n > maxPage) maxPage = n;
      var href = el.getAttribute('href') || el.href || '';
      if (href && !urlTemplate && n > 0) urlTemplate = href.replace(n.toString(), '{{page}}');
    }});
    Array.from(doc.querySelectorAll('iframe')).forEach(function(f) {{
      try {{ if (f.contentDocument) search(f.contentDocument); }} catch(e) {{}}
    }});
  }}
  search(document);
  if (maxPage > 0 && urlTemplate) {{
    for (var i = 1; i <= maxPage; i++) {{
      result.push({{url: urlTemplate.replace('{{page}}', i.toString()), text: '\\u7b2c' + i + '\\u9875'}});
    }}
  }}
  return result;
}})();
"""
