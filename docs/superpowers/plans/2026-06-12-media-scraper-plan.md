# 通用网站媒体下载器 — 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement. Steps use checkbox syntax.

**Goal:** PyQt5 GUI 程序，通过可视化点选定义爬取规则，从任意网站逐层提取图片和视频并下载。视频支持 m3u8→mp4 自动转换。

**Architecture:** 单实例 QWebEnginePage 作为浏览器引擎，规则构建/爬取/下载三个模块通过 `pyqtSignal` + `queue.Queue` 通信，下载引擎使用 `ThreadPoolExecutor` + ffmpeg subprocess。

**Tech Stack:** Python 3.10+, PyQt5, Qt WebEngine, ffmpeg, pytest+pytest-qt

---

## 文件结构

```
getIv/
├── app/
│   ├── __init__.py
│   ├── main.py                 # 入口 QApplication 启动
│   ├── config.py               # config.json 加载/保存
│   ├── models.py               # SiteRule, SelectorRule, AntiCrawlConfig 等数据模型
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py      # 主窗口: 三区布局
│   │   ├── browser_panel.py    # 嵌入式 WebEngine 面板
│   │   ├── data_panel.py       # URL输入, 规则选择, 分页/详情列表
│   │   ├── bottom_bar.py       # 进度条, 控制按钮, 日志
│   │   └── settings_dialog.py  # 设置对话框
│   ├── rule_builder/
│   │   ├── __init__.py
│   │   ├── selector_picker.py  # 可视化点选 (JS注入 + Python 桥)
│   │   ├── picker_bridge.py    # QWebChannel 桥接对象 (JS→Python)
│   │   └── type_selector_dialog.py  # 点选后类型标注对话框
│   ├── crawl_engine/
│   │   ├── __init__.py
│   │   ├── js_injector.py      # JS 脚本管理 + 注入包装
│   │   └── crawler.py          # 多页爬取编排
│   └── download_engine/
│       ├── __init__.py
│       ├── downloader.py       # 线程池下载器
│       └── m3u8_handler.py     # m3u8→mp4 转换 + 清理
├── resources/
│   └── js/
│       ├── extract_links.js
│       ├── extract_media.js
│       ├── extract_pages.js
│       └── selector_picker.js
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_selector_utils.py
│   ├── test_js_injector.py
│   ├── test_downloader.py
│   └── test_m3u8_handler.py
├── requirements.txt
└── config.json
```

---

## Chunk 1: 基础框架

### Task 1: 项目脚手架

- [ ] **创建 requirements.txt**

```
PyQt5>=5.15
PyQtWebEngine>=5.15
```

- [ ] **创建 app/__init__.py** — 空文件
- [ ] **创建 models.py** — 所有数据模型

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SelectorRule:
    css: str
    attribute: str
    wait_selector: str = ""
    lazy_scroll: bool = False

@dataclass
class AntiCrawlConfig:
    delay_range: tuple = (1, 3)
    use_proxy: bool = False
    proxy_list: Optional[list[str]] = None
    random_user_agent: bool = True

@dataclass
class SiteRule:
    name: str
    url_pattern: str
    pagination: Optional[SelectorRule] = None
    page_list: SelectorRule
    detail_images: SelectorRule
    detail_videos: Optional[SelectorRule] = None
    next_button: Optional[SelectorRule] = None
    anti_crawl: AntiCrawlConfig = field(default_factory=AntiCrawlConfig)

@dataclass
class CrawlResult:
    source_url: str
    page_title: str
    detail_urls: list[str]
    media_urls: list[dict]

@dataclass
class DownloadProgress:
    total_files: int
    completed: int
    failed: int
    current_file: str
    bytes_downloaded: int
    total_bytes: int
    speed: float
```

- [ ] **创建 config.py**

```python
import json, os

DEFAULT_CONFIG = {
    "download_threads": 10,
    "save_path": "",
    "speed_limit": 0,
    "resume_enabled": True,
    "delay_min": 1,
    "delay_max": 3,
    "random_ua": True,
    "proxy_list": [],
    "ffmpeg_path": "ffmpeg",
    "page_timeout": 30,
    "js_retries": 3,
    "rules": []
}

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return dict(DEFAULT_CONFIG)

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
```

- [ ] **创建 main.py** — 简易入口占位

```python
import sys
from PyQt5.QtWidgets import QApplication
from app.gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GetIv")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
```

- [ ] **提交: git add -A && git commit -m "feat: add scaffold, models, config, entrypoint"**

---

### Task 2: GUI 主窗口骨架

- [ ] **创建 app/gui/__init__.py** — 空
- [ ] **创建 app/gui/main_window.py** — 三区布局

```python
from PyQt5.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget
from app.gui.browser_panel import BrowserPanel
from app.gui.data_panel import DataPanel
from app.gui.bottom_bar import BottomBar

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GetIv - 网站媒体下载器")
        self.resize(1200, 800)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter()
        self.browser_panel = BrowserPanel()
        self.data_panel = DataPanel()
        splitter.addWidget(self.browser_panel)
        splitter.addWidget(self.data_panel)
        splitter.setSizes([600, 600])
        layout.addWidget(splitter)
        self.bottom_bar = BottomBar()
        layout.addWidget(self.bottom_bar)
