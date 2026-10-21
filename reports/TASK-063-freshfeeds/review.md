# freshfeeds 验收报告

结论：仓库能在本机跑通。依赖按 README 装上，`pytest` 27 项通过，服务在 `127.0.0.1:8000` 首页返回 200 后已关掉。没有 P0。P1 有 1 项：OPML 导入的 `htmlUrl` 不过滤 `javascript:`，会写入 `site_url` 并原样导出。本轮只修这一项。

## 本地跑通记录

环境：仓库 `E:\muse-bridge\in\TASK-063-freshfeeds`。虚拟环境放在 `E:\muse-bridge\work\TASK-063-freshfeeds\.venv`，没有写进仓库。解释器 Python 3.11.9（`py -3.11`）。

README 的 `py -m venv` 在本机失败，是启动器问题，不是项目缺陷：

```
py -3 --version
exit: 1
Unable to create process using 'E:\python.exe --version': ???????????

py -m venv E:\muse-bridge\work\TASK-063-freshfeeds\venv-readme-try
exit: 1
Unable to create process using 'E:\python.exe -m venv ...': ???????????
```

`py -0p` 显示默认 `py` 指向损坏的 `E:\python.exe`（3.14）。README 要求 Python 3.10+，改用 `py -3.11`（3.11.9）建虚拟环境，exit 0。标为环境限制。

安装（venv 的 python）：

```
python -m pip install -r E:\muse-bridge\in\TASK-063-freshfeeds\requirements.txt
```
exit 0。`Successfully installed ... fastapi-0.156.7 ... python-multipart-0.0.32 ... uvicorn-0.54.0`。传递依赖被解析为 starlette 1.9.0、pydantic 2.14.1（文件里没钉这些）。

```
python -m pip install -r E:\muse-bridge\in\TASK-063-freshfeeds\requirements-dev.txt
```
exit 0。`Successfully installed ... httpx-0.28.1 ... pytest-9.1.1`。

全量测试（在仓库目录）：

```
python -m pytest tests\ -q --tb=short -p no:cacheprovider --basetemp=E:\muse-bridge\work\TASK-063-freshfeeds\pytest-tmp
```
exit 0：

```
...........................                                              [100%]
27 passed, 1 warning in 6.86s
```

警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 来自 `fastapi/testclient.py:1`。没有失败项。没有依赖外网的用例（抓取用例打本地 `HTTPServer` 或打桩）。

起服务：工作目录 `smoke_server.py` 用与 `app.py` 的 `__main__` 相同的参数调用 uvicorn（同一 `app`，`127.0.0.1:8000`）。数据库用工作目录的 `smoke.db`。结束时 `server.should_exit`，没有用 taskkill。命令 exit 0。输出片段：

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
SERVER_STARTED True
GET / HTTP/1.1" 200 OK
HIT / 200 text/html; charset=utf-8 b'<!DOCTYPE html>...<title>freshfeeds · 清泉阅读</title>...'
GET /health HTTP/1.1" 404 Not Found
HIT /health HTTP 404 b'{"detail":"Not Found"}'
GET /api/me HTTP/1.1" 401 Unauthorized
HIT /api/me HTTP 401 b'{"detail":"未登录"}'
GET /docs 404
GET /openapi.json 404
POST /api/login HTTP/1.1" 200 OK
LOGIN 200 must_change_password true
STOPPED True
Application shutdown complete.
Finished server process [36924]
```

首页正常。没有健康检查路由，README 也没写 `/health`，404 不算缺陷。未登录接口会 401。默认账号能登录。文档页按代码关闭。服务已停。

另有两次只在本机跑的探测（`probe_security.py`、`probe_pin.py`，均 exit 0），证据见下面 P1 和 P2。没有抓外网页面。

## README 与实际不符处

核对过且与代码一致的，不展开：Token 24 小时（README.md:9，app.py:34）、默认账号 admin/admin123（README.md:42，app.py:272）、只提示不强制改密（README.md:9，接口没有 `must_change` 拦截）、HOST/PORT 默认值（README.md:57-58，app.py:1046-1047）、数据库路径相对 app.py（README.md:59，app.py:31）、刷新间隔 30 分钟（README.md:60，app.py:32）、目录里点名的文件都在。

不符与未写明的实际行为：

1. README.md:10 写「响应是 HTML 且正文前 500 字符不含订阅源」才自动发现并改写订阅地址。app.py:655 的条件是内容类型字符串包含 `html`，并且前 500 字符里没有子串 `<feed` 或 `<rss`。RSS 1.0 的 `<rdf:RDF` 不算「已经是订阅源」，仍会走发现逻辑。`text/html` 以外、靠正文判断的页面也不会发现。
2. README.md:61 写 `FRESHFEEDS_SCHEDULER` 默认 `1`、设为 `0` 关闭。默认值与 app.py:33 一致。关闭条件是字符串不等于 `"0"`，所以 `false`、`off`、`no`、空字符串都仍然开启。表里没有写反，但关闭条件比「布尔开关」更窄。
3. README.md:72 写运行/开发依赖「版本钉死」。requirements.txt:1-3 与 requirements-dev.txt:2-3 只钉了直接依赖。本次安装实际解析出 starlette 1.9.0、pydantic 2.14.1 等，文件里没有钉住。

## 许可证与署名核查

没有访问 GitHub。`UPSTREAM.md` 里的 `source_commit` 和「版权行逐字来自 main.go」都标未核实。

- 许可证类型自洽。README.md:76 写 Apache License 2.0。LICENSE 正文是 Apache License 2.0 标准条款。UPSTREAM.md:5 写上游也是 Apache-2.0。
- 本仓库著作权人缺失。LICENSE:190 仍是模板 `Copyright [yyyy] [name of copyright owner]`。app.py:1 和 static/index.html:1 都没有版权行或 Apache 样板头。这是授权通知没落地，不是一份写错的许可证正文。按任务约束，没有外网证据就不改 LICENSE。
- UPSTREAM.md:6 的 `attribution: Copyright The Miniflux Authors. All rights reserved.` 和 UPSTREAM.md:11-12 放在一起读，后者说明这行是上游 `main.go` 文件头的摘录，并声明本项目未复制上游源码。顶栏容易被读成「本仓库版权属于 Miniflux」，但下文没有把这句话写成事实性的假归属。上游 commit 与摘录是否逐字，未核实，因此不改 UPSTREAM.md。
- 仓库没有 NOTICE 文件。LICENSE 附录里关于 NOTICE 的句子是「如果发行物带了 NOTICE 才要保留」。UPSTREAM.md:11 也写上游没有 NOTICE。这里没有互相打架。
- app.py:35 的 User-Agent 指向 `https://github.com/ZZmkk88/freshfeeds`，UPSTREAM.md:3 的上游是 `https://github.com/miniflux/v2`。一个是产品标识，一个是设计来源，可以并存。ZZmkk88 这个地址是否真实存在，未核实。

