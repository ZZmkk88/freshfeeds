# freshfeeds 验收

结论：依赖能装上，31 项测试通过，`127.0.0.1:8000` 首页和登录正常。没有 P0。有 1 个 P1：NAT64 本地前缀 `64:ff9b:1::/48` 的内嵌 IPv4 抽错了位，私网和云元数据地址会被放行。本轮只修这一项。

## 本地跑通记录

环境：`python` 指向 `E:\muse-bridge\env\TASK-077-freshfeeds\Scripts\python.exe`，版本 3.11.9。仓库内没有另建 `.venv`。临时库和脚本在 `E:\muse-bridge\work\TASK-077-freshfeeds`。

`py -3 --version` 失败（exit 1）：

```
Unable to create process using 'E:\python.exe --version': ???????????
```

这是本机 py 启动器坏了，不是仓库缺陷。README 要求 Python 3.10+，3.11.9 满足。

安装（工作目录为仓库，exit 0）：

```
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

`fastapi==0.156.7`、`uvicorn==0.54.0`、`python-multipart==0.0.32`、`httpx==0.28.1`、`pytest==9.1.1` 都装上了。

全量测试（修复前，exit 0）：

```
python -m pytest tests/ -q --tb=line
31 passed, 1 warning in 7.43s
```

警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 测试没有失败。

起服务：`E:\muse-bridge\work\TASK-077-freshfeeds\serve.py` 在导入前把库指到 work 目录，并设 `FRESHFEEDS_SCHEDULER=0`，然后听 `127.0.0.1:8000`。日志：

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

`smoke_client.py` 结果：

```
GET / 200 text/html; charset=utf-8 b'<!DOCTYPE html>\n<html lang="zh-CN">...
GET /health 404 b'{"detail":"Not Found"}'
GET /api/health 404 b'{"detail":"Not Found"}'
GET /docs 404
GET /openapi.json 404
GET /redoc 404
GET /app.py 404
GET /data/freshfeeds.db 404
LOGIN 200 keys ['must_change_password', 'token'] must_change True
ME 200 {"username":"admin","must_change_password":true}
FEEDS_NOAUTH 401 {"detail":"未登录"}
```

README 没有健康检查路径。`/health` 与 `/api/health` 返回 404 与 README 不冲突。`/docs`、`/openapi.json`、`/redoc` 关闭，和 `app.py:206-208` 一致。源码和数据库文件没有被静态路径暴露。

本机没有浏览器工具，登录后的改密对话框没有在浏览器里点过。接口返回 `must_change_password: true`，前端在 `static/index.html:163` 会弹出对话框。

服务进程 PID 36648 已退出（`tasklist` 无此 PID）。`netstat` 上 8000 只剩 TIME_WAIT，没有 LISTENING。之后对 `127.0.0.1:8000` 的 TCP 连接超时而不是立刻拒绝，进程已经不在。

另外用本地 HTTP 服务器核对了抓取（`probe2.py`，未访问外网）：

- 302 能跟到下一跳，并取回 RSS：`REDIR-OK ok application/rss+xml`
- 302 到 `http://10.1.2.3/evil` 被拦：`拒绝抓取内网/保留地址：10.1.2.3`
- HTML 页里的 `rel=alternate` RSS 能发现并改写订阅地址，入库 1 篇
- 按 RFC 6052 拼出的 `64:ff9b:1:7f00:0:100:808:808`（内嵌 127.0.0.1，后缀 8.8.8.8）被放行；`64:ff9b:1:a9fe:a9:fe00:101:101`（内嵌 169.254.169.254，后缀 1.1.1.1）被放行。代码把末 32 位当成了 IPv4

## README 与实际不符处

1. README.md:10 写「填源地址添加」，没有说内网或保留地址会被拒绝。`app.py:801-804` 在入库前调用 `ensure_fetch_allowed`，`http://127.0.0.1/...` 直接 400。
2. README.md:10 写「响应是 HTML 且正文前 500 字符不含订阅源，会从页面自动发现源」。`app.py:662` 实际看的是 Content-Type 是否包含子串 `html`，并且前 500 个字符里没有字面量 `<feed` 或 `<rss`。页面正文前 500 字符里出现 `<rss` 就不会发现；Content-Type 不含 `html` 的 HTML 也不会发现。
3. README.md:60-61 只把 `FRESHFEEDS_SCHEDULER=0` 写成关闭定时刷新。`app.py:1034-1035` 在 `FRESHFEEDS_REFRESH_MINUTES <= 0` 时也会直接返回，调度线程不再循环。

