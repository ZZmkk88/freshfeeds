# freshfeeds 验收

结论：仓库能在本机装好、测完、起服务。`pytest` 36 项通过。`http://127.0.0.1:8000/` 返回 200 的首页 HTML，默认账号能登录。代码里没有 `/health`，请求得到 404；README 也没有写健康检查。核对过的 README 陈述与代码一致，不符条目为无。LICENSE 与 README 的 Apache-2.0 声明一致；UPSTREAM 里的上游 commit 与文件头署名本次未向外网复核。没有 P0，没有 P1，未改仓库源码。

## 本地跑通记录

解释器：`C:\Users\xzm\AppData\Local\Programs\Python\Python311\python.exe`，输出 `Python 3.11.9`。

README 写的 `py -m venv .venv` 在这台机器上不能用。命令 `py -3 --version` 退出码 1，原文：

```
Unable to create process using 'E:\python.exe --version': ???????????
```

这是本机启动器指向了不存在的 `E:\python.exe`，不记为项目缺陷。虚拟环境改用上面的 Python 3.11.9 创建：`python.exe -m venv .venv`，退出码 0。

运行依赖（退出码 0）：

```
.venv\Scripts\python.exe -m pip install -r requirements.txt
Successfully installed ... fastapi-0.156.7 ... python-multipart-0.0.32 ... uvicorn-0.54.0
```

测试依赖（退出码 0）：

```
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Successfully installed ... httpx-0.28.1 ... pytest-9.1.1
```

全量测试（修复前，退出码 0，7.95s）：

```
.venv\Scripts\python.exe -m pytest tests/ -q --tb=short
....................................                                     [100%]
36 passed, 1 warning in 7.95s
```

警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 来自 `.venv\Lib\site-packages\fastapi\testclient.py:1`。`DECISIONS.md:25` 已写明不改依赖版本。

起服务：`FRESHFEEDS_DB` 指到 `E:\muse-bridge\work\TASK-093-freshfeeds\server.db`，HOST / PORT / 定时刷新用默认。`.venv\Scripts\python.exe app.py` 的日志：

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

本机请求（urllib，未使用 curl / wget）：

| 请求 | 状态 | 正文片段 |
| --- | --- | --- |
| GET / | 200 | `text/html`，16132 字节，title 为 freshfeeds · 清泉阅读 |
| GET /health | 404 | `{"detail":"Not Found"}` |
| GET /api/health | 404 | `{"detail":"Not Found"}` |
| GET /docs、/redoc、/openapi.json | 404 | 与 `app.py:213-215` 关闭文档页一致 |
| GET /api/me（无令牌） | 401 | `{"detail":"未登录"}` |
| POST /api/login `admin` / `admin123` | 200 | `must_change_password` 为 true |
| GET /api/me、GET /api/feeds（带令牌） | 200 | 用户名 admin；订阅列表 `[]` |

进程随后 `terminate()`，父进程退出码 1（结束信号，不是启动失败）。端口 8000 再次连接为 TimeoutError。`Get-Process -Id 9024,34688` 已无此进程。未用浏览器点击页面。定时线程默认开启，循环先 `sleep`（`app.py:1052-1053`）；进程数秒内被关掉，没有等待 30 分钟，没有第一轮抓取。

默认配置另由 `probe2.py` 打印：`DB_PATH` = `E:\muse-bridge\in\TASK-093-freshfeeds\data\freshfeeds.db`，`REFRESH_MINUTES` = 30，`SCHEDULER_ON` = True，`TOKEN_TTL_HOURS` = 24。未再改端口复测 HOST/PORT 的覆盖值；默认值已由上面的 uvicorn 日志证实（`app.py:1069-1072`）。

