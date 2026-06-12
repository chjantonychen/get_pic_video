from PyQt5.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget, QAction
from PyQt5.QtCore import QUrl
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
        self._load_rule_list()
        self.data_panel.urlSubmitted.connect(self._on_url_submitted)
        self.data_panel.pageDoubleClicked.connect(self._on_page_double_clicked)
        self.data_panel.detailDoubleClicked.connect(self._on_detail_double_clicked)
        self._crawler.linksFound.connect(self._on_links_found)
        self._crawler.mediaFound.connect(self._on_media_found)
        self._downloader.progressUpdated.connect(self._on_download_progress)
        self._selector_picker.elementPicked.connect(self._on_element_picked)
        self.data_panel.btn_new_rule.clicked.connect(self._start_new_rule)
        self.browser_panel.btn_pick.clicked.connect(self._toggle_pick_mode)
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
                kwargs[field] = SelectorRule(css=picks[0]["css"], attribute=picks[0]["attribute"])
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

    def _on_element_picked(self, selector: str):
        dlg = TypeSelectorDialog(selector, self)
        if dlg.exec_() and dlg.selected_type:
            t = dlg.selected_type
            attr = dlg.selected_attribute or "src"
            self.bottom_bar.log_message(f"已标注 [{t}]: {selector} (attr={attr})")
            if t not in self._picked_selectors:
                self._picked_selectors[t] = []
            self._picked_selectors[t].append({"css": selector, "attribute": attr})
            self._selector_picker.validate_selector(selector,
                lambda count: self.bottom_bar.log_message(f"选择器匹配到 {count} 个元素"))
        else:
            self.bottom_bar.log_message("元素标注取消")

    def _on_url_submitted(self, url: str):
        self.data_panel.clear_pages()
        self.browser_panel.navigate(url)
        self.bottom_bar.log_message(f"导航到: {url}")

    def _on_page_double_clicked(self, url: str):
        self.data_panel.clear_details()
        self.browser_panel.navigate(url)
        self.bottom_bar.log_message(f"打开分页: {url}")

    def _on_detail_double_clicked(self, url: str):
        self.bottom_bar.log_message(f"分析详情: {url}")

    def _on_links_found(self, links):
        for link in links:
            self.data_panel.add_page_item(link.get("text", link["url"]), link["url"])
        self.bottom_bar.log_message(f"找到 {len(links)} 个链接")

    def _on_media_found(self, media):
        self.bottom_bar.log_message(f"找到 {len(media)} 个媒体文件")

    def _on_download_progress(self, prog: DownloadProgress):
        self.bottom_bar.update_progress(prog.completed, prog.total_files)
        self.bottom_bar.log_message(f"下载: {prog.completed}/{prog.total_files}, 失败 {prog.failed}")
