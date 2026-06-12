from PyQt5.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget, QAction, QShortcut
from PyQt5.QtCore import QUrl, pyqtSignal
from PyQt5.QtGui import QKeySequence
import json, urllib.parse, os, threading
from app.gui.browser_panel import BrowserPanel
from app.gui.data_panel import DataPanel
from app.gui.bottom_bar import BottomBar
from app.gui.settings_dialog import SettingsDialog
from app.crawl_engine.crawler import Crawler
from app.download_engine.downloader import Downloader
from app.download_engine.m3u8_handler import M3U8Handler
from app.config import load_config, save_config
from app.models import SiteRule, SelectorRule, DownloadProgress
from app.util import safe_title, save_dir
from app.rule_builder.selector_picker import SelectorPicker
from app.rule_builder.type_selector_dialog import TypeSelectorDialog

class MainWindow(QMainWindow):
    _logSignal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GetIv - 网站媒体下载器")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)
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
        layout.addWidget(splitter, 1)
        self.bottom_bar = BottomBar()
        self._logSignal.connect(self.bottom_bar.log_message)
        layout.addWidget(self.bottom_bar, 0)
        self._crawler = Crawler(self.browser_panel.page())
        self._m3u8_handler = M3U8Handler(self._config.get("ffmpeg_path", "ffmpeg"),
                                         log_callback=lambda msg: self._threadsafe_log(msg),
                                         progress_callback=self._on_m3u8_progress)
        self._downloader = Downloader(self._config, m3u8_handler=self._m3u8_handler)
        self._selector_picker = SelectorPicker(self.browser_panel.page())
        self._pending_media = []
        self._load_rule_list()
        self._connect_signals()
        self.browser_panel.navigate("about:blank")

        # Tooltips
        self.data_panel.url_input.setToolTip("输入网址，Enter 或点击「分析」")
        self.data_panel.btn_analyze.setToolTip("分析当前页面 (Ctrl+Enter)")
        self.data_panel.btn_new_rule.setToolTip("创建新规则")
        self.browser_panel.btn_pick.setToolTip("开启/关闭点选模式")
        self.bottom_bar.btn_auto.setToolTip("自动遍历分页提取详情并下载")
        self.bottom_bar.btn_download.setToolTip("下载已提取的媒体文件")
        self.bottom_bar.btn_pause.setToolTip("暂停下载")
        self.bottom_bar.btn_cancel.setToolTip("取消下载")

        # Keyboard shortcuts
        self._setup_shortcuts()

    def _connect_signals(self):
        self.data_panel.urlSubmitted.connect(self._on_url_submitted)
        self.data_panel.btn_analyze.clicked.connect(self._on_analyze)
        self.data_panel.pageDoubleClicked.connect(self._on_page_double_clicked)
        self.data_panel.detailDoubleClicked.connect(self._on_detail_double_clicked)
        self._crawler.paginationFound.connect(self._on_pagination_found)
        self._crawler.linksFound.connect(self._on_detail_links_found)
        self._crawler.mediaFound.connect(self._on_media_found)
        self._downloader.progressUpdated.connect(self._on_download_progress)
        self._selector_picker.elementPicked.connect(self._on_element_picked)
        self.data_panel.btn_new_rule.clicked.connect(self._start_new_rule)
        self.browser_panel.btn_pick.clicked.connect(self._toggle_pick_mode)
        self.bottom_bar.downloadRequested.connect(self._start_download)
        self.bottom_bar.autoDownloadRequested.connect(self._start_auto_download)
        self.bottom_bar.autoPauseRequested.connect(self._toggle_auto_pause)
        self.bottom_bar.autoStopRequested.connect(self._stop_auto_download)
        self.bottom_bar.pauseRequested.connect(lambda: (self._downloader.pause(), self.bottom_bar.log_message("下载已暂停")))
        self.bottom_bar.cancelRequested.connect(lambda: (self._downloader.cancel(), self.bottom_bar.log_message("下载已取消")))
        self.browser_panel.webview.page().titleChanged.connect(self._on_page_title_changed)
        self.data_panel.clearPagesRequested.connect(self.data_panel.clear_pages)
        self.data_panel.clearDetailsRequested.connect(self.data_panel.clear_details)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Return"), self).activated.connect(
            lambda: self.data_panel.urlSubmitted.emit(self.data_panel.url_input.text()))
        QShortcut(QKeySequence("Ctrl+D"), self).activated.connect(self._start_download)
        QShortcut(QKeySequence("Ctrl+Shift+A"), self).activated.connect(self._start_auto_download)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(self._stop_auto_download)
        QShortcut(QKeySequence("F5"), self).activated.connect(
            lambda: self.browser_panel.webview.reload())

    def _disconnect_load(self, handler):
        try:
            self.browser_panel.webview.page().loadFinished.disconnect(handler)
        except TypeError:
            pass

    def _reset_state(self):
        self.data_panel.clear_pages()
        self.data_panel.clear_details()
        self._pending_media = []
        self.bottom_bar.set_pending_count(0)

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
        self._reset_state()
        self.browser_panel.webview.page().loadFinished.connect(self._delayed_auto_analyze)
        self.browser_panel.navigate(url)
        self.bottom_bar.log_message(f"导航到: {url}")

    def _resolve_url(self, url: str) -> str:
        if url.startswith(("http://", "https://")):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            page = self.browser_panel.webview.url().toString()
            parsed = urllib.parse.urlparse(page)
            return f"{parsed.scheme}://{parsed.netloc}{url}"
        return url

    def _on_analyze(self):
        url = self.data_panel.url_input.text().strip()
        if url:
            self._reset_state()
            self.browser_panel.webview.page().loadFinished.connect(self._delayed_auto_analyze)
            self.browser_panel.navigate(url)
            self.bottom_bar.log_message(f"导航到: {url}")
        elif self._current_rule:
            self._run_crawl_detail()

    def _delayed_auto_analyze(self, ok):
        self._disconnect_load(self._delayed_auto_analyze)
        if not ok:
            return
        if self._current_rule:
            self._run_crawl_all()

    def _run_crawl_all(self):
        """只提取分页链接（→上表），不提取详情"""
        if not self._current_rule:
            return
        rule = SiteRule.from_config(self._current_rule)
        if rule.pagination:
            self.bottom_bar.log_message("提取分页链接...")
            self._crawler.extract_pagination(rule)
        else:
            self.bottom_bar.log_message("没有分页规则，尝试提取详情链接...")
            self._crawler.extract_detail_links(rule)

    def _run_crawl_detail(self):
        """只提取详情链接（→下表），双击分页时用"""
        if not self._current_rule:
            return
        rule = SiteRule.from_config(self._current_rule)
        self.bottom_bar.log_message("提取详情链接...")
        self._crawler.extract_detail_links(rule)

    def _on_page_double_clicked(self, url: str):
        self.data_panel.clear_details()
        self._pending_media = []
        self.browser_panel.webview.page().loadFinished.connect(self._delayed_crawl_detail)
        self.browser_panel.navigate(url)
        self.bottom_bar.log_message(f"打开分页: {url}")

    def _delayed_crawl_detail(self, ok):
        self._disconnect_load(self._delayed_crawl_detail)
        if ok and self._current_rule:
            self._run_crawl_detail()

    def _threadsafe_log(self, msg):
        self._logSignal.emit(msg)

    def _on_detail_double_clicked(self, url: str):
        self.bottom_bar.log_message(f"分析详情: {url}")
        self._pending_media = []
        self.bottom_bar.set_pending_count(0)
        self.browser_panel.webview.page().loadFinished.connect(self._delayed_extract_media)
        self.browser_panel.navigate(url)

    def _delayed_extract_media(self, ok):
        self._disconnect_load(self._delayed_extract_media)
        if not ok or not self._current_rule:
            self.bottom_bar.log_message("提取跳过: 页面加载失败或无规则")
            return
        self.bottom_bar.log_message("提取媒体文件...")
        r = self._current_rule
        di = r.get("detail_images")
        dv = r.get("detail_videos")
        self.bottom_bar.log_message(f"规则: 图片CSS={di.get('css','无') if di else '无'}, 视频CSS={dv.get('css','无') if dv else '无'}")
        # Get page title
        self.browser_panel.webview.page().runJavaScript("document.title", self._on_got_title_for_dl)

    def _on_got_title_for_dl(self, title):
        self._current_page_title = safe_title(title)
        self.bottom_bar.log_message(f"页面标题: {self._current_page_title}")
        r = self._current_rule
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self._media_extract(r.get("detail_images"), r.get("detail_videos")))

    def _media_extract(self, di, dv):
        self.bottom_bar.log_message("提取媒体...")
        js = """
(function() {
  var all = [];
  function add(u, t) { if (u && u.trim()) all.push({url: u.trim(), type: t}); }
  // Search entire page for m3u8 URLs
  try {
    var re = /https?:\\/\\/[^\\s'\"<>\\\\]+\\.m3u8/g;
    var text = document.documentElement.outerHTML;
    var m;
    while ((m = re.exec(text)) !== null) {
      add(m[0], 'video');
    }
  } catch(e) {}
"""
        if di:
            js += f"try{{Array.from(document.querySelectorAll({json.dumps(di['css'])})).forEach(function(el){{var u=el.getAttribute({json.dumps(di['attribute'])})||el.src||'';if(u)all.push({{url:u,type:'image'}});}});}}catch(e){{}}"
        if dv:
            js += f"try{{Array.from(document.querySelectorAll({json.dumps(dv['css'])})).forEach(function(el){{var u=el.getAttribute({json.dumps(dv['attribute'])})||el.src||'';if(u)all.push({{url:u,type:'video'}});}});}}catch(e){{}}"
        js += """
  try { Array.from(document.querySelectorAll('iframe')).forEach(function(f) {
    try { if (f.contentDocument) {
"""
        if di:
            js += f"Array.from(f.contentDocument.querySelectorAll({json.dumps(di['css'])})).forEach(function(el){{var u=el.getAttribute({json.dumps(di['attribute'])})||el.src||'';if(u)all.push({{url:u,type:'image'}});}});"
        if dv:
            js += f"Array.from(f.contentDocument.querySelectorAll({json.dumps(dv['css'])})).forEach(function(el){{var u=el.getAttribute({json.dumps(dv['attribute'])})||el.src||'';if(u)all.push({{url:u,type:'video'}});}});"
        js += """
      // Search iframe content for m3u8
      var re = /https?:\\/\\/[^\\s'\"<>\\\\]+\\.m3u8/g;
      var text = f.contentDocument.documentElement.outerHTML;
      var m;
      while ((m = re.exec(text)) !== null) {
        if (all.every(function(item) { return item.url !== m[0]; })) add(m[0], 'video');
      }
    }} catch(e) {}
  }); } catch(e) {}
  return JSON.stringify({count: all.length, all: all});
})();
"""
        self.browser_panel.webview.page().runJavaScript(js, lambda result: self._on_media_result(result))

    def _on_media_result(self, result):
        try:
            import json as j
            data = j.loads(result) if isinstance(result, str) else result
            all_items = data.get("all", [])
            self.bottom_bar.log_message(f"JS返回: {len(all_items)} 个媒体文件")
            m3u8_items = [item for item in all_items if '.m3u8' in item.get("url","").lower()]
            if m3u8_items:
                self.bottom_bar.log_message(f"发现 {len(m3u8_items)} 个M3U8视频，开始下载转换...")
                title = getattr(self, '_current_page_title', f"video_{len(m3u8_items)}")
                base = save_dir(self._config)
                folder = os.path.join(base, title)
                os.makedirs(folder, exist_ok=True)
                for i, item in enumerate(m3u8_items):
                    url = item.get("url","")
                    if url:
                        task_id = f"m3u8_{id(url)}"
                        self.data_panel.add_m3u8_task(task_id, title)
                        self.bottom_bar.log_message(f"下载M3U8: {url[:60]}")
                        import threading
                        threading.Thread(target=self._download_m3u8, args=(url, title, folder, task_id), daemon=True).start()
            if all_items:
                self._pending_media = [item for item in all_items if '.m3u8' not in item.get("url","").lower()]
                self.bottom_bar.set_pending_count(len(self._pending_media))
                types = {}
                for item in all_items:
                    t = item.get("type", "image")
                    types[t] = types.get(t, 0) + 1
                    try:
                        self.data_panel.add_media_item(t, item.get("url",""))
                    except Exception as e2:
                        self.bottom_bar.log_message(f"添加媒体失败: {e2}")
                self.bottom_bar.log_message(f"分类: {types}")
        except Exception as e:
            self.bottom_bar.log_message(f"JS结果解析错误: {e}")

    def _download_m3u8(self, url, title, folder, task_id=""):
        try:
            self._m3u8_handler.download_and_convert(url, os.path.join(folder, f"{title}.mp4"), task_id=task_id)
            self._logSignal.emit(f"M3U8完成: {title}")
        except Exception as e:
            self._logSignal.emit(f"M3U8失败: {e}")

    def _on_m3u8_progress(self, task_id, stage, ts_total=0, ts_done=0, detail=""):
        if stage == "parsing":
            self.data_panel.update_m3u8_task(task_id, "解析", detail or f"共 {ts_total} 个TS")
        elif stage == "downloading":
            pct = f"{ts_done}/{ts_total}" if ts_total else ""
            self.data_panel.update_m3u8_task(task_id, f"下载 {pct}", detail)
        elif stage == "converting":
            self.data_panel.update_m3u8_task(task_id, "合成MP4", detail)
        elif stage == "done":
            self.data_panel.update_m3u8_task(task_id, "完成", detail or "完成")
        elif stage == "error":
            self.data_panel.update_m3u8_task(task_id, "失败", detail)

    def _start_download(self):
        if self._downloader.is_paused:
            self._downloader.resume()
            self.bottom_bar.log_message("下载已恢复")
            return
        if self._downloader.is_running:
            self.bottom_bar.log_message("下载正在进行中")
            return
        if self._pending_media:
            import threading
            threading.Thread(target=self._downloader.start, args=(self._pending_media, save_dir(self._config)), daemon=True).start()
        else:
            self.bottom_bar.log_message("没有待下载的媒体文件，请先双击详情页分析")

    def _start_auto_download(self):
        pages = []
        for i in range(self.data_panel.page_list.count()):
            url = self.data_panel.page_list.item(i).data(256)
            if url:
                pages.append(url)
        if not pages:
            self.bottom_bar.log_message("分页列表为空，请先分析")
            return
        self._auto_paused = False
        self._auto_stopped = False
        self._auto_page_idx = 0
        self._auto_pages = pages
        self._auto_collecting = True
        self._auto_all_details = []  # Collect all detail URLs in phase 1
        self._auto_detail_idx = 0
        self._auto_save_base = save_dir(self._config)
        self.data_panel.clear_details()
        self.bottom_bar.log_message(f"阶段1/2: 遍历 {len(pages)} 个分页收集详情...")
        self._auto_page_collect()

    def _auto_page_collect(self):
        if getattr(self, '_auto_stopped', False): return self._auto_finish("已停止")
        if getattr(self, '_auto_paused', False): return self._auto_retry(self._auto_page_collect)
        if getattr(self, '_auto_finished', False): return
        if self._auto_page_idx >= len(self._auto_pages):
            total = len(self._auto_all_details)
            self._auto_collecting = False
            self.bottom_bar.log_message(f"阶段1完成: 收集到 {total} 个详情链接")
            if total == 0:
                return self._auto_finish("无详情链接")
            self.bottom_bar.log_message("阶段2/2: 开始下载...")
            self._auto_detail_idx = 0
            self.bottom_bar.update_progress(0, total)
            return self._auto_retry(self._auto_download_next)
        url = self._auto_pages[self._auto_page_idx]
        self.bottom_bar.log_message(f"收集分页 [{self._auto_page_idx+1}/{len(self._auto_pages)}]")
        self.browser_panel.webview.page().loadFinished.connect(self._auto_on_collect_loaded)
        self.browser_panel.navigate(url)

    def _auto_on_collect_loaded(self, ok):
        self._disconnect_load(self._auto_on_collect_loaded)
        if getattr(self, '_auto_stopped', False): return
        if getattr(self, '_auto_paused', False): return self._auto_retry(lambda: self._auto_on_collect_loaded(False))
        if not ok:
            self._auto_page_idx += 1
            return self._auto_retry(self._auto_page_collect)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1500, self._auto_extract_and_store)

    def _auto_extract_and_store(self):
        if getattr(self, '_auto_stopped', False): return
        if getattr(self, '_auto_paused', False): return self._auto_retry(self._auto_extract_and_store)
        if not getattr(self, '_current_rule', None):
            self._auto_page_idx += 1
            return self._auto_retry(self._auto_page_collect)
        rule = SiteRule.from_config(self._current_rule)
        self._crawler.extract_detail_links(rule)

    def _on_detail_links_found(self, links):
        for link in links:
            url = self._resolve_url(link.get("url") or "")
            text = link.get("text") or url
            if url:
                self.data_panel.add_detail_item(text, url)
        self.bottom_bar.log_message(f"找到 {len(links)} 个详情链接")
        if getattr(self, '_auto_collecting', False):
            if getattr(self, '_auto_paused', False): return
            for l in links:
                u = self._resolve_url(l.get("url",""))
                if u: self._auto_all_details.append(u)
            self._auto_page_idx += 1
            self._auto_retry(self._auto_page_collect)

    def _auto_download_next(self):
        """Phase 2: Download each detail page"""
        if getattr(self, '_auto_stopped', False): return self._auto_finish("已停止")
        if getattr(self, '_auto_paused', False): return self._auto_retry(self._auto_download_next)
        if getattr(self, '_auto_finished', False): return
        if self._auto_detail_idx >= len(self._auto_all_details):
            self._auto_finished = True
            return self._auto_finish("全部完成")
        url = self._auto_all_details[self._auto_detail_idx]
        self.bottom_bar.log_message(f"下载 [{self._auto_detail_idx+1}/{len(self._auto_all_details)}]")
        self.browser_panel.webview.page().loadFinished.connect(self._auto_on_dl_loaded)
        self.browser_panel.navigate(url)

    def _auto_on_dl_loaded(self, ok):
        self._disconnect_load(self._auto_on_dl_loaded)
        if getattr(self, '_auto_stopped', False): return
        if getattr(self, '_auto_paused', False): return self._auto_retry(lambda: self._auto_on_dl_loaded(False))
        if not ok:
            self._auto_detail_idx += 1
            return self._auto_retry(self._auto_download_next)
        self.browser_panel.webview.page().runJavaScript("document.title", self._auto_on_got_title)

    def _auto_on_got_title(self, title):
        if getattr(self, '_auto_stopped', False): return
        if getattr(self, '_auto_paused', False): return self._auto_retry(lambda: self._auto_on_got_title(title))
        self._auto_cur_title = safe_title(title)
        self.bottom_bar.log_message(f"标题: {self._auto_cur_title}")
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1500, self._auto_extract_media)

    def _auto_extract_media(self):
        if getattr(self, '_auto_stopped', False): return
        if getattr(self, '_auto_paused', False): return self._auto_retry(self._auto_extract_media)
        if not getattr(self, '_current_rule', None):
            return self._auto_retry(self._auto_download_next)
        r = self._current_rule
        di = r.get("detail_images")
        if not di:
            self._auto_detail_idx += 1
            return self._auto_retry(self._auto_download_next)
        css = di.get("css","img"); attr = di.get("attribute","src")
        js = f"""
(function() {{
  function sd(d) {{
    var r = [];
    Array.from(d.querySelectorAll({json.dumps(css)})).forEach(function(el) {{
      var u = el.getAttribute({json.dumps(attr)}) || el.src || '';
      if (u) r.push(u);
    }});
    Array.from(d.querySelectorAll('iframe')).forEach(function(f) {{
      try {{ if (f.contentDocument) r = r.concat(sd(f.contentDocument)); }} catch(e) {{}}
    }});
    return r;
  }}
  var urls = sd(document);
  document.title = '__autodl:' + encodeURIComponent(JSON.stringify({{urls: urls, idx: {self._auto_detail_idx}}}));
}})();
"""
        self.browser_panel.webview.page().runJavaScript(js)

    def _auto_finish(self, msg):
        self.bottom_bar.log_message(f"自动下载: {msg}")
        self.bottom_bar.update_progress(0, 1)

    def _auto_retry(self, fn):
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(500, fn)

    def _toggle_auto_pause(self):
        self._auto_paused = not getattr(self, '_auto_paused', False)
        is_paused = self._auto_paused
        self.bottom_bar.btn_auto_pause.setText("恢复自动" if is_paused else "暂停自动")
        self.bottom_bar.log_message("已暂停" if is_paused else "已恢复")
        if not is_paused:
            in_phase1 = hasattr(self, '_auto_all_details') and self._auto_detail_idx == 0
            in_phase2 = hasattr(self, '_auto_all_details') and self._auto_detail_idx < len(self._auto_all_details)
            if in_phase1:
                self._auto_retry(self._auto_page_collect)
            elif in_phase2:
                self._auto_retry(self._auto_download_next)

    def _stop_auto_download(self):
        self._auto_stopped = True
        self._auto_finish("已停止")

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
            self._run_crawl_all()
        except Exception as e:
            self.bottom_bar.log_message(f"自动分析失败: {e}")

    def _on_pagination_found(self, links):
        for link in links:
            url = self._resolve_url(link.get("url") or "")
            text = link.get("text") or url
            if url:
                self.data_panel.add_page_item(text, url)
        self.bottom_bar.log_message(f"分页: 找到 {sum(1 for l in links if l.get('url'))} 个分页链接")

    def _on_media_found(self, media):
        self._pending_media.extend(media)
        self.bottom_bar.set_pending_count(len(self._pending_media))
        self.bottom_bar.log_message(f"找到 {len(media)} 个媒体文件，累计 {len(self._pending_media)} 个")
        for m in media:
            url = m.get("url", "")
            t = m.get("type", "image")
            if url:
                self.data_panel.add_media_item(t, url)

    def _on_page_title_changed(self, title):
        if title.startswith("__auto:"):
            try:
                data = json.loads(urllib.parse.unquote(title[7:]))
                self._handle_auto_analyze(data)
            except Exception as e:
                self.bottom_bar.log_message(f"__auto解析错误: {e}")
        elif title.startswith("__autodl:"):
            try:
                data = json.loads(urllib.parse.unquote(title[9:]))
                urls = data.get("urls", [])
                idx = data.get("idx", 0)
                if urls and hasattr(self, '_auto_cur_title') and hasattr(self, '_auto_save_base'):
                    folder = os.path.join(self._auto_save_base, self._auto_cur_title)
                    self.bottom_bar.log_message(f"下载 {len(urls)} 个文件到 {self._auto_cur_title}")
                    import threading
                    threading.Thread(target=self._downloader.start, args=([{"url": u, "type": "image"} for u in urls], folder), daemon=True).start()
                self._auto_detail_idx = idx + 1
                self.bottom_bar.update_progress(self._auto_detail_idx, len(self._auto_all_details))
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(500, self._auto_download_next)
            except:
                pass

    def _on_download_progress(self, prog: DownloadProgress):
        self.bottom_bar.update_progress(prog.completed, prog.total_files)
        self.bottom_bar.log_message(f"下载: {prog.completed}/{prog.total_files}, 失败 {prog.failed}")
