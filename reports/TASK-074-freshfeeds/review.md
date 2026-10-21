# freshfeeds 验收

结论：依赖能装上，31 项测试通过，服务在 `127.0.0.1:8000` 能打开首页。没有 P0。有 2 项 P1：NAT64 本地前缀的内嵌 IPv4 判错，以及首页自动发现在解析失败时仍改写订阅地址。本轮只修这两项。

## 本地跑通记录

环境：仓库 `E:\muse-bridge\in\TASK-074-freshfeeds`。本机 `py` 默认是 `E:\python.exe`（登记为 3.14），进程起不来。改用 `py -3.11`，版本 Python 3.11.9。虚拟环境在 `E:\muse-bridge\work\TASK-074-freshfeeds\venv`，没有写进仓库。

README 的 `py -m venv` 原文错误（退出码 1）：

```
Unable to create process using 'E:\python.exe -m venv E:\muse-bridge\work\TASK-074-freshfeeds\venv-readme-try': ???????????
```

这是本机解释器损坏，不是仓库缺陷。README 要求的 Python 3.10+ 由 3.11.9 满足。

安装（2026-10-22T00:07:24+08:00，退出码 0）：

```
py -3.11 -m venv E:\muse-bridge\work\TASK-074-freshfeeds\venv
E:\muse-bridge\work\TASK-074-freshfeeds\venv\Scripts\python.exe -m pip install --disable-pip-version-check -r E:\muse-bridge\in\TASK-074-freshfeeds\requirements-dev.txt
```

`requirements-dev.txt` 含 `-r requirements.txt`。钉死版本都装上了：fastapi==0.156.7、uvicorn==0.54.0、python-multipart==0.0.32、httpx==0.28.1、pytest==9.1.1。

测试（退出码 0，7.07 秒）。临时目录指到工作目录：

```
set TEMP=E:\muse-bridge\work\TASK-074-freshfeeds\tmp
set TMP=E:\muse-bridge\work\TASK-074-freshfeeds\tmp
cd /d E:\muse-bridge\in\TASK-074-freshfeeds
...\venv\Scripts\python.exe -B -m pytest tests -q -p no:cacheprovider --basetemp E:\muse-bridge\work\TASK-074-freshfeeds\tmp\pytest-basetemp
```

```
...............................                                          [100%]
31 passed, 1 warning in 7.07s
```

警告是 Starlette 弃用 httpx（`fastapi/testclient.py:1`），DECISIONS.md 写明不改依赖版本。

服务（2026-10-22T00:17:43 起，约 00:18:04 停）。`FRESHFEEDS_DB` 指到工作目录，调度保持默认开启。

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:52022 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:52026 - "GET /api/me HTTP/1.1" 401 Unauthorized
```

`GET /` 返回 200，`Content-Type: text/html; charset=utf-8`，正文含 `<title>freshfeeds · 清泉阅读</title>`。`GET /api/me` 无令牌时 401，正文 `{"detail":"未登录"}`。`GET /health` 与 `GET /api/health` 均为 404 `{"detail":"Not Found"}`：代码里没有健康检查路由，README 也没写。`/docs`、`/openapi.json` 为 404，与 `docs_url=None` 一致。停进程后 `netstat` 对 8000 只剩 TIME_WAIT，没有 LISTENING。

另外两条本地抽查（不访问外网，见 run.md 第 4 节）：`64:ff9b:1::/48` 里嵌了 127.0.0.1 仍被放行；首页发现到的地址解析失败后，订阅 url 从 `http://blog.example/home` 变成了 `http://feeds.example/rss`。重定向到 `127.0.0.1:1` 的第二跳会被拦住。

## README 与实际不符处

1. README.md:10 写「响应是 HTML 且正文前 500 字符不含订阅源，会从页面自动发现源（并改写该订阅的地址）」。app.py:662 的条件是 Content-Type 含子串 `html`，并且原始响应前 500 字符里没有 `<feed` 或 `<rss`。没有 link 标签时不会发现，也不会改写；有标签时 app.py:664-666 在 `parse_feed`（app.py:667）之前就 `UPDATE` url。解析失败走 app.py:668-673，这次改写会一起提交。抽查里原地址已被换成解析失败的地址。

2. README.md:11 写「重复订阅同一地址会被拦下」。app.py:244 的 `url TEXT UNIQUE` 和 app.py:806-814 的插入只做字符串全等。主机大小写不同、或只差末尾斜杠，会当成两个源。

3. README.md:12 写定时刷新「默认每 30 分钟一轮」。app.py:1037 在 `refresh_all` 之前先 `sleep(REFRESH_MINUTES * 60)`。进程起来后的第一轮要等满 30 分钟，启动当时不会定时抓取。添加订阅时的立即抓取在另一条路径，不受这句影响。

4. README.md:63-72 的目录清单没有 `.gitignore`。仓库根目录有这个文件（含 `.venv/`、`data/`、`*.db`）。

下列表述与代码一致，不记为不符：Token 24 小时（app.py:34）、默认 `127.0.0.1:8000`（app.py:1053-1056）、`FRESHFEEDS_DB` 相对 app.py 目录（app.py:31）、`FRESHFEEDS_REFRESH_MINUTES` / `FRESHFEEDS_SCHEDULER`（app.py:32-33）、只提示不强制改密（无 403 拦截；static/index.html:131 有「稍后再说」）、RSS 2.0 / RSS 1.0 / Atom、OPML、已读未读与分类。