```

- [ ] **创建 app/gui/browser_panel.py** — 占位

```python
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

class BrowserPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("浏览器面板 (WebEngine)"))
```

- [ ] **创建 app/gui/data_panel.py** — 占位

```python
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

class DataPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("数据面板 (URL输入 + 列表)"))
```

- [ ] **创建 app/gui/bottom_bar.py** — 占位

```python
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QProgressBar, QPushButton, QLabel

class BottomBar(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        self.progress = QProgressBar()
        self.btn_pause = QPushButton("暂停")
        self.btn_cancel = QPushButton("取消")
        self.log_label = QLabel("就绪")
        layout.addWidget(self.progress, 1)
        layout.addWidget(self.btn_pause)
        layout.addWidget(self.btn_cancel)
        layout.addWidget(self.log_label)
```

- [ ] **提交: git add -A && git commit -m "feat: add main window skeleton with 3-panel layout"**

---

## Chunk 2: 浏览器面板 + 点选引擎

### Task 3: 浏览器面板 (WebEngine)

- [ ] **覆盖 Chunk 1 中创建的占位 browser_panel.py（删除 QLabel，替换为导航栏 + QWebEngineView）**

```python
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl

class BrowserPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        nav = QHBoxLayout()
        self.btn_back = QPushButton("◀")
        self.btn_forward = QPushButton("▶")
        self.btn_refresh = QPushButton("🔄")
        self.btn_pick = QPushButton("点选模式")
        self.btn_pick.setCheckable(True)
        nav.addWidget(self.btn_back)
        nav.addWidget(self.btn_forward)
        nav.addWidget(self.btn_refresh)
        nav.addStretch()
        nav.addWidget(self.btn_pick)
        layout.addLayout(nav)
        self.webview = QWebEngineView()
        self.btn_back.clicked.connect(self.webview.back)
        self.btn_forward.clicked.connect(self.webview.forward)
        self.btn_refresh.clicked.connect(self.webview.reload)
        layout.addWidget(self.webview)

    def navigate(self, url):
        self.webview.setUrl(QUrl(url))

    def page(self):
        return self.webview.page()
```

- [ ] **提交: git commit -am "feat: implement browser panel with navigation and pick mode toggle"**

---

### Task 4: 可视化点选 — QWebChannel 桥接

点选引擎使用 `QWebChannel` 实现 JS→Python 通信，这是 PyQt5 的标准双向桥接方式。

- [ ] **创建 app/rule_builder/__init__.py** — 空文件

- [ ] **创建 app/rule_builder/picker_bridge.py** — Python 端桥接对象

```python
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal

class PickerBridge(QObject):
    elementPicked = pyqtSignal(str)  # CSS Selector 被传递到 Python

    @pyqtSlot(str)
    def onElementPicked(self, selector: str):
        self.elementPicked.emit(selector)
```

- [ ] **创建 resources/js/selector_picker.js**

```javascript
(function() {
  var SELECTED_CSS = "outline: 3px solid #4CAF50 !important; outline-offset: 2px;";

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
      e.target.style.cssText += SELECTED_CSS;
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
    var count = document.querySelectorAll(css).length;
    var els = document.querySelectorAll(css);
    els.forEach(function(el) { el.style.outline = "3px solid #4CAF50"; el.style.outlineOffset = "2px"; });
    return count;
  };

  window.__clearHighlights = function() {
    document.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; });
  };
})();
```

- [ ] **创建 app/rule_builder/selector_picker.py**

```python
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
        base = os.path.join(os.path.dirname(__file__), "..", "..", "resources", "js")
        with open(os.path.join(base, "selector_picker.js")) as f:
            self._js_code = f.read()

    def enable(self):
        """注入 picker JS，通过 Qt 资源加载 qwebchannel.js，初始化通道"""
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
        self._page.runJavaScript("__disablePicker();")

    def validate_selector(self, css: str, callback):
        """验证选择器，用绿框标记匹配元素，返回匹配数"""
        safe_css = json.dumps(css)
        self._page.runJavaScript(f"__validateSelector({safe_css})", callback)

    def clear_highlights(self):
        self._page.runJavaScript("""document.querySelectorAll("[style*='outline']").forEach(function(el) { el.style.outline = ""; });""")

    @property
    def bridge(self) -> PickerBridge:
        return self._bridge
