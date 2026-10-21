# freshfeeds 验收审查

结论：测试 30 项通过，服务能在 127.0.0.1:8000 起来，首页和登录正常，没有 P0。有 2 个已复现的 P1（订阅地址被错误改写、OPML 的 javascript: 站点地址入库），下面按清单修。上游 commit 与 main.go 署名未联网核对，标为未核实。

## 本地跑通记录

环境：本机 `python --version` 为 Python 3.11.9。README 写的 `py -m venv` 在本机不可用（`py -3 --version` 退出码 1：`Unable to create process using 'E:\python.exe --version'`）。这是本机启动器损坏，不是仓库缺陷。虚拟环境放在 `E:\muse-bridge\work\TASK-067-freshfeeds\venv`，避免在仓库里留下删不掉的 `.venv`。

依赖（退出码 0，无版本冲突）：

```
E:\muse-bridge\work\TASK-067-freshfeeds\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-067-freshfeeds\requirements.txt
E:\muse-bridge\work\TASK-067-freshfeeds\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-067-freshfeeds\requirements-dev.txt
```

装上 fastapi==0.156.7、uvicorn==0.54.0、python-multipart==0.0.32、httpx==0.28.1、pytest==9.1.1。

全量测试（工作目录为仓库根，临时文件指到任务工作目录）：

```
E:\muse-bridge\work\TASK-067-freshfeeds\venv\Scripts\python.exe E:\muse-bridge\work\TASK-067-freshfeeds\run_pytest.py
```

```
..............................                                           [100%]
30 passed, 1 warning in 6.02s
```

警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 来自站点包 `fastapi/testclient.py:1`，不是断言失败。

起服务一次（`FRESHFEEDS_DB` 指到工作目录的 `smoke.db`，调度保持默认开启，HOST/PORT 用默认）：

```
GET / -> 200  text/html  正文以 <!DOCTYPE html> 开头，标题含 freshfeeds
POST /api/login {"username":"admin","password":"admin123"} -> 200  must_change_password=true
GET /api/me（带 Bearer）-> 200  {"username":"admin","must_change_password":true}
POST /api/feeds/refresh-all -> 200  {"feeds":0,"added":0,"failed":0}
GET /health -> 404  {"detail":"Not Found"}
GET /api/health -> 404  {"detail":"Not Found"}
GET /docs 、/redoc 、/openapi.json -> 404
GET /api/me 无令牌 -> 401  {"detail":"未登录"}
```

uvicorn 日志：`Uvicorn running on http://127.0.0.1:8000`。检查完后已关掉，端口不再监听。进程退出码 1 来自主动 terminate，日志无 traceback。README 没写健康检查 URL，404 不算跑不起来。

未用图形浏览器点界面。登录提示框的存在以接口字段和 `static/index.html:127-132`、`:163` 为准。

## README 与实际不符处

1. README.md:10 写「从页面自动发现源（并改写该订阅的地址）」，按成功发现来理解。app.py:664-666 在 `parse_feed`（app.py:667）之前就 `UPDATE feeds SET url`，解析抛错后 app.py:668-674 的 `except` 会把这次更新一起提交。探针：订阅 `http://orig.example/`，页面指向一份非法 XML，结果库里的地址变成 `http://orig.example/bad.xml`，`last_error` 为 `syntax error: line 1, column 0`。没有改地址的接口，原地址找不回来。

2. README.md:10 写「正文前 500 字符不含订阅源」才自动发现。app.py:662 的判断是 content-type 含 `html`，且前 500 个字符里没有子串 `<feed` 和 `<rss`。RSS 1.0 的根标签在 app.py:601 一带是 `rdf:RDF`，带前缀的 `<atom:feed` 也不含这两个子串，仍会走进发现逻辑。

其余 README 条目与代码一致，抽查过：默认账号 admin/admin123（app.py:273-274）、Token 24 小时（app.py:34、335）、只提示不强制（static/index.html:69、131）、环境变量默认值（app.py:31-33、1055-1056）、一键刷新全部（冒烟 `POST /api/feeds/refresh-all` 200）、目录里列出的文件都在。

## 许可证与署名核查