## 许可证与署名核查

本地文本是自洽的。

- README.md:75-76 写 Apache License 2.0，指向 `LICENSE`。`LICENSE` 是 Apache-2.0 第 1–9 条加附录。附录 LICENSE:190 仍是官方模板占位符 `Copyright [yyyy] [name of copyright owner]`，没有另写版权人。
- UPSTREAM.md:5-6 写上游许可证 Apache-2.0，attribution 为 `Copyright The Miniflux Authors. All rights reserved.`。UPSTREAM.md:9-12 说明这行是上游 `main.go` 的 `SPDX-FileCopyrightText` 引文，本仓库是独立实现，未复制上游源码。app.py:1-6 的模块说明与这句话一致。
- 「All rights reserved」只出现在这句引文里，没有变成对本仓库的额外限制。本仓库自己的许可证文本是 Apache-2.0。
- 仓库没有 NOTICE。UPSTREAM.md:11 说上游也没有 NOTICE。与这段说明一致。
- 源码文件没有版权头。Apache-2.0 不强制每个文件都有头，只要随发行附上许可证。版权人未填是缺口，不是两份声明互相打架。

未核实（禁止抓取外网，不能对照 GitHub）：

- UPSTREAM.md:3 的 `source_commit` `bdd8087d9cf7a20ca7e800948389e8a7e86445da` 是否仍是上游默认分支 HEAD。
- UPSTREAM.md:11 说 attribution 逐字来自 `main.go`，无法对照原文。

app.py:36 的 User-Agent 指向 `https://github.com/ZZmkk88/freshfeeds`。README 与 UPSTREAM 都没写这个地址。它不像许可证冲突，本次未改，也未联网核实该仓库是否存在。

未改 `LICENSE` 与 `UPSTREAM.md`：没有查出可以改写的事实错误。

## 分级修复清单

### P0

无。测试 31 项通过，服务能监听 8000，首页 200。

### P1

1. **NAT64 本地前缀内嵌私网地址被放行。** app.py:81-82 把 `64:ff9b::/96` 和 `64:ff9b:1::/48` 都当成「IPv4 在最低 32 位」。`/96` 这样是对的；`/48` 按 RFC 6052 应取第 48–63 位和第 72–87 位，中间隔着 1 字节 `u`。抽查 `64:ff9b:1:7f00:0:108:808:800`（内嵌 127.0.0.1，后缀看起来像公网）`_is_public_ip` 为 True，`ensure_fetch_allowed` 返回 ALLOW。同一函数对 `/96`、6to4、Teredo、IPv4 映射地址能拦住 127.0.0.1。修法：`/48` 单独按 RFC 6052 拼回 IPv4，再走现有黑名单。

2. **自动发现解析失败仍改写订阅地址。** app.py:664-666 在 app.py:667 的 `parse_feed` 之前更新 url；失败分支 app.py:668-673 提交同一连接，改写被保存。抽查原地址 `http://blog.example/home` 变成 `http://feeds.example/rss`，同时 `last_error` 为 syntax error。修法：只有 `parse_feed` 成功之后才 `UPDATE` url；解析或再次抓取失败时不改地址。

### P2

1. **fec0::/10 未进黑名单。** app.py:67 没有 `fec0::/10`。抽查 `http://[fec0::1]/x` 被 ALLOW。修法：把 `fec0::/10` 加进 `_BLOCKED_NETWORKS`。DECISIONS.md:32 已写明维持不修，本轮不动。

2. **文档用地址段未拦。** app.py:64-66 没有 `192.0.2.0/24`、`198.51.100.0/24`、`203.0.113.0/24`。抽查 `192.0.2.1` 的 `_is_public_ip` 为 True。修法：这三段加入黑名单。DECISIONS.md:32 同样写明维持，本轮不动。`198.18.0.0/15` 是有意放行（app.py:46-48，测试断言其为公网），不修。

3. **同一 URL 的大小写和末尾斜杠不算重复。** app.py:244、app.py:782-783。修法：入库前规范化 scheme/主机。见 README 不符第 2 条。本轮不改行为，避免动到现有判重测试的字符串假设。

4. **测试桩返回 4 元组，生产代码按 5 元组解包。** tests/test_app.py:490 的 `fetch_url` 假实现返回 `("ok", JS_SITE_FEED, "", "")`，app.py:651 解包 5 个值。异常被收成 502 后，site_url 保持默认空串，断言仍能过，并没有真正走到清洗。修法：把桩改成 5 元组。任务禁止改测试，本轮不动。

5. **没有注销接口。** 登录只在 app.py:319 写入 token，改密只删其他会话（app.py:373-377）。修法：增加需登录的注销，删除当前 token。DECISIONS.md:32 写明维持，本轮不动。

6. **Starlette 弃用 httpx 的警告。** 跑测试时的 warning 来自已安装的 fastapi/testclient.py:1。修法会碰到依赖版本。任务禁止改已有依赖版本号，DECISIONS.md:25 也写了不修。

7. **本仓库版权人未写入附录。** LICENSE:190。没有确凿错误，不改 LICENSE。
