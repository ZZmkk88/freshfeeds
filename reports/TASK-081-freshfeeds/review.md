# freshfeeds 验收

结论：仓库能在本机跑通。pytest **31 passed**（6.63s，另有 1 条依赖弃用警告）。`127.0.0.1:8000` 能起，首页 200，默认账号能登录；没有 `/health`（404），与 README 一致。服务已关掉。README 有 4 处和代码不一致，都是文档。许可证种类自洽，版权人没写上，上游 commit 未联网核实。**没有 P0，没有 P1，仓库源码未改。**

## 本地跑通记录

解释器：`python -V` → `Python 3.11.9`。`py -V:3.11 -V` 同样是 3.11.9。README 写的 `py -m venv` 在本机失败（环境限制，不是项目缺陷）：

```
py -m venv E:\muse-bridge\work\TASK-081-freshfeeds\venv-py-default
```

```
Unable to create process using 'E:\python.exe -m venv ...': ???????????
```

`py -0p` 显示默认指向损坏的 `E:\python.exe`（登记为 3.14）。实际用 `py -V:3.11 -m venv E:\muse-bridge\work\TASK-081-freshfeeds\venv`（exit 0）。虚拟环境放在工作目录，没有在仓库里建 `.venv`。

装依赖（exit 0）：

```
...\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-081-freshfeeds\requirements.txt
...\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-081-freshfeeds\requirements-dev.txt
```

装上 `fastapi==0.156.7`、`uvicorn==0.54.0`、`python-multipart==0.0.32`、`httpx==0.28.1`、`pytest==9.1.1`。传递依赖里有 starlette 1.9.0、pydantic 2.14.1。未改版本号。

全量测试（仓库根目录，TEMP 指到工作目录）：

```
...\venv\Scripts\python.exe -m pytest tests/ -q -o cache_dir=E:\muse-bridge\work\TASK-081-freshfeeds\pytest_cache --basetemp E:\muse-bridge\work\TASK-081-freshfeeds\tmp
```

```
...............................                                          [100%]
31 passed, 1 warning in 6.63s
```

警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 来自 `fastapi\testclient.py:1`。DECISIONS.md:25 写明这项不改依赖版本。不记为缺陷。

起服务：工作目录里的 `start_server.py` 把 `FRESHFEEDS_DB` 指到 `E:\muse-bridge\work\TASK-081-freshfeeds\freshfeeds.db`，`HOST=127.0.0.1`，`PORT=8000`，再以 `__main__` 跑仓库 `app.py`。未改 `FRESHFEEDS_SCHEDULER`，默认开启。

```
INFO:     Started server process [10500]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

`probe_http.py`（标准库 urllib，只打本机）：

```
/               200  text/html  标题 freshfeeds · 清泉阅读
/health         404  {"detail":"Not Found"}
/docs           404  {"detail":"Not Found"}
/redoc          404  {"detail":"Not Found"}
/openapi.json   404  {"detail":"Not Found"}
/api/me         401  {"detail":"未登录"}
/api/feeds      401  {"detail":"未登录"}
POST /api/login 200  must_change True  token_len 43
GET /api/me     200  {"username":"admin","must_change_password":true}
POST /api/feeds/refresh-all  200  {"feeds":0,"added":0,"failed":0}
```

访问日志与上面的状态码一致。README 未写健康检查；`app.py` 只有 `GET /`（`app.py:1044`），没有 `/health`。404 不是文档不符。

关掉：`Stop-Process -Id 10500`（exit 0）。之后 `Get-Process -Id 10500` 为 `NoProcessFoundForGivenId`；`netstat -ano -p tcp | findstr :8000` 无匹配（exit 1）。再连 8000 得到 `TimeoutError timed out`，没有 HTTP 响应。

另外用本地探针核对了抓取行为（脚本在 `E:\muse-bridge\work\TASK-081-freshfeeds\`，未访问外网）：

- 重定向第二跳到 `127.0.0.1` 被拒绝；同端口 302 到本机 `/rss` 能跟到正文（`redirect followed | ok`）。
- `ensure_fetch_allowed` 被换成只返回 `127.0.0.1` 时，`http://pinned.invalid:<端口>/pin` 打进本地监听（`HIT /pin`），DNS 钉死生效。
- 首页 HTML 带 `application/rss+xml` 的 link 时，订阅地址从 `/page` 改写成 `/rss.xml`，标题 `Discovered`，`added` 1。
- 浏览器那种空 body + `Content-Type: application/json` 的「全部标已读」「刷新全部」都是 200。
- `parse_feed`：频道 `javascript:alert(1)` 和条目 `javascript:` 的 url 都是 `''`，`https://js.example/ok` 保留。

