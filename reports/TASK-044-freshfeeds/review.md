# freshfeeds 验收审查

结论：仓库能装、能测、能起。修复前 `pytest` 26 项通过（6.23s），`python app.py` 在 `127.0.0.1:8000` 首页返回 200。没有 P0。有 3 个已用本地探针证实的 P1（前端属性未转义引号、抓取校验放行非 http(s) / 解析失败 / 十进制回环写法、订阅源 XML 会展开内部实体）。这 3 项已改完，命令和输出在 `fix-report.md`。改完后全量测试仍是 26 passed（6.52s）。清单里的文件:行号是修改前的位置。上游 commit 与版权原文未联网，标「未核实」。

## 本地跑通记录

环境：本机 `python --version` 为 Python 3.11.9。README 写的 `py -m venv` 在本机不能用（环境限制，不是项目缺陷）：

```
py -3 --version
Unable to create process using 'E:\python.exe --version': ???????????
```

虚拟环境：`E:\muse-bridge\work\TASK-044-freshfeeds\venv`。依赖安装命令与结果：

```
E:\muse-bridge\work\TASK-044-freshfeeds\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-044-freshfeeds\requirements-dev.txt
```

exit 0。装上 `fastapi==0.156.7`、`uvicorn==0.54.0`、`python-multipart==0.0.32`、`httpx==0.28.1`、`pytest==9.1.1`，无版本冲突。

全量测试（`TEMP`/`TMP` 指到 `E:\muse-bridge\work\TASK-044-freshfeeds\tmp`，`PYTHONDONTWRITEBYTECODE=1`）：

```
E:\muse-bridge\work\TASK-044-freshfeeds\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
..........................                                               [100%]
26 passed, 1 warning in 6.23s
EXIT=0
```

警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 出自 `fastapi\testclient.py:1`。DECISIONS.md:25 写明这条不修，且任务不许改已有依赖版本号。

起服务：子进程执行仓库里的 `app.py`，`HOST=127.0.0.1`，`PORT=8000`，数据库放在工作目录。输出片段：

```
PORT_8000_READY True
GET / status 200 ctype text/html; charset=utf-8
GET /health status 404
GET /api/health status 404
GET /api/me status 401
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:64859 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:64862 - "GET /api/me HTTP/1.1" 401 Unauthorized
```

首页正文以 `<title>freshfeeds · 清泉阅读</title>` 开头。`/api/me` 未登录时的 `detail` 为「未登录」。探测结束后进程已停。`/health` 与 `/api/health` 为 404；README 没有这些路径，不记缺陷。

## README 与实际不符处

1. README.md:10 写「填网站首页地址时会自动发现源」。app.py:507-510 只在响应 `Content-Type` 含 `html`，且正文前 500 字符里没有 `<feed` / `<rss` 时，才调用 `discover_feed_url`。其它 Content-Type 的首页不会发现源。

2. README.md:9 写「首次登录强制提示改密码」。static/index.html:158-159 先 `enterApp()` 进入主界面，再 `showModal()`。app.py 没有在 `must_change=1` 时对其它接口返回 403。DECISIONS.md:7-10 已定「只提示、不强制」，此项不修。

3. README.md:63-69 的目录只列了 `app.py`、`static/index.html`、`tests/test_app.py`、`NOTES.md`、`UPSTREAM.md`。仓库根上还有 `DECISIONS.md`、`requirements.txt`、`requirements-dev.txt`、`LICENSE`。`LICENSE` 在 README.md:73 另有一句，目录节本身没列。

4. README 的运行与配置节没有写新密码长度。app.py:261 在新密码短于 6 位时返回 400「新密码至少 6 位」。static/index.html:130 的占位文案写了「至少 6 位」。

