import os, json
from PyQt5.QtCore import QObject
from PyQt5.QtWebChannel import QWebChannel
from app.rule_builder.picker_bridge import PickerBridge


class SelectorPicker(QObject):
    def __init__(self, page):
        super().__init__()
        self._page = page
        self._bridge = PickerBridge()
        self._channel = QWebChannel(page)
        self._channel.registerObject("picker", self._bridge)
        page.setWebChannel(self._channel)
        self._enabled = False
        base = os.path.join(os.path.dirname(__file__), "..", "..", "resources", "js")
        with open(os.path.join(base, "selector_picker.js")) as f:
            self._js_code = f.read()

    def enable(self):
        self._enabled = True
        self._page.runJavaScript(self._js_code)
        self._page.runJavaScript("""
            (function() {
                function init() {
                    new QWebChannel(qt.webChannelTransport, function(ch) {
                        window.__pickerBridge = ch.objects.picker;
                        __enablePicker();
                    });
                }
                if (typeof QWebChannel !== 'undefined') { init(); }
                else {
                    var s = document.createElement('script');
                    s.src = 'qrc:///qtwebchannel/qwebchannel.js';
                    s.onload = init;
                    document.head.appendChild(s);
                }
            })();
        """)

    def disable(self):
        self._enabled = False
        self._page.runJavaScript("""document.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; });""")
        self._page.runJavaScript("__disablePicker();")

    def reenable(self):
        """导航后重新注入（若点选模式仍激活）"""
        if self._enabled:
            self.enable()

    def validate_selector(self, css: str, callback):
        safe_css = json.dumps(css)
        self._page.runJavaScript(f"__validateSelector({safe_css})", callback)

    def clear_highlights(self):
        self._page.runJavaScript("""document.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; });""")

    @property
    def bridge(self) -> PickerBridge:
        return self._bridge