```

- [ ] **创建元素类型标注对话框** — 当用户选取一个元素后弹出，选择类型

```python
# app/rule_builder/type_selector_dialog.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QHBoxLayout

ELEMENT_TYPES = ["分页链接", "详情链接", "图片容器", "视频容器", "下一页按钮"]

class TypeSelectorDialog(QDialog):
    def __init__(self, selector: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择元素类型")
        self.selected_type = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"选择器: {selector}"))
        layout.addWidget(QLabel("这个元素属于什么类型？"))
        for t in ELEMENT_TYPES:
            btn = QPushButton(t)
            btn.clicked.connect(lambda checked, t=t: self._pick(t))
            layout.addWidget(btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

    def _pick(self, t: str):
        self.selected_type = t
        self.accept()
```

- [ ] **提交: git commit -am "feat: add visual element picker with QWebChannel bridge and type dialog"**

---

### Task 5: CSS Selector 归纳

JS 端的 `getElementSelector()` 负责单个元素的选择器生成。Python 端收集用户对同一类型的多次点选结果，归纳为通用规则。

- [ ] **在 app/rule_builder/__init__.py 或 picker_bridge.py 中添加 generalize 方法**

```python
def generalize_selectors(selectors: list[str]) -> str:
    """多个选择器归纳为通用规则"""
    if not selectors:
        return ""
    if len(selectors) == 1:
        return selectors[0]
    parts = [s.split(" > ") for s in selectors]
    common = []
    for segs in zip(*parts):
        if len(set(segs)) == 1:
            common.append(segs[0])
        else:
            break
    return " > ".join(common) if common else selectors[0]
```

- [ ] **提交: git commit -am "feat: add generalize_selectors helper for multi-pick"**

- [ ] **提交: git commit -am "feat: add CSS selector generation and generalization"**

---

## Chunk 3: 爬取引擎

### Task 6: JS 注入脚本

- [ ] **创建 app/crawl_engine/__init__.py** — 空文件

- [ ] **创建 resources/js/extract_links.js**

```javascript
function extractLinks(selector, attribute) {
  var els = document.querySelectorAll(selector);
  return Array.from(els).map(function(el) {
    return {
      url: el.getAttribute(attribute) || el.href || el.src,
      text: (el.textContent || "").trim().slice(0, 100)
    };
  });
}
```

- [ ] **创建 resources/js/extract_media.js**

```javascript
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
```

- [ ] **创建 resources/js/extract_pages.js**

```javascript
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

function lazyScroll() {
  window.scrollTo(0, document.body.scrollHeight);
  return new Promise(function(r) { setTimeout(r, 1500); });
}
```

- [ ] **创建 app/crawl_engine/js_injector.py**

```python
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
        return f"{self._scripts['extract_links']}\nextractLinks('{selector}', '{attribute}');"

    def build_extract_media_js(self, css: str, attr: str) -> str:
        return f"{self._scripts['extract_media']}\nextractMedia('{css}', '{attr}');"
```

- [ ] **提交: git commit -am "feat: add JS injection scripts and injector module"**

---

### Task 7: 爬取编排器

- [ ] **创建 app/crawl_engine/crawler.py**

```python
from PyQt5.QtCore import QObject, pyqtSignal
from app.models import SiteRule
from app.crawl_engine.js_injector import JSInjector

class Crawler(QObject):
    linksFound = pyqtSignal(list)     # [{"url":..., "text":...}]
    mediaFound = pyqtSignal(list)     # [{"url":..., "type":...}]
    pageCount = pyqtSignal(int)
    crawlError = pyqtSignal(str)

    def __init__(self, page):
        super().__init__()
        self._page = page
        self._js = JSInjector()

    def extract_pagination(self, rule: SiteRule):
        if not rule.pagination:
            return
        js = self._js.build_extract_links_js(rule.pagination.css, rule.pagination.attribute)
        self._page.runJavaScript(js, self.linksFound.emit)

    def extract_detail_links(self, rule: SiteRule):
        js = self._js.build_extract_links_js(rule.page_list.css, rule.page_list.attribute)
        self._page.runJavaScript(js, self.linksFound.emit)

    def extract_media(self, rule: SiteRule, media_type: str = "image"):
        sr = rule.detail_images if media_type == "image" else rule.detail_videos
        if not sr:
            return
        js = self._js.build_extract_media_js(sr.css, sr.attribute)
        self._page.runJavaScript(js, self.mediaFound.emit)

    def extract_total_pages(self, rule: SiteRule):
        if not rule.pagination:
            return
        js = self._js.get_script("extract_pages")
        js += f"\nextractTotalPages('{rule.pagination.css}');"
        self._page.runJavaScript(js, self.pageCount.emit)
```

- [ ] **提交: git commit -am "feat: add crawler orchestration with pyqtSignal results"**

---

## Chunk 4: 数据面板 + 交互

### Task 8: 数据面板完整实现

- [ ] **实现 app/gui/data_panel.py**

```python
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QComboBox, QSplitter, QLabel)
from PyQt5.QtCore import pyqtSignal