以下与代码一致，不算不符：Token 24 小时（app.py:33、app.py:239）、默认 `127.0.0.1:8000`（app.py:896-899）、数据库默认路径相对 `app.py`（app.py:30，README.md:59）、定时刷新默认 30 分钟且 `FRESHFEEDS_SCHEDULER=0` 可关（app.py:31-32）、测试命令（README.md:48，本机 26 passed）。

## 许可证与署名核查

- README.md:73 写 Apache License 2.0，见 `LICENSE`。`LICENSE` 是 Apache-2.0 标准条款（第 1–9 节 + 附录）。附录 LICENSE:190 仍是占位符 `Copyright [yyyy] [name of copyright owner]`，本仓库版权人没有填上。这是附录没套用到本项目，不是把许可证种类写错。按任务约束不改 `LICENSE`。
- UPSTREAM.md:3-5 写上游 `https://github.com/miniflux/v2`、commit `bdd8087d9cf7a20ca7e800948389e8a7e86445da`、Apache-2.0，以及 `Copyright The Miniflux Authors. All rights reserved.`。UPSTREAM.md:11-13 说明该版权行是上游 `main.go` 文件头的逐字引用，并声明本仓库是独立实现、未复制上游源码。禁网，上游 commit、LICENSE 原文和 `main.go` 那一行均「未核实」。在未核实前，不把「All rights reserved」改成事实错误：它出现在「上游溯源」里，本仓库自身许可证仍是 Apache-2.0。
- 本仓库没有 `NOTICE` 文件。UPSTREAM.md:11 称上游也没有 NOTICE。「未核实」上游仓库。
- NOTES.md:4-6 与 UPSTREAM 的上游名称、许可证、commit 一致。app.py:1-6 的模块说明只写「开源社区 RSS 阅读工具」，没有写 Miniflux；点名在 UPSTREAM.md 与 NOTES.md。
- app.py:34 的 User-Agent 是 `freshfeeds/1.0 (+https://github.com/ZZmkk88/freshfeeds)`。这个地址和 UPSTREAM.md:3 的 miniflux 仓库不是同一个。该 GitHub 地址「未核实」。不改这一行：没有证据证明它是假声明，只是与上游溯源文档不是同一 URL。
- DECISIONS.md 里已宣称修好的行为，和当前代码、已通过的测试一致：改密吊销其它 token（app.py:274-278）、RSS 1.0 命名空间标题（app.py:450-454）、`limit` 夹到 1–200（app.py:719）、分类不存在的报错（app.py:644）、198.18/15 不拦截（探针 `http://198.18.0.1/` 为 ALLOW）。不把这些已决事项再开成缺陷。

## 分级修复清单

### P0

无。依据：全量测试 26 passed；`python app.py` 监听 `127.0.0.1:8000`，`GET /` 为 200。

### P1

1. **前端把订阅源可控字符串放进 HTML 属性，转义函数不处理引号。** static/index.html:147 的 `esc` 用 `textContent`/`innerHTML`，不转义 `"` 与 `'`。static/index.html:179 把源地址或 `last_error` 放进 `title="..."`。static/index.html:194 经 `safeHref`（static/index.html:148）把条目 URL 放进 `href="..."`。app.py:391-397 的 `_clean_url` 对 `https://example.com/"onmouseover="alert(1)` 原样返回（探针）。修法：`esc` 在一次替换里转义 `& < > " '`。

2. **抓取前的地址校验会放行不该抓的 URL。** app.py:80-95。探针：`ftp://93.184.216.34/feed.xml` 为 ALLOW，OPML 导入后 `added:1` 并入库；`resolve_host_addresses` 抛 `OSError` 时函数直接 return（FAIL_OPEN）；`http://2130706433/feed.xml` 通过 `POST /api/feeds` 返回 200 并入库，而 `socket.inet_aton("2130706433")` 为 `127.0.0.1`。添加接口 app.py:628 会拒绝 `gopher://`，OPML 路径 app.py:826-833 只调用 `ensure_fetch_allowed`，没有同样的 scheme 限制。修法：只允许 `http`/`https`；`inet_aton` 能解析的主机按该 IPv4 做网段判断；DNS 失败改为抛 `BlockedUrlError`。

