# freshfeeds 验收审查

结论：依赖能装上，31 项测试通过，服务能起来并完成登录。README 有 4 处和代码不一致。许可证类型是 Apache-2.0，版权人没填，上游 commit 与 SPDX 原文本次未联网核实。没有新的 P0，也没有要改代码的 P1。

## 本地跑通记录

环境：仓库 `E:\muse-bridge\in\TASK-091-freshfeeds`。README 写的 `py -m venv` 在本机失败（`py -3 -V` → `Unable to create process using 'E:\python.exe -V'`）。实际解释器是任务 venv：

```
Python 3.11.9
E:\muse-bridge\env\TASK-091-freshfeeds\Scripts\python.exe
```

3.11.9 满足 README 第 22 行的 Python 3.10+。没有在仓库里建 `.venv`，避免把环境写进工作区。

安装（exit 0）：

```
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

装上 `fastapi==0.156.7`、`uvicorn==0.54.0`、`python-multipart==0.0.32`、`httpx==0.28.1`、`pytest==9.1.1`。

测试命令是 work 目录里的 `run_pytest.py`（把 TEMP 指到 `E:\muse-bridge\work\TASK-091-freshfeeds`，再跑 `tests/ -q`）。等价于 README 第 48 行的 `python -m pytest tests/ -q`。第一次因脚本没把仓库放进 `sys.path` 报 `ModuleNotFoundError: No module named 'app'`，这是启动脚本的问题。改完后：

```
31 passed, 1 warning in 6.94s
```

警告原文：

```
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

来自 `fastapi/testclient.py:1`，退出码仍是 0。

服务：默认 8000 被本机 PID 35756 占用，不是本仓库。错误原文：

```
ERROR:    [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): 通常每个套接字地址(协议/网络地址/端口)只允许使用一次。
```

当时 `http://127.0.0.1:8000/` 返回的标题是「weblens · 网站访问统计」。未结束该进程。用 `PORT=18765`、`FRESHFEEDS_DB` 指向 work 目录再起，日志：

```
INFO:     Uvicorn running on http://127.0.0.1:18765 (Press CTRL+C to quit)
```

实机结果：

- `GET /` → 200，`text/html`，标题 `freshfeeds · 清泉阅读`
- `GET /health`、`GET /api/health` → 404 `{"detail":"Not Found"}`。代码里没有健康检查路由
- `GET /docs`、`GET /openapi.json` → 404（`app.py:206-208` 关掉了文档）
- `POST /api/login` `admin` / `admin123` → 200，`must_change_password` 为 true
- 带 token 的 `GET /api/me` → 200，`GET /api/feeds` → 200 `[]`
- 不带 token 的 `GET /api/feeds` → 401，`detail` 为「未登录」

随后停掉 18765。`netstat` 上该端口只剩 `TIME_WAIT`，没有 `LISTENING`。

另外在本机探针里确认了：内网字面地址、localhost、6to4/NAT64/Teredo 内嵌私网会被拒；DNS 钉死能连上本地测试服务器；302 第二跳会再校验；`HTTP_PROXY=http://127.0.0.1:1` 时抓取仍直连。这些都不走外网页面。

## README 与实际不符处

核对过且一致的，这里只列代表：Token 24 小时（README.md:9，`app.py:34`）、默认账号（README.md:42，`app.py:273-274`）、五个环境变量的默认值（README.md:57-61，`app.py:31-33` 与 `app.py:1053-1056`）、只提示不强制改密（README.md:9 与 `index.html:69,128`）、目录清单（README.md:63-72）和仓库文件一致。

不符：

1. README.md:10 写「响应是 HTML 且正文前 500 字符不含订阅源」才自动发现源。`app.py:662` 的条件是 Content-Type 字符串里含 `html`，并且前 500 字符里没有字面量 `<feed` 和 `<rss`。RSS 1.0 的 `<rdf:RDF` 不算在内。发现逻辑在 `app.py:486-497`，只认第一个 `type="application/rss+xml"` 或 `atom+xml` 的 link。
2. README.md:10 写支持 RSS 2.0。`app.py:601-613` 在非 RDF 时只找无命名空间的 `channel` / `title` / `item`。整份带默认命名空间的 RSS，`root.tag == "rss"` 不成立，标题和条目会空。规范里的无命名空间 RSS 2.0 可以解析，测试用的也是这种。
3. README.md:12 写进程内定时刷新默认每 30 分钟一轮。`app.py:1036-1037` 进入循环后先 `sleep(REFRESH_MINUTES * 60)` 再 `refresh_all()`。进程起来后的第一轮在 30 分钟之后，启动当时不会先抓。
4. README.md:18 写抓取失败不会假装成功。界面确实会用 `last_error` 标 ⚠️（`index.html:183`）。但 `app.py:816-819` 在首次抓取抛 HTTPException 时仍返回 HTTP 200，body 带 `warning`，订阅已经入库。
5. README.md:72 写运行/开发依赖版本钉死。`requirements.txt:1-3` 和 `requirements-dev.txt:2-3` 只钉了直接依赖。本次安装解析出的传递依赖没有写进文件，例如 starlette 1.9.0、pydantic 2.14.1。