class DataPanel(QWidget):
    urlSubmitted = pyqtSignal(str)
    ruleSelected = pyqtSignal(str)
    pageDoubleClicked = pyqtSignal(str)
    detailDoubleClicked = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        # URL input
        url_bar = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入网址...")
        self.btn_analyze = QPushButton("分析")
        url_bar.addWidget(self.url_input)
        url_bar.addWidget(self.btn_analyze)
        layout.addLayout(url_bar)
        # Rule selector
        rule_bar = QHBoxLayout()
        self.rule_selector = QComboBox()
        self.rule_selector.addItem("选择规则...")
        self.btn_new_rule = QPushButton("新建规则")
        rule_bar.addWidget(self.rule_selector)
        rule_bar.addWidget(self.btn_new_rule)
        layout.addLayout(rule_bar)
        # Lists
        splitter = QSplitter()
        self.page_list = QListWidget()
        self.detail_list = QListWidget()
        self.page_list.setHeaderHidden(True)
        self.detail_list.setHeaderHidden(True)
        splitter.addWidget(self.page_list)
        splitter.addWidget(self.detail_list)
        layout.addWidget(splitter)
        # Signals
        self.url_input.returnPressed.connect(lambda: self.urlSubmitted.emit(self.url_input.text()))
        self.btn_analyze.clicked.connect(lambda: self.urlSubmitted.emit(self.url_input.text()))
        self.page_list.itemDoubleClicked.connect(lambda item: self.pageDoubleClicked.emit(item.data(256)))
        self.detail_list.itemDoubleClicked.connect(lambda item: self.detailDoubleClicked.emit(item.data(256)))

    def add_page_item(self, text: str, url: str):
        item = QListWidgetItem(text)
        item.setData(256, url)
        self.page_list.addItem(item)

    def add_detail_item(self, text: str, url: str):
        item = QListWidgetItem(text)
        item.setData(256, url)
        self.detail_list.addItem(item)

    def clear_pages(self):
        self.page_list.clear()

    def clear_details(self):
        self.detail_list.clear()
```

- [ ] **提交: git commit -am "feat: implement data panel with URL input, rule selector, and lists"**

---

### Task 9: 底部栏完整实现

- [ ] **实现 app/gui/bottom_bar.py**

```python
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QProgressBar, QPushButton, QTextEdit
from PyQt5.QtCore import pyqtSignal
import time

