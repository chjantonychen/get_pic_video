# 通用网站媒体下载器 — 设计文档

## 概述

PyQt5 图形界面程序，通过可视化点选定义爬取规则，从任意网站逐层提取图片和视频并下载。视频支持 m3u8 → mp4 自动转换。三层结构：网址 → 分页/列表 → 详情页 → 媒体资源。

## 技术栈

| 组件 | 选型 | 原因 |
|------|------|------|
| GUI 框架 | PyQt5 | 内置 Qt WebEngine，支持嵌入式浏览器 |
| 浏览器引擎 | Qt WebEngine (Chromium) | 渲染 JS 页面、支持可视化点选、天然反爬 |
| 爬取方式 | 通过 `runJavaScript()` 注入 JS 操作 DOM | 无需 Session 同步，复用浏览器 Cookie |
| 下载并行 | `concurrent.futures.ThreadPoolExecutor` | 多线程 HTTP 下载 |
| 视频转换 | `subprocess` + ffmpeg | m3u8 → mp4 转封装 |
| 规则存储 | JSON | 简单、可导出/导入、人类可读 |

## 架构

```
┌──────────────────────────────────────────────────┐
│                  App (QApplication)               │
├──────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌────────────┐  ┌───────────┐  │
│  │  规则构建器    │  │  爬取引擎   │  │  下载引擎  │  │
│  │  (WebEngine) │→│  (JS注入)   │→│  (线程池)  │  │
│  └─────────────┘  └────────────┘  └───────────┘  │
│  ┌──────────────────────────────────────────┐     │
│  │           规则存储 (JSON)                  │     │
│  └──────────────────────────────────────────┘     │
│  ┌──────────────────────────────────────────┐     │
│  │            GUI 界面 (PyQt5)               │     │
│  └──────────────────────────────────────────┘     │
└──────────────────────────────────────────────────┘
```

### 模块职责

- **规则构建器** — 内嵌 Chromium 浏览器，用户通过鼠标点选页面元素，程序自动生成 CSS Selector。支持悬停高亮、类型标注、验证。
- **爬取引擎** — 通过 QWebEnginePage 加载目标页面，注入 JavaScript 提取 DOM 中的链接和媒体 URL。自动处理翻页、懒加载。
- **下载引擎** — 基于线程池的并发下载器，支持断点续传、URL 去重、失败重试（指数退避）、可选限速。m3u8 视频自动下载所有分段、调用 ffmpeg 合成为 mp4、清理临时文件。
- **规则存储** — 以 JSON 序列化整套规则（选择器、属性、反爬配置），按域名管理，支持导入导出。

### 模块间接口

```
规则构建器 ──emit(SiteRule)──▶ 规则存储 ──load(SiteRule)──▶ 爬取引擎
爬取引擎   ──emit(CrawlResult)──▶ 下载引擎
爬取引擎   ──emit(ProgressUpdate)──▶ GUI (信号)
下载引擎   ──emit(DownloadProgress)──▶ GUI (信号)
GUI       ──slot(onUrlInput)──▶ 爬取引擎 (调用方法)
```

**数据契约：**

| 接口 | 方向 | 数据结构 | 机制 |
|------|------|---------|------|
| 规则构建器 → 规则存储 | 输出 | `SiteRule` | 直接调用 `save(rule)` |
| 规则存储 → 爬取引擎 | 输入 | `SiteRule` | 直接调用 `load(name)` 返回 |
| 爬取引擎 → 下载引擎 | 输出 | `CrawlResult{page_url, detail_urls, media_urls}` | `queue.Queue` (跨线程) |
| 爬取引擎 → GUI | 更新 | `dict{stage, count, status}` | `QtCore.pyqtSignal` |
| 下载引擎 → GUI | 更新 | `DownloadProgress` | `QtCore.pyqtSignal` |

**线程边界：** 爬取引擎在 GUI 线程中调用 `runJavaScript()`，结果通过 `pyqtSignal` 回调。下载引擎在独立线程池运行，进度通过线程安全 `queue.Queue` + `QTimer.poll()` 或 `pyqtSignal` 回灌。