## README 与实际不符处

1. **发现订阅源的判定和 README 的说法不一样。** README.md:10 写「响应是 HTML 且正文前 500 字符不含订阅源」。`app.py:662` 的条件是 Content-Type 含子串 `html`，并且前 500 字符里没有 `<feed` 和 `<rss`。`text/plain` 的 HTML 不会走发现；`application/xhtml+xml` 会（`xhtml` 里含 `html`）；RSS 1.0 的 `<rdf:RDF` 不算「已有订阅源」。主路径（`text/html` + `<link type=application/rss+xml>`）探针已走通。

2. **定时刷新的第一次执行点和「≤0」的含义 README 没写。** README.md:12、README.md:60 把 `FRESHFEEDS_REFRESH_MINUTES` 说成默认 30 分钟一轮。`app.py:1036-1037` 先 `sleep` 再抓，进程起来后要等满一个间隔才有第一轮。`app.py:1034-1035` 在间隔 ≤0 时线程直接 return。表里没写 0 或负数是关闭。只有字符串 `"0"` 会关调度器（`app.py:33`），`false` 仍会开。

3. **目录清单漏了 `.gitignore`。** README.md:63-72 列出的源码文件都在。仓库另有 `.gitignore:1`（`.venv/`、`data/`、`*.db` 等），清单里没有。

4. **「版本钉死」只钉了直接依赖。** README.md:72。`requirements.txt:1-3` 与 `requirements-dev.txt:1-3` 钉了直接包。本次 pip 解析出的 starlette 1.9.0、pydantic 2.14.1 不在这两个文件里。

核对过、与代码一致的部分：Python 3.10+ 与 `int | None`；默认 `admin` / `admin123`（`app.py:274`，登录探针 200）；Token 24 小时（`app.py:34`）；只提示改密、不强制（登录返回 `must_change_password: true`，接口没有因未改密而 403）；库路径默认在 `app.py` 旁的 `data/freshfeeds.db`（`app.py:31`）；监听默认 `127.0.0.1:8000`（`app.py:1053-1056`，启动日志已证实）；RSS 2.0 / RSS 1.0 / Atom、OPML、分类删除不删源、搜索标题和正文，由通过的测试覆盖。

## 许可证与署名核查

种类是齐的。README.md:75-76 写 Apache License 2.0。`LICENSE` 是 Apache 2.0 条款全文加官方附录模板。UPSTREAM.md:5 写 `license: Apache-2.0`。三处对得上。

附录里的 `Copyright [yyyy] [name of copyright owner]`（LICENSE:190）是官方「如何套用」模板，括号还在，不是已经填好的本仓库版权行。`app.py`、`static/index.html` 没有版权头，仓库里也没有 NOTICE。Apache 2.0 第 1 条用版权声明来标明 Work；这份声明在本仓库里没有落到具体版权人。

UPSTREAM.md:6 的 `Copyright The Miniflux Authors. All rights reserved.` 按 UPSTREAM.md:11 是从上游 `main.go` 的 SPDX 行抄来的记录。同文件 UPSTREAM.md:12 写本仓库只学设计、未复制源码。文件内部讲得通。「All rights reserved」是版权声明，不取消 Apache 2.0 已给出的许可，不构成条款互相否定。

缺口是：本实现的版权人没有出现。`app.py:36` 的 User-Agent 是 `freshfeeds/1.0 (+https://github.com/ZZmkk88/freshfeeds)`，README 和 UPSTREAM 都没有这个地址。任务禁止抓外网，**未核实** `ZZmkk88/freshfeeds` 是否存在，也 **未核实** UPSTREAM.md:4 的 commit `bdd8087d9cf7a20ca7e800948389e8a7e86445da` 是否仍是 miniflux/v2 的 HEAD、`main.go` 是否有那行 SPDX。代码形态是 Python + FastAPI + SQLite（`app.py:1-6`），和上游 Go 项目不同，和「独立实现」的自述方向一致；没有逐行比对上游。