class BottomBar(QWidget):
    pauseRequested = pyqtSignal()
    cancelRequested = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(300)
        self.btn_pause = QPushButton("暂停")
        self.btn_cancel = QPushButton("取消")
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(60)
        self.log.setMaximumWidth(400)
        layout.addWidget(self.progress)
        layout.addWidget(self.btn_pause)
        layout.addWidget(self.btn_cancel)
        layout.addWidget(self.log, 1)
        self.btn_pause.clicked.connect(self.pauseRequested.emit)
        self.btn_cancel.clicked.connect(self.cancelRequested.emit)

    def log_message(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self.log.append(f"[{ts}] {msg}")

    def update_progress(self, current: int, total: int):
        self.progress.setMaximum(total)
        self.progress.setValue(current)
```

- [ ] **提交: git commit -am "feat: implement bottom bar with progress, controls, and log"**

---

### Task 10: 设置对话框

- [ ] **创建 app/gui/settings_dialog.py**

```python
from PyQt5.QtWidgets import (QDialog, QFormLayout, QSpinBox,
    QLineEdit, QCheckBox, QDoubleSpinBox, QTextEdit, QDialogButtonBox,
    QTabWidget, QWidget, QVBoxLayout)

class SettingsDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self._config = config
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_download_tab(), "下载")
        tabs.addTab(self._build_anti_crawl_tab(), "反爬")
        tabs.addTab(self._build_browser_tab(), "浏览器")
        layout.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_download_tab(self):
        w = QWidget()
        f = QFormLayout(w)
        self.spin_threads = QSpinBox(); self.spin_threads.setRange(1, 50)
        self.spin_threads.setValue(self._config.get("download_threads", 10))
        self.edit_path = QLineEdit(self._config.get("save_path", ""))
        self.spin_speed = QDoubleSpinBox(); self.spin_speed.setRange(0, 100)
        self.spin_speed.setValue(self._config.get("speed_limit", 0))
        self.chk_resume = QCheckBox(); self.chk_resume.setChecked(self._config.get("resume_enabled", True))
        self.edit_ffmpeg = QLineEdit(self._config.get("ffmpeg_path", "ffmpeg"))
        f.addRow("线程数:", self.spin_threads)
        f.addRow("保存路径:", self.edit_path)
        f.addRow("限速 (MB/s, 0=不限):", self.spin_speed)
        f.addRow("断点续传:", self.chk_resume)
        f.addRow("ffmpeg 路径:", self.edit_ffmpeg)
        return w

    def _build_anti_crawl_tab(self):
        w = QWidget()
        f = QFormLayout(w)
        self.spin_delay_min = QDoubleSpinBox(); self.spin_delay_min.setRange(0, 60)
        self.spin_delay_min.setValue(self._config.get("delay_min", 1))
        self.spin_delay_max = QDoubleSpinBox(); self.spin_delay_max.setRange(0, 60)
        self.spin_delay_max.setValue(self._config.get("delay_max", 3))
        self.chk_ua = QCheckBox(); self.chk_ua.setChecked(self._config.get("random_ua", True))
        self.edit_proxies = QTextEdit()
        self.edit_proxies.setPlainText("\n".join(self._config.get("proxy_list", [])))
        f.addRow("最小延迟 (秒):", self.spin_delay_min)
        f.addRow("最大延迟 (秒):", self.spin_delay_max)
        f.addRow("随机 UA:", self.chk_ua)
        f.addRow("代理列表:", self.edit_proxies)
        return w

    def _build_browser_tab(self):
        w = QWidget()
        f = QFormLayout(w)
        self.spin_timeout = QSpinBox(); self.spin_timeout.setRange(5, 120)
        self.spin_timeout.setValue(self._config.get("page_timeout", 30))
        self.spin_retries = QSpinBox(); self.spin_retries.setRange(0, 10)
        self.spin_retries.setValue(self._config.get("js_retries", 3))
        f.addRow("加载超时 (秒):", self.spin_timeout)
        f.addRow("JS 重试次数:", self.spin_retries)
        return w

    def get_config(self) -> dict:
        return {
            "download_threads": self.spin_threads.value(),
            "save_path": self.edit_path.text(),
            "speed_limit": self.spin_speed.value(),
            "resume_enabled": self.chk_resume.isChecked(),
            "ffmpeg_path": self.edit_ffmpeg.text(),
            "delay_min": self.spin_delay_min.value(),
            "delay_max": self.spin_delay_max.value(),
            "random_ua": self.chk_ua.isChecked(),
            "proxy_list": self.edit_proxies.toPlainText().strip().splitlines(),
            "page_timeout": self.spin_timeout.value(),
            "js_retries": self.spin_retries.value(),
        }
```

- [ ] **提交: git commit -am "feat: add settings dialog with download/anti-crawl/browser tabs"**

---

## Chunk 5: 下载引擎

### Task 11: HTTP 下载器

- [ ] **创建 app/download_engine/__init__.py** — 空文件

- [ ] **创建 app/download_engine/downloader.py**

```python
import os, time, random
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
from PyQt5.QtCore import QObject, pyqtSignal
from app.models import DownloadProgress

