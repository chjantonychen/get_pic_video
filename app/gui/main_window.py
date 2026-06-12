from PyQt5.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget, QAction
from PyQt5.QtCore import QUrl
import json, urllib.parse
from app.gui.browser_panel import BrowserPanel
from app.gui.data_panel import DataPanel
from app.gui.bottom_bar import BottomBar
from app.gui.settings_dialog import SettingsDialog
from app.crawl_engine.crawler import Crawler
from app.download_engine.downloader import Downloader
from app.download_engine.m3u8_handler import M3U8Handler
from app.config import load_config, save_config
from app.models import SiteRule, SelectorRule, DownloadProgress
from app.rule_builder.selector_picker import SelectorPicker
from app.rule_builder.type_selector_dialog import TypeSelectorDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GetIv - 网站媒体下载器")
        self.resize(1200, 800)
        self._config = load_config()
        self._current_rule = None
        self._picked_selectors = {}
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
        self._crawler = Crawler(self.browser_panel.page())
        self._m3u8_handler = M3U8Handler(self._config.get("ffmpeg_path", "ffmpeg"))
        self._downloader = Downloader(self._config, m3u8_handler=self._m3u8_handler)
        self._selector_picker = SelectorPicker(self.browser_panel.page())
        self._pending_media = []
        self._load_rule_list()
        self.data_panel.urlSubmitted.connect(self._on_url_submitted)
        self.data_panel.btn_analyze.clicked.connect(self._on_analyze)
        self.data_panel.pageDoubleClicked.connect(self._on_page_double_clicked)
        self.data_panel.detailDoubleClicked.connect(self._on_detail_double_clicked)
        self._crawler.linksFound.connect(self._on_detail_links_found)
        self._crawler.mediaFound.connect(self._on_media_found)
        self._downloader.progressUpdated.connect(self._on_download_progress)
        self._selector_picker.elementPicked.connect(self._on_element_picked)
        self.data_panel.btn_new_rule.clicked.connect(self._start_new_rule)
        self.browser_panel.btn_pick.clicked.connect(self._toggle_pick_mode)
        self.bottom_bar.downloadRequested.connect(self._start_download)
        self.browser_panel.webview.page().titleChanged.connect(self._on_page_title_changed)
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
        act_new.triggered.connect(self._start_new_rule)
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

    def _load_rule_list(self):
        self.data_panel.rule_selector.clear()
        self.data_panel.rule_selector.addItem("选择规则...")
        for r in self._config.get("rules", []):
            self.data_panel.rule_selector.addItem(r.get("name", "未命名规则"))
        self.data_panel.rule_selector.currentIndexChanged.connect(self._on_rule_selected)

    def _on_rule_selected(self, idx):
        if idx > 0 and idx - 1 < len(self._config.get("rules", [])):
            self._current_rule = self._config["rules"][idx - 1]
            self.bottom_bar.log_message(f"已选择规则: {self._current_rule['name']}")

    def _start_new_rule(self):
        self._current_rule = None
        self._picked_selectors = {}
        self.data_panel.clear_pages()
        self.data_panel.clear_details()
        self.data_panel.rule_selector.setCurrentIndex(0)
        self.bottom_bar.log_message("新建规则: 先在URL输入框导航到目标网站，页面加载完成后点击「点选模式」按钮")

    def _toggle_pick_mode(self, checked):
        self.browser_panel.btn_pick.setText("开启点选" if not checked else "退出点选")
        if checked:
            self._selector_picker.enable()
        else:
            self._selector_picker.disable()
            if self._picked_selectors:
                self._save_rule_from_picks()

    def _save_rule_from_picks(self):
        from app.models import SiteRule, SelectorRule
        type_map = {
            "分页链接": "pagination", "详情链接": "page_list",
            "图片容器": "detail_images", "视频容器": "detail_videos",
            "下一页按钮": "next_button"
        }
        kwargs = {"name": f"规则_{len(self._config['rules']) + 1}", "url_pattern": ""}
        for label, picks in self._picked_selectors.items():
            field = type_map.get(label)
            if field and picks:
                p = picks[0]
                kwargs[field] = SelectorRule(
                    css=p.get("css", ""),
                    attribute=p.get("attribute", "href"),
                    url_pattern=p.get("url_pattern", ""),
                )
        if "page_list" not in kwargs or "detail_images" not in kwargs:
            self.bottom_bar.log_message("规则不完整: 至少需要标注「详情链接」和「图片容器」")
            return
        try:
            rule = SiteRule(**kwargs)
            import dataclasses, json
            rule_dict = dataclasses.asdict(rule)
            self._config["rules"].append(rule_dict)
            save_config(self._config)
            self.data_panel.rule_selector.addItem(rule.name)
            self.bottom_bar.log_message(f"规则已保存: {rule.name}")
            self._picked_selectors = {}
        except Exception as e:
            self.bottom_bar.log_message(f"保存规则失败: {e}")

    def _on_element_picked(self, data_json: str):
        try:
            data = json.loads(data_json)
            selector = data.get("selector", "")
            attrs = data.get("attrs", [])
        except:
            selector = data_json
            attrs = []
        dlg = TypeSelectorDialog(selector, attrs, self)
        if dlg.exec_() and dlg.selected_type:
            t = dlg.selected_type
            attr = dlg.selected_attribute or "href"
            entry = {"css": selector, "attribute": attr}
            if dlg.use_url_pattern and dlg.url_pattern:
                entry["url_pattern"] = dlg.url_pattern
            self.bottom_bar.log_message(f"已标注 [{t}]: {selector[:60]}... (模式={'URL' if dlg.use_url_pattern else 'CSS'})")
            if t not in self._picked_selectors:
                self._picked_selectors[t] = []
            self._picked_selectors[t].append(entry)
            self._selector_picker.validate_selector(selector,
                lambda count: self.bottom_bar.log_message(f"匹配到 {count} 个元素"))
        else:
            self.bottom_bar.log_message("元素标注取消")

    def _on_url_submitted(self, url: str):
        self.data_panel.clear_pages()
        self._pending_media = []
        self.bottom_bar.set_pending_count(0)
        self.browser_panel.webview.page().loadFinished.connect(self._delayed_auto_analyze)
        self.browser_panel.navigate(url)
        self.bottom_bar.log_message(f"导航到: {url}")

    def _on_analyze(self):
        url = self.data_panel.url_input.text().strip()
        if url:
            self.data_panel.clear_pages()
            self._pending_media = []
            self.bottom_bar.set_pending_count(0)
            self.browser_panel.webview.page().loadFinished.connect(self._delayed_auto_analyze)
            self.browser_panel.navigate(url)
            self.bottom_bar.log_message(f"导航到: {url}")
        elif self._current_rule:
            self._run_crawl_now()

    def _delayed_auto_analyze(self, ok):
        try:
            self.browser_panel.webview.page().loadFinished.disconnect(self._delayed_auto_analyze)
        except TypeError:
            pass
        if not ok:
            return
        if self._current_rule:
            self._run_crawl_now()
        elif not self._picked_selectors:
            self._auto_analyze_page()

    def _auto_analyze_page(self):
        """自动分析页面结构，生成规则"""
        self._auto_analyze_retries = 0
        self._run_auto_analyze()

    def _run_auto_analyze(self):
        js = """
(function() {
  function countLinks(doc, depth) {
    var total = 0;
    Array.from(doc.querySelectorAll('a[href]')).forEach(function(a) { total++; });
    var iframes = 0;
    Array.from(doc.querySelectorAll('iframe')).forEach(function(f) {
      iframes++;
      try { if (f.contentDocument) total += countLinks(f.contentDocument, depth+1); } catch(e) {}
    });
    return {total: total, iframes: iframes};
  }
  var mainCount = countLinks(document, 0);
  console.log('GetIv auto-analyze: mainLinks=' + mainCount.total + ' iframes=' + mainCount.iframes);
  function searchLinks(doc) {
    var all = [];
    var imgs = [];
    Array.from(doc.querySelectorAll('a[href]')).forEach(function(a) {
      var h = a.href.split('?')[0].split('#')[0];
      if (h && !h.endsWith('/')) all.push({href: h, text: (a.textContent||'').trim()});
    });
    Array.from(doc.querySelectorAll('img[src]')).forEach(function(img) {
      imgs.push({src: img.src, alt: (img.alt||'').trim()});
    });
    Array.from(doc.querySelectorAll('iframe')).forEach(function(f) {
      try { if (f.contentDocument) { var r = searchLinks(f.contentDocument); all = all.concat(r.all); imgs = imgs.concat(r.imgs); } } catch(e) {}
    });
    return {all: all, imgs: imgs};
  }
  var data = searchLinks(document);
  var groups = {};
  data.all.forEach(function(l) {
    var parts = l.href.split('/');
    var key = parts.slice(0, -1).join('/') + '/';
    if (!groups[key]) groups[key] = [];
    groups[key].push(l.href);
  });
  var best = {key: '', count: 0, samples: []};
  for (var k in groups) {
    if (groups[k].length > best.count) {
      best = {key: k, count: groups[k].length, samples: groups[k].slice(0, 3)};
    }
  }
  document.title = '__auto:' + encodeURIComponent(JSON.stringify({
    totalLinks: data.all.length,
    totalImgs: data.imgs.length,
    bestGroup: best
  }));
})();
"""
        self.browser_panel.webview.page().runJavaScript(js)
        # Retry after 3s for dynamic iframe content
        from PyQt5.QtCore import QTimer
        self._auto_analyze_retries = getattr(self, '_auto_analyze_retries', 0) + 1
        if self._auto_analyze_retries <= 2:
            QTimer.singleShot(3000, self._run_auto_analyze)

    def _delayed_crawl(self, ok):
        if ok and self._current_rule:
            self._run_crawl_now()
        # Disconnect after first fire to prevent stacking
        try:
            self.browser_panel.webview.page().loadFinished.disconnect(self._delayed_crawl)
        except TypeError:
            pass

    def _run_crawl_now(self):
        if not self._current_rule:
            return
        self.bottom_bar.log_message("开始分析页面...")
        from app.models import SelectorRule, SiteRule
        def sr(d):
            return SelectorRule(css=d.get("css", ""), attribute=d.get("attribute", "href"),
                                url_pattern=d.get("url_pattern", "")) if d else None
        r = self._current_rule
        rule = SiteRule(name=r["name"], url_pattern=r.get("url_pattern", ""),
                        page_list=sr(r["page_list"]), detail_images=sr(r["detail_images"]),
                        pagination=sr(r.get("pagination")), detail_videos=sr(r.get("detail_videos")),
                        next_button=sr(r.get("next_button")))
        self._crawler.extract_detail_links(rule)

    def _on_page_double_clicked(self, url: str):
        self.data_panel.clear_details()
        self._pending_media = []
        self.browser_panel.webview.page().loadFinished.connect(self._delayed_auto_analyze)
        self.browser_panel.navigate(url)
        self.bottom_bar.log_message(f"打开分页: {url}")

    def _on_detail_double_clicked(self, url: str):
        self.bottom_bar.log_message(f"分析详情: {url}")
        self.browser_panel.webview.page().loadFinished.connect(self._delayed_extract_media)
        self.browser_panel.navigate(url)

    def _delayed_extract_media(self, ok):
        try:
            self.browser_panel.webview.page().loadFinished.disconnect(self._delayed_extract_media)
        except TypeError:
            pass
        if not ok or not self._current_rule:
            return
        r = self._current_rule
        di = r.get("detail_images")
        dv = r.get("detail_videos")
        js = """
function searchDoc(doc, css, attr, type) {
  var r = [];
  doc.querySelectorAll(css).forEach(function(el) { r.push({url: el.getAttribute(attr)||el.src, type: type}); });
  doc.querySelectorAll("iframe").forEach(function(f) {
    try { if (f.contentDocument) r = r.concat(searchDoc(f.contentDocument, css, attr, type)); } catch(e) {}
  });
  return r;
}
var all = [];
"""
        if di:
            js += f"all = all.concat(searchDoc(document, {json.dumps(di['css'])}, {json.dumps(di['attribute'])}, 'image'));"
        if dv:
            js += f"all = all.concat(searchDoc(document, {json.dumps(dv['css'])}, {json.dumps(dv['attribute'])}, 'video'));"
        js += "document.title='__media:'+encodeURIComponent(JSON.stringify(all));"
        self.browser_panel.webview.page().runJavaScript(js)

    def _start_download(self):
        if self._pending_media:
            import os
            save_dir = self._config.get("save_path") or os.path.join(os.getcwd(), "downloads")
            self._downloader.start(self._pending_media, save_dir)
        else:
            self.bottom_bar.log_message("没有待下载的媒体文件，请先双击详情页分析")

    def _handle_auto_analyze(self, data):
        if self._current_rule:
            return  # Already have a rule, don't create duplicate
        try:
            best = data.get("bestGroup", {})
            samples = best.get("samples", [])
            if not samples:
                self.bottom_bar.log_message("自动分析: 未能检测到页面结构")
                return
            from urllib.parse import urlparse
            domain = urlparse(samples[0]).netloc or "unknown"
            import re
            # Generate URL pattern from sample
            sample = samples[0]
            pattern = re.sub(r"/\d+", r"/\\d+", sample)
            # Create rule
            from app.models import SelectorRule
            rule_data = {
                "name": domain,
                "url_pattern": "",
                "page_list": SelectorRule(css="", attribute="href", url_pattern=pattern),
                "detail_images": SelectorRule(css="img", attribute="src"),
                "pagination": None,
                "detail_videos": None,
                "next_button": None,
            }
            # Save rule
            import dataclasses
            rule_dict = {k: dataclasses.asdict(v) if hasattr(v, '__dataclass_fields__') else v for k, v in rule_data.items()}
            # Remove None values for optional fields
            rule_dict = {k: v for k, v in rule_dict.items() if v is not None}
            # Handle SiteRule required fields
            rule_dict["name"] = domain
            self._config["rules"].append(rule_dict)
            save_config(self._config)
            # Select the new rule
            self._current_rule = rule_dict
            self.data_panel.rule_selector.addItem(domain)
            self.data_panel.rule_selector.setCurrentIndex(self.data_panel.rule_selector.count() - 1)
            self.bottom_bar.log_message(f"自动分析: 检测到 {data.get('totalLinks',0)} 个链接，已创建规则「{domain}」")
            self.bottom_bar.log_message(f"URL模式: {pattern[:80]}")
            # Run crawl with the new rule
            self._run_crawl_now()
        except Exception as e:
            self.bottom_bar.log_message(f"自动分析失败: {e}")

    def _on_detail_links_found(self, links):
        for link in links:
            url = link.get("url") or ""
            text = link.get("text") or url
            if url:
                self.data_panel.add_detail_item(text, url)
        self.bottom_bar.log_message(f"找到 {sum(1 for l in links if l.get('url'))} 个详情链接")

    def _on_media_found(self, media):
        self._pending_media.extend(media)
        self.bottom_bar.set_pending_count(len(self._pending_media))
        self.bottom_bar.log_message(f"找到 {len(media)} 个媒体文件，累计 {len(self._pending_media)} 个")

    def _on_page_title_changed(self, title):
        if title.startswith("__media:"):
            try:
                data = json.loads(urllib.parse.unquote(title[8:]))
                if isinstance(data, list):
                    self._pending_media.extend(data)
                    self.bottom_bar.set_pending_count(len(self._pending_media))
                    self.bottom_bar.log_message(f"解析到 {len(data)} 个媒体文件，累计 {len(self._pending_media)} 个")
            except:
                pass
        elif title.startswith("__auto:"):
            try:
                data = json.loads(urllib.parse.unquote(title[7:]))
                self._handle_auto_analyze(data)
            except:
                pass

    def _on_links_found(self, links):
        for link in links:
            url = link.get("url") or ""
            text = link.get("text") or url
            if url:
                self.data_panel.add_page_item(text, url)
        self.bottom_bar.log_message(f"找到 {sum(1 for l in links if l.get('url'))} 个链接")

    def _on_download_progress(self, prog: DownloadProgress):
        self.bottom_bar.update_progress(prog.completed, prog.total_files)
        self.bottom_bar.log_message(f"下载: {prog.completed}/{prog.total_files}, 失败 {prog.failed}")
