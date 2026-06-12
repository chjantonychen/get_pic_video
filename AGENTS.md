# GetIv — AGENTS.md

## 运行
```bash
python -m app.main
```

## 测试
```bash
pytest tests/ -v
```

## 架构
- **技术栈**: PyQt5, Qt WebEngine (Chromium 87), ffmpeg
- **核心模块**: `app/gui/` (界面), `app/rule_builder/` (点选引擎), `app/crawl_engine/` (爬取), `app/download_engine/` (下载)
- **规则存储**: `config.json` (同级目录)，自动以域名为规则名
- **快捷键**: Ctrl+Enter 分析, Ctrl+D 下载, Ctrl+Shift+A 自动下载, F5 刷新浏览器

## 关键要点
- **iframe 网站**: 内容在 `<iframe>` 中，所有 JS 注入和爬取需递归搜索 iframe (`f.contentDocument`)
- **动态内容**: iframe 通过 postMessage 加载，`loadFinished` 后需延迟 2-3 秒再提取
- **JS→Python 通信**: 不使用 QWebChannel，改用 `document.title` 变更 + `titleChanged` 信号
- **点选高亮**: 使用 CSS `*:hover` 或 JS `mouseover` 事件（`useCapture: true`），非 QWebChannel
- **分页展开**: 提取最大页码后生成完整 URL 列表（`build_extract_all_pages_js`）
- **URL 相对路径**: 所有提取的 URL 必须补全为绝对路径（`_resolve_url` 加 `window.location.origin`）
- **信号时序**: 必须先 `connect` 再 `navigate`，否则错过 `loadFinished`

## 已知问题
- Qt WebEngine 5.15 Chromium 版本过旧，部分网站渲染不全
- 混合内容（HTTP 图片 on HTTPS 页面）需要 `AllowRunningInsecureContent`
- m3u8→mp4 需要在 `_download_file` 中检测 URL 后缀并路由到 `M3U8Handler`（已实现）