class Downloader(QObject):
    progressUpdated = pyqtSignal(DownloadProgress)
    downloadComplete = pyqtSignal()
    downloadError = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self._config = config
        self._pool = None
        self._paused = False
        self._cancelled = False

    def start(self, media_urls: list, save_dir: str):
        self._cancelled = False
        self._paused = False
        threads = self._config.get("download_threads", 10)
        self._pool = ThreadPoolExecutor(max_workers=threads)
        total = len(media_urls)
        completed = 0
        failed = 0
        futures = []
        for item in media_urls:
            if self._cancelled:
                break
            url = item["url"] if isinstance(item, dict) else item
            fname = self._safe_filename(os.path.basename(url.split("?")[0]))
            fpath = os.path.join(save_dir, fname)
            future = self._pool.submit(self._download_file, url, fpath)
            futures.append(future)
        for f in as_completed(futures):
            if self._cancelled:
                break
            while self._paused and not self._cancelled:
                time.sleep(0.5)
            try:
                f.result()
                completed += 1
            except Exception as e:
                failed += 1
                self.downloadError.emit(str(e))
            self.progressUpdated.emit(DownloadProgress(
                total, completed, failed, "", 0, 0, 0))
        self.downloadComplete.emit()

    def _download_file(self, url: str, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        delay = self._config.get("delay_min", 1)
        delay_max = self._config.get("delay_max", 3)
        time.sleep(random.uniform(delay, delay_max))
        headers = {"User-Agent": self._random_ua()} if self._config.get("random_ua") else {}
        resume = self._config.get("resume_enabled", True)
        if resume and os.path.exists(path):
            existing = os.path.getsize(path)
            headers["Range"] = f"bytes={existing}-"
            resp = requests.get(url, headers=headers, stream=True, timeout=30)
            if resp.status_code == 206:
                mode = "ab"
            else:
                mode = "wb"
        else:
            resp = requests.get(url, headers=headers, stream=True, timeout=30)
            resp.raise_for_status()
            mode = "wb"
        with open(path, mode) as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    def _safe_filename(self, name: str) -> str:
        illegal = '<>:"/\\|?*'
        for c in illegal:
            name = name.replace(c, "_")
        return name or "download"

    def _random_ua(self) -> str:
        import random
        uas = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
        ]
        return random.choice(uas)

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def cancel(self):
        self._cancelled = True
```

- [ ] **提交: git commit -am "feat: implement multi-threaded HTTP downloader with resume and anti-crawl delays"**

---

### Task 12: m3u8 处理器

- [ ] **创建 app/download_engine/m3u8_handler.py**

```python
import os, re, subprocess, tempfile, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