3. **订阅源 XML 会展开内部实体，OPML 路径已拒绝 DTD，解析源没有。** app.py:402 `ET.fromstring`。探针：`<!ENTITY a "XY"><!ENTITY b "&a;&a;&a;">` 使标题变成 `XYXYXY`。外部实体未被展开（`ParseError undefined entity`）。OPML 在 app.py:814-815 拒绝 `<!DOCTYPE` / `<!ENTITY`。修法：`parse_feed` 在解析前对同一类声明直接 `ValueError`。

### P2

1. **校验和真正连接各做一次 DNS。** app.py:301 调用 `ensure_fetch_allowed`，app.py:309 的 `urlopen` 会再解析。修法：连到已经判定过的 IP，并保留原来的 Host 与 HTTPS SNI。本轮不改连接方式，避免半成品把 HTTPS 订阅读坏。本机也没有做出一次成功的重绑定。

2. **源的站点链接不清洗。** app.py:456-457 把 channel 的 `link` 原样当作 `site_url`。探针：`javascript:alert(1)` 会留下。app.py:850 导入 OPML 时 `htmlUrl` 同样原样入库，导出在 app.py:786。修法：入库前走 `_clean_url`。当前页面没有把 `site_url` 当成链接渲染。

3. **`offset` 没有下限。** app.py:698 与 app.py:720 只夹了 `limit`。探针：有 1 条数据时 `offset=-1` 仍 200 并返回该条。修法：`offset` 小于 0 时改为 0。

4. **README 与实现对不齐的 4 条（见上节）。** 修法：改 README 对应句，补目录和密码长度，把「强制提示」改成与 DECISIONS.md:7 一致的「只提示」。不改「不强制改密」的实现。

5. **LICENSE 附录版权占位符未填。** LICENSE:190。修法：填本仓库实际版权人。版权人未知，且任务不许擅自改 LICENSE 的事实声明，本轮不填。

6. **没有健康检查路由。** 路由只有 app.py:887 的 `GET /`。探针 `/health`、`/api/health` 为 404。README 未承诺。修法：若需要，另加只返回 200 的 `/health`。本轮不加。

7. **FastAPI 默认文档页开着。** app.py:116 未关闭 `docs`/`openapi`。修法：`FastAPI(..., docs_url=None, redoc_url=None, openapi_url=None)`。本轮不改。

8. **条件请求头的值未先去掉 CR/LF。** app.py:305-307 把库存的 ETag / Last-Modified 放进请求头。探针：`add_header` 接受含 `\r\n` 的值。本机 CPython 3.11 `http/client.py` 的 `putheader` 在发送前拒绝非法头值，没有打出成功注入。修法：写入请求头前去掉 `\r` 和 `\n`。

9. **已入库文章内容变更不会更新。** app.py:523 `INSERT OR IGNORE`。修法：冲突时按需更新标题、链接和正文。README 只承诺不重复入库，本轮不改。

10. **定时线程先睡满一个间隔再刷。** app.py:878-880。修法：若要启动后先刷一轮，把 `sleep` 放到 `refresh_all` 之后。本轮不改。

11. **搜索把 `%` 和 `_` 交给 SQL LIKE。** app.py:715-717。修法：转义这两个通配符。同一登录用户只能搜到自己的库，不构成越权。

12. **httpx / Starlette 弃用警告。** 测试输出已引用。DECISIONS.md:25 不修。修法会改 `requirements-dev.txt` 里的版本或换客户端，任务不许改已有依赖版本号。

13. **默认口令 `admin` / `admin123`。** README.md:42、app.py:180-181、static/index.html:69。DECISIONS.md:7 禁止把强制改密加回来。监听默认是 127.0.0.1（app.py:898）。不修。
