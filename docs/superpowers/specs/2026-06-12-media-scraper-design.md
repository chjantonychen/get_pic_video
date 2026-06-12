# 通用网站媒体下载器 — 设计文档

## 概述

PyQt5 图形界面程序，通过可视化点选定义爬取规则，从任意网站逐层提取图片和视频并下载。三层结构：网址 → 分页/列表 → 详情页 → 媒体资源。

## 技术栈

| 组件 | 选型 | 原因 |
|------|------|------|
| GUI 框架 | PyQt5 | 内置 Qt WebEngine，支持嵌入式浏览器 |
| 浏览器引擎 | Qt WebEngine (Chromium) | 渲染 JS 页面、支持可视化点选、天然反爬 |
| 爬取方式 | 通过 `runJavaScript()` 注入 JS 操作 DOM | 无需 Session 同步，复用浏览器 Cookie |
| 下载并行 | `concurrent.futures.ThreadPoolExecutor` | 多线程 HTTP 下载 |
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
- **下载引擎** — 基于线程池的并发下载器，支持断点续传、URL 去重、失败重试（指数退避）、可选限速。
- **规则存储** — 以 JSON 序列化整套规则（选择器、属性、反爬配置），按域名管理，支持导入导出。

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
    pagination: SelectorRule
    page_list: SelectorRule
    detail_images: SelectorRule
    detail_videos: SelectorRule
    next_button: SelectorRule
    anti_crawl: AntiCrawlConfig

@dataclass
class SelectorRule:
    css: str
    attribute: str              # src / href / data-src
    wait_selector: str = ""

@dataclass
class AntiCrawlConfig:
    delay_range: tuple = (1, 3)
    use_proxy: bool = False
    proxy_list: list = None
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

### 交互流程

| 步 | 用户操作 | 程序行为 |
|----|---------|---------|
| 1 | 输入 URL → 点击"分析" | 浏览器加载 → 注入 `extractLinks` → 填充分页列表 |
| 2 | 双击某分页 | 浏览器导航到该页 → 提取详情链接 → 填充详情列表 |
| 3 | 选中详情 → 下载 | 遍历选中的详情页 → 提取媒体 URL → 启动线程池 |
| 可选 | "下载全部" | 遍历全部分页 → 全部详情 → 全部资源 |

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
  const nums = Array.from(links).map(el => parseInt(el.textContent));
  return Math.max(...nums.filter(n => !isNaN(n)));
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
- URL 去重：基于 URL 字符串

### 断点续传

下载前检查本地文件是否存在及大小，发 HTTP Range 请求续传。仅对支持 Range 的服务器有效。

### 反爬

- WebEngine 本身就是真实浏览器指纹，无需额外伪装
- 请求间隔随机延迟（1-3 秒可配）
- 可选代理轮换
- User-Agent 随机切换
- Cookie 自动保持

## 错误处理

- **规则匹配不到元素** — 提示用户检查选择器，高亮当前页面所有可交互元素帮助诊断
- **网络错误** — 自动重试，3 次失败后跳过并记录
- **下载失败** — 跳过该文件，继续队列，最终汇总失败列表
- **浏览器崩溃** — 重启 WebEngine，保留已爬取的数据

## 测试策略

- 规则选择器验证：用已知页面测试 `querySelectorAll` 返回值
- 下载引擎：用本地 HTTP Server 模拟慢速/断连场景
- GUI：手动测试各交互路径，重点测试双击/右键菜单

## 排除项（YAGNI）

- 不内置视频格式转换（如需 m3u8→mp4，可提示用户安装 ffmpeg 作为可选）
- 不提供登录功能（依赖浏览器中已登录的 Session）
- 不做分布式爬取
- 不做自动规则分享平台