## 分级修复清单

### P0

无。测试 27 项通过，服务能监听并返回首页。`py -m venv` 失败是本机 Python 启动器损坏，不记成项目缺陷。

### P1

1. OPML 导入的 `htmlUrl` 不经 `_clean_url`，`javascript:` 会写入 `feeds.site_url`。刷新时若解析出的站点链接为空，app.py:690 的 `site_url or feed["site_url"]` 会把这个值留下，导出时 app.py:934 写回 `htmlUrl`。探测：导入 `htmlUrl="javascript:alert(1)"` 且频道 `<link>` 为空，结果 `site='javascript:alert(1)'`，导出含 `javascript:`。解析路径已经清洗（app.py:590、619），导入路径漏了（app.py:998）。修法：导入时对 `htmlUrl` 调用 `_clean_url`，非 http(s) 入库为空串。

### P2

不在本轮改。

1. app.py:60-68 的网段黑名单没有 `fec0::/10`。探测 `http://[fec0::1]/` 被放行。这是已废弃的 IPv6 站点本地地址。修法：把 `fec0::/10` 加进 `_BLOCKED_NETWORKS`。`198.18.0.0/15` 是 DECISIONS.md:16 刻意放行，不要加。
2. 文档用地址未拦截：探测 `http://192.0.2.1/`、`http://198.51.100.1/`、`http://[2001:db8::1]/` 均放行（app.py:60-68）。不是内网。修法：如需更严，把 TEST-NET 与 `2001:db8::/32` 加入黑名单。
3. 退出登录不吊销服务端 token。static/index.html:172 只清 `localStorage`。探测 `POST /api/logout` 为 404，之后 `GET /api/me` 仍 200。改密会删掉其他会话（app.py:366-370）。修法：增加注销接口，删除当前 token，前端退出时调用。
4. 带用户信息的源地址被拒绝。探测 `http://user:pass@8.8.8.8/feed` 在 app.py:125-152 报「主机名含混」（`InvalidURL nonnumeric port: 'pass@8.8.8.8'`）。方向是拒绝，不是绕过。修法：把 userinfo 和主机拆开再比较。本轮不动，避免改 SSRF 比较。
5. 默认口令 `admin` / `admin123`，且不强制改密。DECISIONS.md:7-10 写明永久不采纳「强制改密」。不修。
6. httpx/Starlette 弃用警告。DECISIONS.md:33 与任务都不许改依赖版本号。不修。
7. tests/test_app.py:490 把 `fetch_url` 打成 4 元组，app.py:644 按 5 元组解包，刷新会进异常分支，`site_url` 停在默认空串，断言仍能过。解析器本身会清掉 `javascript:`（本报告的 parse_feed 探测）。修法：mock 改成 5 元组。不许改测试，不修。
8. tests/test_app.py:261 的重定向用例，第一跳就是 `127.0.0.1`，真实校验会在第一跳拒绝，测名里的「第二跳」没有被单独打到。不许改测试，不修。