LICENSE 与 UPSTREAM 的事实句没有查出可以改写的确凿错误，本次不改这两个文件。

## 分级修复清单

### P0

无。测试 31 项通过，服务能监听 `127.0.0.1:8000` 并返回首页。

### P1

无。下面这些已经在代码里，并用探针或测试确认过，不列成待修：

- 回环、RFC1918、169.254.169.254、100.64/10、组播、`0.0.0.0`、`::1`、IPv4 映射、6to4、NAT64、十进制 `2130706433`、十六进制 `0x7f000001`、八进制 `0177.0.0.1`、`localhost` 均拒绝（`app.py:61-68`、`app.py:91-104`；`probe_behavior.py` / `probe_ssrf2.py`）。
- 带 userinfo 的 `http://8.8.8.8@127.0.0.1/`、`http://127.0.0.1@8.8.8.8/` 报「网址主机名含混」并拒绝（`app.py:152-153`）。
- 重定向每一跳再校验；第二跳内网被拒。DNS 钉死能把连接打到已放行的 IP。
- `javascript:` 的频道链接和条目链接入库为空（`app.py:541-547`，`probe_clean.py`）。
- `/docs`、`/redoc`、`/openapi.json` 为 404（`app.py:203-208`）。
- 超长密码、改密吊销其他会话：测试已通过（`tests/test_app.py` 中对应用例，`app.py:322-323`、`app.py:373-377`）。

### P2

1. README.md:10 与 `app.py:662` 的发现条件不一致。修法：按代码改 README 那一句，写明 Content-Type 与 `<feed`/`<rss`。
2. README.md:12、README.md:60 与 `app.py:1034-1037`。修法：写上「先睡再抓」以及间隔 ≤0 时不跑。
3. README.md:63-72 漏了 `.gitignore`。修法：目录清单补一行。
4. README.md:72 的「版本钉死」没覆盖传递依赖。修法：若要可复现构建，另加锁文件；不要为这个去改已钉死的直接依赖版本。
5. `app.py:61-68` 未拦截 `fec0::/10`。探针 `http://[fec0::1]/`、`http://[fec0:0:0:ffff::1]/` 放行。DECISIONS.md:32 已决定不修。修法：把 `fec0::/10` 加进 `_BLOCKED_NETWORKS`。本次不改。
6. `app.py:61-68` 未拦截文档网段 `192.0.2.0/24`、`198.51.100.0/24`、`203.0.113.0/24`、`2001:db8::/32`。探针放行。DECISIONS.md:32 同样不修。修法：加入黑名单。本次不改。
7. `static/index.html:57` 在宽度 ≤760px 时 `aside{display:none}`，退订、分类、退出只在侧栏里。修法：窄屏改成可打开的侧栏。
8. `tests/test_app.py:490` 把 `fetch_url` 桩成 4 元组，`app.py:651` 要解包 5 个值。抓取失败后 `site_url` 默认就是空串，断言仍能过。产品路径是对的（`probe_clean.py`）。修法：测试桩改成 5 元组。任务不许改测试，本次不动。
9. `fastapi\testclient.py:1` 的 StarletteDeprecationWarning。修法：升级 httpx/starlette。DECISIONS.md:25 禁止改依赖版本，本次不动。
10. 版权人缺失（LICENSE:190 仍是模板；源码无版权头）。修法：由实际版权人补一行声明。名字未核实，不改 LICENSE / UPSTREAM。
11. `app.py:36` User-Agent 里的 GitHub 地址在 README、UPSTREAM 都没有。修法：要么在 UPSTREAM 说明，要么改成真实可核对的联系地址。未联网核实，本次不改。
12. `app.py:853` 的 `offset` 没有夹到 ≥0（`limit` 在 `app.py:874` 已夹紧）。探针 `offset=-1` 返回 200 和文章，没有 500。修法：`offset = max(0, offset)`。

不把「强制改密」列为缺陷。DECISIONS.md:7-10 写明该项永久不采纳，README.md:9 与登录探针都是只提示。