### WebEngine 实例策略

整个应用共享**一个** `QWebEnginePage` 实例。规则构建器和爬取引擎共用同一个浏览器面板中的页面：
- 构建规则时：用户点选操作
- 爬取时：程序导航到目标 URL，注入 JS 提取数据
- 切换时 `page.runJavaScript()` 的上下文自动跟随当前 URL
- 无需两个实例，避免内存翻倍和 Cookie/Session 不同步

## 可视化规则构建器

### 用户流程

1. 输入 URL，嵌入式浏览器加载页面
2. 开启"点选模式"
3. 鼠标悬停时元素高亮（蓝色 outline）
4. 点击元素，弹出菜单选择类型：`分页链接` / `详情链接` / `图片容器` / `视频容器` / `下一页按钮`
5. 程序自动提取当前元素的唯一 CSS Selector：
   - 优先使用 ID
   - 其次 class + nth-child 组合
   - 最后父链定位
6. 同一类型可多次选中，程序尝试归纳为通用规则
7. 规则生成后自动注入 JS 验证：匹配到的元素用绿框标记

### 规则数据模型

```python
@dataclass
class SiteRule:
    name: str
    url_pattern: str
    pagination: Optional[SelectorRule] = None  # 部分网站无分页
    page_list: SelectorRule
    detail_images: SelectorRule
    detail_videos: Optional[SelectorRule] = None  # 部分页面无视频
    next_button: Optional[SelectorRule] = None  # URL模板翻页时无需
    anti_crawl: AntiCrawlConfig = field(default_factory=AntiCrawlConfig)

@dataclass
class SelectorRule:
    css: str
    attribute: str              # src / href / data-src
    wait_selector: str = ""     # 懒加载: 等待此选择器出现
    lazy_scroll: bool = False   # 懒加载: 提取前是否滚动到底部

@dataclass
class CrawlResult:
    """爬取引擎输出给下载引擎的数据"""
    source_url: str
    page_title: str
    detail_urls: list[str]
    media_urls: list[dict]  # [{"url": "...", "type": "image|video", "alt": ""}]

@dataclass
class DownloadProgress:
    total_files: int
    completed: int
    failed: int
    current_file: str
    bytes_downloaded: int
    total_bytes: int
    speed: float  # KB/s

@dataclass
class AntiCrawlConfig:
    delay_range: tuple = (1, 3)   # 请求间隔 (秒)
    use_proxy: bool = False
    proxy_list: Optional[list[str]] = None  # 格式: "http://user:pass@host:port"
    random_user_agent: bool = True
```

## GUI 界面

### 布局

三区域布局：

```
┌──────────────────────────────────────────────┐
│ 菜单栏: 文件 | 规则 | 工具 | 帮助            │
├──────────────────┬───────────────────────────┤
│                  │  控制区                    │
│  浏览器面板      │  [URL输入] [分析]          │
│  (可调宽度)      │  [规则选择▼] [新建规则]    │
│                  │  ┌─ 分页列表 ───────┐     │
│                  │  │ page 1 ▶ 45 links│     │
│                  │  │ page 2 ▶ 42 links│     │
│                  │  └──────────────────┘     │
│                  │  ┌─ 详情列表 ───────┐     │
│                  │  │ item A ▶ 5img    │     │
│                  │  │ item B ▶ 3img+1v │     │
│                  │  └──────────────────┘     │
├──────────────────┴───────────────────────────┤
│ [进度条] download 12/35  [暂停] [取消]        │
│ [日志] INFO: page 3 scanned, 38 items found   │
└──────────────────────────────────────────────┘
```

### 菜单功能

| 菜单 | 条目 |
|------|------|
| 文件 | 导入规则、导出规则、退出 |
| 规则 | 新建规则、编辑当前规则、删除规则 |
| 工具 | 设置、清除已下载列表 |
| 帮助 | 关于 |

### 设置对话框

通过菜单 `工具 → 设置` 打开，包含：