class M3U8Handler:
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self._ffmpeg = ffmpeg_path

    def download_and_convert(self, m3u8_url: str, output_path: str) -> str:
        """下载 m3u8 并转 mp4，返回 mp4 路径"""
        base = os.path.dirname(m3u8_url)
        resp = requests.get(m3u8_url, timeout=30)
        resp.raise_for_status()
        content = resp.text
        ts_urls = self._parse_ts_urls(content, base)
        tmpdir = tempfile.mkdtemp(prefix="getiv_")
        ts_files = self._download_segments(ts_urls, tmpdir)
        mp4_path = output_path
        if not mp4_path.endswith(".mp4"):
            mp4_path += ".mp4"
        self._concat_to_mp4(ts_files, mp4_path)
        self._cleanup(tmpdir)
        return mp4_path

    def _parse_ts_urls(self, m3u8_content: str, base_url: str) -> list[str]:
        urls = []
        for line in m3u8_content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                if line.startswith("http"):
                    urls.append(line)
                else:
                    urls.append(base_url.rstrip("/") + "/" + line.lstrip("/"))
        return urls

    def _download_segments(self, ts_urls: list[str], tmpdir: str) -> list[str]:
        files = []
        with ThreadPoolExecutor(max_workers=10) as pool:
            def dl(i, url):
                r = requests.get(url, timeout=30)
                r.raise_for_status()
                path = os.path.join(tmpdir, f"seg_{i:04d}.ts")
                with open(path, "wb") as f:
                    f.write(r.content)
                return path
            futures = {pool.submit(dl, i, u): i for i, u in enumerate(ts_urls)}
            for f in as_completed(futures):
                files.append(f.result())
        files.sort()
        return files

    def _concat_to_mp4(self, ts_files: list[str], output: str):
        list_path = os.path.join(os.path.dirname(ts_files[0]), "concat.txt")
        with open(list_path, "w") as f:
            for tf in ts_files:
                f.write(f"file '{tf}'\n")
        subprocess.run([
            self._ffmpeg, "-f", "concat", "-safe", "0",
            "-i", list_path, "-c", "copy", "-y", output
        ], check=True, capture_output=True, timeout=300)

    def _cleanup(self, tmpdir: str):
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
```

- [ ] **提交: git commit -am "feat: implement m3u8→mp4 converter with parallel segment download and cleanup"**

---

## Chunk 6: 主窗口集成

### Task 13: 集成所有模块

- [ ] **更新 app/gui/main_window.py** — 完整集成

```python
import os
from PyQt5.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget, QAction, QMessageBox
from PyQt5.QtCore import Qt, QUrl
from app.gui.browser_panel import BrowserPanel
from app.gui.data_panel import DataPanel
from app.gui.bottom_bar import BottomBar
from app.gui.settings_dialog import SettingsDialog
from app.crawl_engine.crawler import Crawler
from app.download_engine.downloader import Downloader
from app.download_engine.m3u8_handler import M3U8Handler
from app.config import load_config, save_config
from app.models import SiteRule, DownloadProgress
from app.rule_builder.selector_picker import SelectorPicker
from app.rule_builder.type_selector_dialog import TypeSelectorDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GetIv - 网站媒体下载器")
        self.resize(1200, 800)
        self._config = load_config()
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        self._build_menu()
        splitter = QSplitter()
        self.browser_panel = BrowserPanel()
        self.data_panel = DataPanel()
        splitter.addWidget(self.browser_panel)
        splitter.addWidget(self.data_panel)
        splitter.setSizes([600, 600])
        layout.addWidget(splitter)
        self.bottom_bar = BottomBar()
        layout.addWidget(self.bottom_bar)
        # Engines
        self._crawler = Crawler(self.browser_panel.page())
        self._downloader = Downloader(self._config)
        self._m3u8_handler = M3U8Handler(self._config.get("ffmpeg_path", "ffmpeg"))
        self._selector_picker = SelectorPicker(self.browser_panel.page())
        # Connect signals
        self.data_panel.urlSubmitted.connect(self._on_url_submitted)
        self.data_panel.pageDoubleClicked.connect(self._on_page_double_clicked)
        self.data_panel.detailDoubleClicked.connect(self._on_detail_double_clicked)
        self._crawler.linksFound.connect(self._on_links_found)
        self._crawler.mediaFound.connect(self._on_media_found)
        self._downloader.progressUpdated.connect(self._on_download_progress)
        self._selector_picker.bridge.elementPicked.connect(self._on_element_picked)
        self.browser_panel.btn_pick.clicked.connect(self._toggle_pick_mode)
        self._current_rule = None
        # default URL
        self.browser_panel.navigate("about:blank")

    def _build_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        act_import = QAction("导入规则", self)
        act_export = QAction("导出规则", self)
        act_exit = QAction("退出", self)
        act_exit.triggered.connect(self.close)
        file_menu.addActions([act_import, act_export, act_exit])
        tool_menu = menubar.addMenu("工具")
        act_settings = QAction("设置", self)
        act_settings.triggered.connect(self._show_settings)
        tool_menu.addAction(act_settings)
        rule_menu = menubar.addMenu("规则")
        act_new = QAction("新建规则", self)
        rule_menu.addAction(act_new)
        help_menu = menubar.addMenu("帮助")
        act_about = QAction("关于", self)
        help_menu.addAction(act_about)

    def _show_settings(self):
        dlg = SettingsDialog(self._config, self)
        if dlg.exec_():
            self._config.update(dlg.get_config())
            save_config(self._config)
            self.bottom_bar.log_message("设置已保存")

    def _toggle_pick_mode(self, checked):
        self.browser_panel.btn_pick.setText("退出点选" if checked else "点选模式")
        if checked:
            self._selector_picker.enable()
        else:
            self._selector_picker.disable()

    def _on_element_picked(self, selector: str):
        """用户选中一个元素后弹出类型标注对话框"""
        dlg = TypeSelectorDialog(selector, self)
        if dlg.exec_() and dlg.selected_type:
            self.bottom_bar.log_message(f"已标注 [{dlg.selected_type}]: {selector}")
            self._selector_picker.validate_selector(selector, lambda count: self.bottom_bar.log_message(f"选择器匹配到 {count} 个元素"))
        else:
            self.bottom_bar.log_message("元素标注取消")

    def _on_url_submitted(self, url: str):
        self.data_panel.clear_pages()
        self.browser_panel.navigate(url)
        # ideally wait for load finished, then crawl
        self.bottom_bar.log_message(f"导航到: {url}")

    def _on_page_double_clicked(self, url: str):
        self.data_panel.clear_details()
        self.browser_panel.navigate(url)
        self.bottom_bar.log_message(f"打开分页: {url}")

    def _on_detail_double_clicked(self, url: str):
        self.bottom_bar.log_message(f"分析详情: {url}")
        # 详情页媒体提取 — 注入 JS 提取图片/视频
        self.bottom_bar.log_message("详情页面媒体提取待实现")

    def _on_links_found(self, links):
        for link in links:
            self.data_panel.add_page_item(link.get("text", link["url"]), link["url"])
        self.bottom_bar.log_message(f"找到 {len(links)} 个链接")

    def _on_media_found(self, media):
        self.bottom_bar.log_message(f"找到 {len(media)} 个媒体文件")

    def _on_download_progress(self, prog: DownloadProgress):
        self.bottom_bar.update_progress(prog.completed, prog.total_files)
        self.bottom_bar.log_message(f"下载: {prog.completed}/{prog.total_files}, 失败 {prog.failed}")