补充探针（DNS 打桩，无外网页面）：内网字面量、十进制/十六进制/八进制、`127.1`、`::1`、IPv4 映射、SIIT、6to4 私网、NAT64 私网、Teredo 私网、`file:` / `javascript:` / `gopher:`、以及 `http://8.8.8.8@127.0.0.1/` 一类 userinfo，均被 `BlockedUrlError` 拒绝。`8.8.8.8`、`93.184.216.34`、`198.18.0.1` 放行。`_open_pinned` 在钉死 IP 时没有调用真实 `getaddrinfo`，本地连接返回 200。`fetch_url` 睡眠 6 秒期间另一条 SQLite 连接插入成功（`SELECT` 之后 `in_transaction` 为 False），不构成「抓取占着写锁」的缺陷。

## README 与实际不符处

不符条目：无。下面是核对过、且与代码一致的陈述。

- `README.md:9` Token 24 小时：`app.py:34` `TOKEN_TTL_HOURS = 24`，签发处 `app.py:342-344`。
- `README.md:9` 首次登录只提示、不强制：冒烟登录返回 `must_change_password: true`，随后 `GET /api/me` 仍是 200。后端没有在 `must_change=1` 时对其它接口返回 403。对话框可关：`static/index.html:131`「稍后再说」。
- `README.md:10` RSS 2.0 / RSS 1.0 / Atom：`app.py:562-648`。对应测试 `tests/test_app.py:132`、`163`、`176` 在 36 项里通过。
- `README.md:10` 首页发现源的条件（Content-Type 含 html、前 500 字符不含 `<feed`/`<rss`、`<rdf:RDF` 不在排除列、解析成功才改地址）：`app.py:675-682`。测试 `tests/test_app.py:599`、`619` 通过。
- `README.md:11` 添加后立即抓取、重复地址拒绝：`app.py:820-835`。
- `README.md:12` 单源刷新、全部刷新、默认 30 分钟、启动后先等一个间隔：`app.py:32`、`848-855`、`1049-1053`。
- `README.md:13` ETag / Last-Modified 与按源内标识判重：`app.py:466-469`，唯一约束 `app.py:272`。
- `README.md:14-18` 已读、分类、搜索、OPML、失败打标：路由在 `app.py:861-1043`，失败写入 `app.py:683-690`，前端标记 `static/index.html:183`。相关测试在同一轮 36 项中通过。
- `README.md:42` 打开 `http://127.0.0.1:8000`、账号 `admin` / `admin123`：冒烟记录如上。
- `README.md:47-48` `pip install -r requirements-dev.txt` 与 `python -m pytest tests/ -q`：已执行，36 passed。
- `README.md:57-61` 五个环境变量的默认值：见上一节打印与 uvicorn 日志。
- `README.md:64-73` 列出的文件都在。`.gitignore:1` 为 `.venv/`，`:6` 为 `data/`，`:7` 为 `*.db`。
- `README.md:22` 需要 Python 3.10+：本次只用 3.11.9 跑通，没有另装 3.10。

`py` 启动器失败只发生在本机，README 的 Windows 步骤本身没有写错命令。

## 许可证与署名核查

- `README.md:71` 与 `README.md:76` 写 Apache License 2.0，指向 `LICENSE`。本地读完的 `LICENSE` 是 Apache License Version 2.0 条款第 1–9 条加附录。未与 apache.org 原文逐字节比对（本次不访问外网页面）。
- 附录 `LICENSE:190` 仍是许可证文本里的示例行 `Copyright [yyyy] [name of copyright owner]`，不是另填的版权人。本仓库源码文件头没有版权行，也没有 NOTICE。这与「附上 Apache 2.0 原文」不冲突。`DECISIONS.md:36` 把「补 LICENSE 附录版权人」记为不采纳。
- `UPSTREAM.md:3-6` 写上游 `https://github.com/miniflux/v2`、commit `bdd8087d9cf7a20ca7e800948389e8a7e86445da`、Apache-2.0、署名 `Copyright The Miniflux Authors. All rights reserved.`。`UPSTREAM.md:11-12` 说该署名抄自上游 `main.go` 的 SPDX 行，且本仓库是独立实现、未复制上游源码。这些上游事实本次未核实。仓库内检索 `Miniflux` / `Copyright` / `SPDX`，署名只出现在 `UPSTREAM.md` 与 `NOTES.md:5`，Python 源码里没有 Miniflux 源码片段，和「未复制上游源码」这句在库内看不到反证。
- `app.py:36` 的 User-Agent 是 `freshfeeds/1.0 (+https://github.com/ZZmkk88/freshfeeds)`。README 与 UPSTREAM 都没有这个地址。UPSTREAM 记录的是 miniflux 的设计来源，User-Agent 写的是另一个仓库。该 URL 是否存在：未核实。见分级清单 P2-4。