## 许可证与署名核查

种类一致。`LICENSE:2-3` 是 Apache License Version 2.0 标准正文。README.md:75 写 Apache License 2.0。`UPSTREAM.md:5` 写 `license: Apache-2.0`。三处说的是同一种许可证。

版权主体没有填。`LICENSE:190` 仍是附录占位符 `Copyright [yyyy] [name of copyright owner]`。`app.py`、`static/index.html`、README 都没有本项目的版权行或 SPDX 头。

上游署名只出现在 `UPSTREAM.md:3-6`：`source_url` 为 `https://github.com/miniflux/v2`，`source_commit` 为 `bdd8087d9cf7a20ca7e800948389e8a7e86445da`，attribution 为 `Copyright The Miniflux Authors. All rights reserved.`。`UPSTREAM.md:11-12` 说这行来自上游 `main.go` 的 SPDX，并说本仓库没有复制上游源码。本次按任务要求没有访问 GitHub，这两句标为未核实。仓库里没有 Go 文件，也没有 NOTICE。`app.py:36` 的 User-Agent 是 `freshfeeds/1.0 (+https://github.com/ZZmkk88/freshfeeds)`，这个地址不在 README 和 UPSTREAM 里，本次也未打开核实。

结论：许可证类型自洽。本项目版权人未署名，和 Apache 附录要求的填法不一致。上游 commit 与 main.go 署名原文未核实，不能据此改 LICENSE 或 UPSTREAM。

## 分级修复清单

### P0

无。测试 31 项通过。服务在空闲端口上能监听，首页 200，登录可用。8000 起不来是本机已被 weblens 占用。

### P1

无。下面几项查过，不列入待修：

- 内网、回环、链路本地、元数据地址、十进制/十六进制回环、IPv4-mapped、6to4、NAT64、Teredo 内嵌私网，探针里都被 `ensure_fetch_allowed` 拒绝（`app.py:61-104`）。
- `198.18.0.1` 放行是 `DECISIONS.md:16` 的既定决定，`tests/test_app.py:258` 锁定为 True。改掉会使现有测试失败，而测试不许改。
- 空 `ProxyHandler` 生效：设了指向 `127.0.0.1:1` 的 `HTTP_PROXY` 后，本地抓取仍返回 `direct-ok`（`app.py:184-188`）。
- 默认口令不强制修改是 `DECISIONS.md:7-10` 写明永久不采纳的决定。现有测试在 `must_change_password` 仍为 true 时直接调用业务接口。
- `/docs` 与 `/openapi.json` 实机为 404，与 `app.py:206-208` 一致。

### P2

1. README.md:10 与 `app.py:662,486-497`。修法：按代码改 README 的发现条件，或让判断覆盖 RSS 1.0 根元素。
2. README.md:10 与 `app.py:601-613`。修法：README 写明只保证无默认命名空间的 RSS 2.0，或解析时去掉元素命名空间再找 channel/item。
3. README.md:12 与 `app.py:1036-1037`。修法：README 写明第一轮在进程启动一个间隔之后，或先刷新再睡眠。
4. README.md:18 与 `app.py:816-819`。修法：README 写明首次抓取失败仍返回 200 且订阅保留，或改成非 2xx。
5. README.md:72 与 `requirements.txt:1-3`。修法：把「版本钉死」改成「直接依赖钉死」。不改已写上的版本号。
6. `app.py:447` 的 docstring 写返回四元组，`app.py:474-480` 实际返回五个值。`tests/test_app.py:490` 的桩仍返回四个值，刷新会在解包处失败，空的 `site_url` 让断言通过。修法：改 docstring。测试桩不能动。
7. `app.py:61-68` 未拦截 `fec0::/10`（探针 ALLOW `fec0::1`）、`192.0.2.0/24`、`198.51.100.0/24`、`203.0.113.0/24`、`100::/64`。修法：补进网段清单。`DECISIONS.md:32` 写明 fec0 和文档地址段维持现状，本轮不改。
8. `app.py:853` 与 `app.py:875` 只夹了 limit，没有夹 offset。探针里 `offset=-1` 与 `offset=0` 都返回全部 3 条。修法：`offset = max(0, offset)`。
9. `app.py:870-872` 把用户输入直接拼进 `LIKE %...%`。探针 `q=%` 命中全部 3 条。修法：转义 `%` 和 `_`。
10. `app.py:570` 的 author 没有截断，title/content/guid 有。修法：给 author 加长度上限。
11. 实机 `GET /health` 404，`app.py` 没有该路由。README 没承诺健康检查。修法：若要探活，加一个不访问外网的 `/health`。
12. 测试警告见 `DECISIONS.md:25`。修法：不改。任务不许改 requirements 里已有依赖的版本号，警告不影响通过。
13. `LICENSE:190` 版权行仍是占位符。修法：不改。没有可核实的版权人，不许凭空填写。