```

- [ ] **提交: git commit -am "feat: integrate all modules in main window with signal wiring"**

---

## Chunk 7: 测试

### Task 14: 模型测试

- [ ] **创建 tests/__init__.py** — 空文件

- [ ] **创建 tests/test_models.py**

```python
import pytest
from app.models import SiteRule, SelectorRule, AntiCrawlConfig, CrawlResult, DownloadProgress

def test_site_rule_defaults():
    r = SiteRule(name="test", url_pattern="example.com", page_list=SelectorRule("a.link", "href"),
                 detail_images=SelectorRule("img", "src"))
    assert r.name == "test"
    assert r.pagination is None
    assert r.detail_videos is None
    assert r.anti_crawl.delay_range == (1, 3)

def test_crawl_result():
    r = CrawlResult(source_url="http://example.com", page_title="Test", detail_urls=["/a"], media_urls=[{"url": "x.jpg", "type": "image"}])
    assert len(r.media_urls) == 1
```

- [ ] **运行测试: pytest tests/test_models.py -v**
- [ ] **提交: git commit -am "test: add model unit tests"**

---

### Task 15: 选择器归纳测试

- [ ] **创建 tests/test_selector_utils.py**

```python
import pytest
from app.rule_builder import generalize_selectors

def test_generalize_single():
    assert generalize_selectors(["a.link"]) == "a.link"

def test_generalize_multiple():
    sels = ["div.list > a:nth-child(1)", "div.list > a:nth-child(2)"]
    assert generalize_selectors(sels) == "div.list"

def test_generalize_no_common():
    sels = ["a.link", "img.photo"]
    assert generalize_selectors(sels) == "a.link"
```

- [ ] **运行测试: pytest tests/test_selector_utils.py -v**
- [ ] **提交: git commit -am "test: add selector generalization unit tests"**

---

### Task 16: 下载器测试

- [ ] **创建 tests/test_downloader.py**

```python
import pytest, os, tempfile
from app.download_engine.downloader import Downloader
from app.models import DownloadProgress

def test_safe_filename():
    d = Downloader({})
    assert d._safe_filename("a<b>c:d") == "a_b_c_d"
    assert d._safe_filename("normal.jpg") == "normal.jpg"
```

- [ ] **运行测试: pytest tests/test_downloader.py -v**
- [ ] **提交: git commit -am "test: add downloader unit tests"**

---

### Task 17: m3u8 处理器测试

- [ ] **创建 tests/test_m3u8_handler.py**

```python
import pytest, os, tempfile
from app.download_engine.m3u8_handler import M3U8Handler

def test_parse_ts_urls_relative():
    h = M3U8Handler()
    content = "#EXTM3U\n#EXTINF:3,\nseg1.ts\nseg2.ts\n"
    urls = h._parse_ts_urls(content, "http://example.com/video/")
    assert urls == ["http://example.com/video/seg1.ts", "http://example.com/video/seg2.ts"]

def test_parse_ts_urls_absolute():
    h = M3U8Handler()
    content = "#EXTM3U\nhttp://cdn.com/seg1.ts\nhttp://cdn.com/seg2.ts\n"
    urls = h._parse_ts_urls(content, "http://example.com/")
    assert urls == ["http://cdn.com/seg1.ts", "http://cdn.com/seg2.ts"]
```

- [ ] **运行测试: pytest tests/test_m3u8_handler.py -v**
- [ ] **提交: git commit -am "test: add m3u8 handler unit tests"**

---

### Task 18: JS 注入器测试

- [ ] **创建 tests/test_js_injector.py**

```python
import pytest
from app.crawl_engine.js_injector import JSInjector

def test_build_extract_links_js():
    inj = JSInjector()
    js = inj.build_extract_links_js("a.link", "href")
    assert "extractLinks" in js
    assert "a.link" in js
    assert "href" in js

def test_build_extract_media_js():
    inj = JSInjector()
    js = inj.build_extract_media_js("img.lazy", "data-src")
    assert "extractMedia" in js
    assert "img.lazy" in js
```

- [ ] **运行测试: pytest tests/test_js_injector.py -v**
- [ ] **提交: git commit -am "test: add JS injector unit tests"**

---

**Plan complete. Ready to execute.**