## 分级修复清单

### P0

无。依赖安装成功，36 项测试通过，服务能监听 8000 并返回首页。

### P1

无。探针覆盖的内网与过渡地址绕过均被拒绝；慢抓取不占着 SQLite 写锁；登录、改密吊销其它会话、OPML 体积与 DTD、密码长度、`javascript:` 链接，已有测试且本轮通过。

### P2

1. `app.py:67` 黑名单有 `fc00::/7`、`fe80::/10`，没有 `fec0::/10`。探针 `http://[fec0::1]/` 放行。修法：把 `fec0::/10` 加入 `_BLOCKED_NETWORKS`。`DECISIONS.md:36` 已关闭此项，本次不修。
2. `app.py:61-68` 未包含文档/特殊地址。探针放行 `192.0.2.1`、`198.51.100.1`、`203.0.113.1`、`2001:db8::1`、`100::1`。修法：按需加入对应网段。IPv4 文档段在 `DECISIONS.md:36` 已关闭。`198.18.0.0/15` 是 `app.py:46-48` 写明的刻意放行（假 IP DNS），不算遗漏。本次不修。
3. 测试警告要装 `httpx2`，钉死版本是 `requirements-dev.txt:2` 的 `httpx==0.28.1`。修法：升级 httpx。`DECISIONS.md:25` 不修，且任务不许改已有依赖版本号。本次不修。
4. `app.py:36` User-Agent 指向 `github.com/ZZmkk88/freshfeeds`，`UPSTREAM.md:3` 与 README 未记载该地址。修法：在 UPSTREAM 说明这个运行时标识，或改掉 User-Agent。上游事实未核实，不改 UPSTREAM 里已有句子。本次不修。
5. `app.py:798` 用区分大小写的 `startswith(("http://", "https://"))`，`HTTP://8.8.8.8/feed` 进不了添加接口；`app.py:150` 的 `ensure_fetch_allowed` 接受同一 URL。修法：用 `urlsplit` 的 scheme 判断。失败方向是拒绝，不是放行内网。本次不修。
6. `app.py:159` 把 urlparse 主机和 urllib 实际主机不一致的 URL 全部拒绝。探针里 `http://user:pass@8.8.8.8/` 也报「网址主机名含混」。修法：只在两边解析出的主机不同且存在混淆时拒绝，相同的 userinfo 公网主机放行。当前是收紧，本次不放宽。
7. `app.py:868` 的 `offset` 在 `app.py:891` 原样进 SQL。探针在 3 篇文章、`limit=2` 时 `offset=-1` 与 `offset=0` 都返回 `title0`、`title1`。修法：`offset = max(0, offset)`。没有多吐数据。本次不修。
8. `app.py:431-432` 在钉死解析时，主机名对不上就回退真实 `getaddrinfo`。正常抓取路径下，对不上的主机在 `app.py:159` 已经拒绝；本次没有做出绕过。修法：对不上时直接失败。本次不修。
9. `tests/test_app.py:490` 把 `fetch_url` 打成 4 元组，`app.py:663` 按 5 元组解包，刷新会进异常分支；`tests/test_app.py:496` 只断言 `site_url == ""`，而新行默认就是空串。修法：测试桩返回 5 元组并断言标题。任务禁止改测试。产品路径在 `app.py:609` 仍对 site_url 调用 `_clean_url`。本次不修。

已决且与 README 一致、不再列入待修：不强制改密（`DECISIONS.md:7-10`）、不提供注销接口（`DECISIONS.md:36`）。