| 分组 | 配置项 |
|------|--------|
| 下载 | 线程数 (1-50)、默认保存路径、限速 (MB/s)、断点续传开关、ffmpeg 路径 |
| 反爬 | 请求延迟范围 (秒)、随机 UA 开关、代理列表 (每行一个) |
| 浏览器 | 页面加载超时 (秒)、JS 注入重试次数、禁用图片加载 (加快爬取) |

配置持久化到 `config.json`（应用同级目录）。

### 两阶段工作流

规则构建与爬取下载是两个**串行阶段**，共用一个浏览器实例：

```
阶段一 (规则构建): 浏览页面 → 点选元素 → 保存规则 (JSON)
                      ↓
阶段二 (爬取下载): 加载已保存规则 → URL输入 → 三层遍历 → 下载
```

用户也可以在阶段二随时切换回阶段一（点击"编辑规则"），此时浏览器保持当前页面状态。

### 交互流程

阶段二的具体操作：

| 步 | 用户操作 | 程序行为 |
|----|---------|---------|
| 1 | 选择已有规则 → 输入 URL → 点击"分析" | 浏览器加载 → 注入 `extractLinks` → 填充分页列表 |
| 2 | 双击某分页 | 浏览器导航到该页 → 提取详情链接 → 填充详情列表 |
| 3 | 选中详情 → 下载 | 遍历选中的详情页 → 提取媒体 URL → 启动线程池 |
| 可选 | "下载全部" | 遍历全部分页 → 全部详情 → 全部资源 |

## 线程安全设计

由于 Qt WebEngine 的 DOM 操作必须在 GUI 线程执行，而下载在后台线程池运行：

- **爬取引擎** — 运行在 GUI 线程，通过 `QWebEnginePage.runJavaScript()` 的回调获取数据，用 `pyqtSignal` 发射结果（信号是线程安全的）
- **下载引擎** — 运行在 `ThreadPoolExecutor` 后台线程，进度更新通过 `pyqtSignal`（需确保信号连接在注册时使用 `Qt.AutoConnection`，或下载开始时将信号提升为跨线程安全）
- **数据传递** — 爬取引擎→下载引擎：通过 `queue.Queue` 传递 URL 列表。`queue.Queue` 是线程安全的，无需额外锁
- **UI 更新** — 所有 UI 交互（列表追加、进度更新、日志输出）通过 `pyqtSignal` 回到 GUI 线程执行，禁止在后台线程直接操作 QWidget

## 爬取引擎（JS 注入）

### 核心注入脚本

```javascript
// 提取链接
function extractLinks(selector, attribute) {
  const els = document.querySelectorAll(selector);
  return Array.from(els).map(el => ({
    url: el.getAttribute(attribute) || el.href || el.src,
    text: el.textContent.trim().slice(0, 100)
  }));
}

// 提取媒体
function extractMedia(selectors) {
  const results = {};
  for (const [type, sel] of Object.entries(selectors)) {
    results[type] = Array.from(document.querySelectorAll(sel.css))
      .map(el => ({
        url: el.getAttribute(sel.attr) || el.src,
        type: type
      }));
  }
  return results;
}

// 获取总页数
function extractTotalPages(selector) {
  const links = document.querySelectorAll(selector);
  const nums = Array.from(links)
    .map(el => {
      // 优先使用 data-page 属性，其次文本
      const val = el.getAttribute('data-page') || el.textContent;
      return parseInt(val, 10);
    })
    .filter(n => Number.isInteger(n) && n > 0);
  return nums.length ? Math.max(...nums) : null;
}
```

### 懒加载处理

- 规则中可指定 `attribute: "data-src"` 替代默认 `src`
- 可选自动滚动：`window.scrollTo(0, document.body.scrollHeight)` 触发懒加载
- 可选等待选择器出现后提取

### 翻页模式

支持两种翻页策略：
1. **URL 模板** — `page=1`、`page=2` 模式，直接构造 URL
2. **点击"下一页"** — 找到 `next_button` 选择器对应的元素，执行 `.click()`，等待新内容加载

## 下载引擎

### 配置