- README.md:76 写 Apache License 2.0，指向 LICENSE。LICENSE 是 Apache-2.0 标准条款全文。附录里的 `Copyright [yyyy] [name of copyright owner]` 是许可证自带的填写示例，不是本仓库已经声明的版权人。源码文件头没有另写版权行。这是「没填自己的版权主体」，不是两份文件互相打架。本次不改 LICENSE。
- UPSTREAM.md:3-6 写上游 `https://github.com/miniflux/v2`，commit `bdd8087d9cf7a20ca7e800948389e8a7e86445da`，许可证 Apache-2.0，署名 `Copyright The Miniflux Authors. All rights reserved.`，并说明该行抄自 `main.go` 的 `SPDX-FileCopyrightText`。任务禁止抓取外部页面，这三项 **未核实**。
- UPSTREAM.md:12 写只借鉴模型、代码独立实现、未复制上游源码。仓库里是 Python 单文件后端加一个 HTML，没有 Go 源码，也没有 Miniflux 的目录结构。这个「未复制源码」的说法和树内文件相符。commit 是否等于上游默认分支 HEAD，未核实。
- 「All rights reserved」出现在 UPSTREAM 的上游署名引用里。本仓库对外许可以 LICENSE 的 Apache-2.0 授权条款为准，UPSTREAM.md:8-12 已说明那行字是上游文件头，不是给本仓库加的额外保留。两边这样读不冲突。
- app.py:36 的 User-Agent 指向 `https://github.com/ZZmkk88/freshfeeds`。和 UPSTREAM 的上游地址不是同一个仓库。该 GitHub 地址是否存在，未核实，不把它写成假署名。

## 分级修复清单

### P0

无。pytest 30 passed；服务能监听 8000，首页 200，登录 200，刷新全部 200。

### P1

1. **P1-1 发现失败仍改掉订阅地址（数据丢失）**。app.py:664-666 在解析前更新 `feeds.url`，app.py:668-674 的异常处理会提交这次更新。修法：只有 `parse_feed` 成功之后才 `UPDATE` 新地址；解析失败保持用户原来填写的 URL。
2. **P1-2 OPML 的 htmlUrl 不清洗，javascript: 会入库并被导出**。app.py:1005 把 `htmlUrl` 原样写入 `site_url`。抓取失败时刷新不会覆盖它（探针导出仍含 `javascript:`）。解析出的站点链接为空时，app.py:697 的 `site_url or feed["site_url"]` 会继续保留这份旧值（探针 `javascript:alert(2)`）。修法：入库前对 htmlUrl 调用已有的 `_clean_url`，非 http(s) 记成空串。

### P2

1. **P2-1** README.md:10 与 app.py:662。前 500 字符只排除 `<feed` / `<rss`，不认 RSS 1.0 和带前缀的 Atom。修法：发现前若已经能被 `parse_feed` 解析成功，就不要改地址。本轮不改，避免动发现启发式。
2. **P2-2** app.py:853、app.py:875。`limit` 被夹到 1~200，`offset=-1` 没有夹紧。本机探针返回 200 并给出文章列表，不是 500。修法：`offset` 小于 0 时按 0。本轮不改。
3. **P2-3** static/index.html:172。退出只删 `localStorage` 的 token。`POST /api/logout` 探针结果 404。服务端会话要等 24 小时或靠改密吊销。修法：增加注销接口并在退出时调用。README 没写服务端注销，本轮不改。
4. **P2-4** static/index.html:57。宽度不超过 760px 时侧栏 `display:none`，没有别的入口，窄屏上到不了退出、分类和源列表。修法：窄屏加一个打开侧栏的按钮。本轮不改界面。
5. **P2-5** app.py:569。条目标题和正文有截断，`author` 原样入库、不截断。修法：作者字段同样去标签并限制长度。本轮不改。
6. **P2-6** tests/test_app.py:490。`fetch_url` 的假返回是 4 元组，真实函数在 app.py:474 返回 5 元组。解包失败后走 502，`site_url` 停在默认空串，`test_site_url_javascript_blanked` 仍能过，没有覆盖到频道链接清洗。不许改测试。用正确 5 元组另测时，解析路径会把 `javascript:` 站点链接收成空串（探针 `site_url ''`）。
7. **P2-7** 全量测试的 StarletteDeprecationWarning。DECISIONS.md:25 已决定不改依赖版本，任务也不许改 requirements 里的版本号。不修。
8. **P2-8** 源码与 LICENSE 附录都没有本仓库自己的版权人。不是事实写错。不改 LICENSE。

不修、也不算缺陷：198.18.0.1 放行（DECISIONS.md:16，假 IP DNS）；首登只提示不强制改密（DECISIONS.md:6-10）。SSRF 抽查（回环、十进制/十六进制/八进制、IPv6 映射、6to4、NAT64、Teredo、169.254.169.254、userinfo 含混主机、重定向第二跳、DNS 钉死）均按现有实现拦住或钉住，不单列修复项。