其余对照过的说法和代码一致：Token 24 小时（`app.py:34`）、默认账号 `admin` / `admin123`（`app.py:273-274`）、只提示改密（`static/index.html:128-131`）、监听 `HOST`/`PORT` 默认 `127.0.0.1:8000`（`app.py:1053-1056`）、数据库默认在 app.py 同目录的 `data/freshfeeds.db`（`app.py:31`）、目录里列出的文件都在。

## 许可证与署名核查

- README.md:75-76 写 Apache License 2.0。`LICENSE` 是 Apache License 2.0 标准条款，条款在 `LICENSE:177` 的 `END OF TERMS AND CONDITIONS` 结束。许可证名称与 README 一致。
- `LICENSE:190` 附录仍是占位符 `Copyright [yyyy] [name of copyright owner]`。这是 Apache 附录里的填写说明，不是已经填好的版权行。本仓库源码文件头也没有版权行。
- UPSTREAM.md:3-6 写上游是 `https://github.com/miniflux/v2`，commit `bdd8087d9cf7a20ca7e800948389e8a7e86445da`，许可证 Apache-2.0，署名为 `Copyright The Miniflux Authors. All rights reserved.`。UPSTREAM.md:12 写本仓库只学设计、代码独立实现、未复制上游源码。本仓库是 Python，LICENSE 正文里没有 Miniflux 这句版权。两份文件可以同时成立：UPSTREAM 记的是上游署名，不是声称 LICENSE 里印了这句。
- 上游 commit 是否仍是默认分支 HEAD、`main.go` 里是否真有这句 SPDX，本次禁止访问外网，**未核实**。
- `app.py:36` 的 User-Agent 是 `freshfeeds/1.0 (+https://github.com/ZZmkk88/freshfeeds)`。README 和 UPSTREAM 都没有这个地址。该仓库是否存在，**未核实**。它和 Miniflux 上游地址不是同一条，文档没有解释。

没有发现 LICENSE / UPSTREAM 里可以凭本地文件断定的事实错误，所以不改这两个文件。

## 分级修复清单

### P0

无。测试 31 项通过，服务能听 8000，首页 200，登录 200，未登录访问 `/api/feeds` 为 401。

### P1

1. P1-1 `app.py:81-82`：`64:ff9b::/96` 和 `64:ff9b:1::/48` 共用「取末 32 位」。前者符合 RFC 6052（前缀长 96，IPv4 就在末尾）；后者前缀长 48，IPv4 被第 64–71 位的 u 字节拆开，末 32 位是后缀。后缀写成公网地址时，内嵌的 127.0.0.1 或 169.254.169.254 会被放行；后缀为 0 时，内嵌 8.8.8.8 会被当成 0.0.0.0 误拦。修法：两条前缀分开，`/48` 用第 48–63 位和第 72–87 位拼 IPv4，再走原来的网段黑名单。

### P2

1. P2-1 `README.md:10`：补一句内网/保留地址会 400。本轮不改文档。
2. P2-2 `README.md:10` 与 `app.py:662`：把自动发现的 Content-Type 和 `<rss`/`<feed` 条件写进 README。本轮不改文档。
3. P2-3 `README.md:60-61` 与 `app.py:1034-1035`：写明刷新间隔小于等于 0 也会停调度。本轮不改文档。
4. P2-4 `app.py:61-68` 与 `app.py:47-48`：`198.18.0.0/15` 故意不拦（假 IP DNS）。`DECISIONS.md:16` 已定，不修。
5. P2-5 `app.py:61-68`：文档网段 `192.0.2.0/24`、`198.51.100.0/24`、`203.0.113.0/24`、`2001:db8::/32` 以及 `fec0::/10` 未进黑名单。`DECISIONS.md:32` 写明维持不修。
6. P2-6 `requirements-dev.txt:2`：Starlette 提示 httpx 已弃用、要装 httpx2。不许改已有依赖版本号，不修。
7. P2-7 `static/index.html:172`：退出只清 localStorage，后端没有注销接口，token 留到过期。`DECISIONS.md:32` 维持，不修。
8. P2-8 `README.md:42` 与 `static/index.html:69`：默认口令写在 README 和登录页，且不强制改密。`DECISIONS.md:7-10` 永久不采纳强制改密，不修。
9. P2-9 `app.py:870-872`：搜索词里的 `%`、`_` 会当成 LIKE 通配符。单用户自己的数据，不修。
10. P2-10 `app.py:1040-1041`：定时刷新把异常吞掉。不修。
11. P2-11 `tests/test_app.py:490`：`fetch_url` 桩只返回 4 元组，生产代码按 5 元组解包，这条用例不能证明 site_url 清洗。不许改测试，不修。
12. P2-12 `LICENSE:190`：附录版权人仍是占位符。不发明版权主体，不改 LICENSE。