- 线程数：默认 10，用户可调
- 重试：最多 3 次，指数退避（1s → 3s → 9s）
- 路径：`下载目录/网站名/详情标题/文件`
- 文件名 sanitize：过滤 `<>:"/\|?*` 等 Windows 非法字符，替换为 `_`
- 同名冲突：如果同一详情页有同名文件，追加递增数字后缀（`image.jpg` → `image_1.jpg`）
- URL 去重：基于 URL 字符串

### m3u8 视频处理

检测到 URL 以 `.m3u8` 结尾时，走视频专用流程：

1. **下载 m3u8 索引** — 获取主播放列表，解析出各分段 `.ts` 地址
2. **下载所有 .ts 分段** — 并行下载（使用下载线程池），写入临时目录
3. **拼接为 mp4** — 调用 ffmpeg 执行 `ffmpeg -i "concat:ts1.ts|ts2.ts|..." -c copy output.mp4`
4. **清理临时文件** — 删除所有 `.ts` 分段和 `.m3u8` 索引文件，仅保留最终 `.mp4`
5. **进度报告** — 分段下载进度 + ffmpeg 转码进度分别汇报

**ffmpeg 检测** — 启动时检查系统 PATH 中是否有 ffmpeg，若无则提示用户指定路径。Windows 下可自动扫描常见安装路径（`C:\ffmpeg\bin\ffmpeg.exe`、`C:\Program Files\ffmpeg\bin\ffmpeg.exe`）。

### 反爬

- WebEngine 本身就是真实浏览器指纹，无需额外伪装
- 请求间隔随机延迟（1-3 秒可配）
- 可选代理轮换
- User-Agent 随机切换
- Cookie 自动保持

## 错误处理

- **规则匹配不到元素** — 提示用户检查选择器，高亮当前页面所有可交互元素帮助诊断
- **JS 注入失败 / 返回空值** — 重试 3 次，每次增加 2 秒等待（页面可能未完全渲染）。3 次后提示用户切换规则或手动检查页面
- **CSP 阻止注入** — 检测 `runJavaScript` 回调超时或报错，尝试通过注入 `<script>` 标签绕过
- **网页导航超时** — 设置 30 秒超时，超时后检查 `isLoading()` 状态，若卡住则 `stop()` + 重试
- **网络错误** — 自动重试，3 次失败后跳过并记录
- **下载失败** — 跳过该文件，继续队列，最终汇总失败列表
- **ffmpeg 未找到** — 启动时检测，缺失则弹窗引导用户下载或指定路径
- **m3u8 解析失败** — 无法解析索引文件时输出错误日志，跳过该视频
- **ffmpeg 转码失败** — 保留临时 .ts 文件，提示用户手动处理
- **.ts 分段下载超时** — 单个分段超时 30 秒则跳过该视频，保留已下载的分段
- **浏览器崩溃** — 重启 WebEngine，保留已爬取的数据
- **应用退出（未完成下载）** — 弹出确认对话框："下载尚未完成，确定退出？"，选"确定"则终止所有线程后退出；选"取消"则继续下载

## 测试策略

- **框架** — `pytest` + `pytest-qt`（Qt 信号测试）
- **单元测试** — 选择器生成逻辑（元素路径→CSS）、`SiteRule` 序列化/反序列化
- **爬取引擎** — 使用 `QWebEnginePage.setHtml()` 加载已知 HTML，验证 `runJavaScript` 返回值
- **下载引擎** — 用 `http.server` 本地 HTTP Server 模拟慢速/断连/限速场景，验证重试和断点续传
- **m3u8 转换** — 用本地 .m3u8 + .ts 文件测试 ffmpeg 拼接流程，验证最终 mp4 和临时文件清理
- **跨线程测试** — `queue.Queue` 数据传递验证
- **集成测试** — 用静态 HTML 站模拟三层结构，验证全流程（规则构建→爬取→下载）
- **GUI 测试** — `pytest-qt` 验证信号连接和列表更新，重点测试双击、右键菜单

## 排除项（YAGNI）

- 不提供登录功能（依赖浏览器中已登录的 Session）
- 不做分布式爬取
- 不做自动规则分享平台
