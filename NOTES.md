# 调研与取舍笔记（freshfeeds）

## 开工前读了什么

- 上游 Miniflux（github.com/miniflux/v2，Apache-2.0）README 全文、LICENSE 原文、根目录结构、main.go 文件头署名；默认分支 HEAD = bdd8087d9cf7a20ca7e800948389e8a7e86445da（GitHub 接口实查）。
- 上游核心模型（从其 README 与公开文档归纳）：分类（categories）→ 订阅源（feeds）→ 文章（entries）三级；文章带状态（未读/已读）；抓取走定时轮询；文章按内容标识判重；支持 OPML 导入导出；抓取用条件请求省流量。

## 资源核对（动手前）

- 云端实测：2 核 CPU、7.7G 内存（本机 free 实测）、磁盘可用约 7.4G、无显卡。
- 本方案：Python + FastAPI + SQLite + 单页前端，项目源码约 180KB，venv 约 49M，运行时只多一个 Python 进程加一个后台刷新线程。结论：带得动，绰绰有余。

## 我的取舍

- 数据库用 SQLite 单文件，不学上游的 PostgreSQL——单用户自用场景更轻，部署一步到位。
- 解析只用标准库 xml.etree：RSS 2.0、RSS 1.0(RDF)、Atom 三种格式手写映射，不引 feedparser，减少依赖面；日期解析用 email.utils + fromisoformat 兜底。
- 判重标识优先级：条目自带 guid/id → 文章链接 → 标题+正文的 sha256。入库用 INSERT OR IGNORE + UNIQUE(feed_id, guid) 兜底。
- 抓取礼貌：带 ETag / If-Modified-Since 条件请求，304 直接跳过；失败把原因写进 feeds.last_error 并在前端标 ⚠️，不吞错。
- 定时刷新：进程内守护线程，默认 30 分钟一轮（FRESHFEEDS_REFRESH_MINUTES 可调，FRESHFEEDS_SCHEDULER=0 关闭）；刷新全程一把锁串行，避免自己和自己抢。
- 订阅发现：填的是网页（HTML）时，正则找 link rel=alternate 的 rss/atom 地址再跳过去抓——查了通行做法后自己实现的简化版，只认第一个候选。
- 正文只存纯文本摘要（去标签、上限 2000 字），前端一律转义输出——不渲染外部 HTML，杜绝订阅源把脚本带进页面。
- 登录沿用自家既有做法：pbkdf2 存密码、Token 存哈希、24 小时过期、默认 admin/admin123，首登只提示改密、不强制（与口径第 1 条一致）。
- 界面自研：左侧栏（分类+订阅列表+未读徽标）+ 右侧文章卡片流、青绿配色，与上游的顶部导航纯列表排版明显不同。

## 没做的（MVP 之外，明确不扩）

- JSON Feed 格式、多用户与第三方登录、全文抓取（Readability）、第三方保存集成、Fever/Google Reader 兼容 API、媒体代理。
