# freshfeeds 验收报告

结论：依赖能装上，14 项测试通过，`python app.py` 能在 `127.0.0.1:8000` 启动，首页返回 200。没有 P0。有 6 条 P1，本轮修其中 5 条。改密不吊销已发出的 token 会让现有测试变红，且不许改测试，这一条不改代码。行号均指修复前的源码。

## 本地跑通记录

工作目录 `E:\muse-bridge\in\TASK-031-freshfeeds`。Python `3.11.9`（`python --version`）。README 要求 3.10+。

README.md:36 的 Windows 命令 `py -m venv .venv` 在本机不能用。`py -3 --version` 原文：

```
Unable to create process using 'E:\python.exe --version'
```

后面的系统提示在控制台里是乱码。改用 `python -m venv .venv`，再执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

退出码 0。装上的锁定版本包括 `fastapi-0.156.7`、`uvicorn-0.54.0`、`python-multipart-0.0.32`、`httpx-0.28.1`、`pytest-9.1.1`。

全量测试：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

```
14 passed, 1 warning in 2.17s
```

警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 来自 `.venv\Lib\site-packages\fastapi\testclient.py:1`。14 个用例都过了，没有失败项。没有用例去访问外网（`test_real_http_fetch` 起的是本机 `HTTPServer`）。

服务：`serve_smoke.py` 用虚拟环境执行仓库里的 `app.py`，数据库指到 `E:\muse-bridge\work\TASK-031-freshfeeds\freshfeeds.db`。启动日志：

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
GET / -> 200 type=text/html; charset=utf-8
GET /health -> HTTP 404 {"detail":"Not Found"}
GET /api/health -> HTTP 404 {"detail":"Not Found"}
GET /api/feeds -> HTTP 401 {"detail":"未登录"}
GET /docs -> 200
```

首页正文以 `<!DOCTYPE html>` 开头，标题区是 freshfeeds。README 只要求打开 `http://127.0.0.1:8000`，没有健康检查路由，`/health` 的 404 与文档一致。探测脚本随后 `terminate()` 子进程，退出码 1，发生在上述请求都返回之后。

修复前另有本地行为探测，命令和原文在 `run.md` 第 4 节。下面各条引用的输出都来自那三次探测。

## README 与实际不符处

1. README.md:10 写支持 RSS 1.0 解析。对一份带默认命名空间的 RSS 1.0 样本，`parse_feed` 的结果是源标题 `''`、站点链接 `''`、条目 1 条、条目标题 `RDF 文章`（`probe_behavior.py`：`RDF '' '' 1 RDF 文章`）。app.py:343-344 用无命名空间的 `title` / `link` 去读 channel；app.py:346 的 `findall("item")` 匹配不到命名空间节点，条目才落到 app.py:347-358。源标题和站点链接解析不到。
2. README.md:9 写「首次登录强制提示改密码」。app.py:109-111 会把默认用户标成 `must_change=1`，app.py:139-152 的 `current_user` 只查 token，不看这个标志。探测：登录返回 `must_change True` 之后，`GET /api/feeds` 与 `GET /api/entries` 都是 200。index.html:158 登录成功后直接 `enterApp()`，再 `showModal()`。index.html:127 的 `<dialog>` 没有拦截 `cancel`，Esc 可以关掉对话框。
3. README.md:12 写「单个源手动刷新」。后端 app.py:555-557 有 `POST /api/feeds/{fid}/refresh`。页面上 index.html:99 只有「刷新全部」，index.html:177-178 每个源只有退订按钮。一键刷新全部是通的（探测 `REFRESH_ALL 200`）。
4. README.md:10 写填网站首页就会自动发现源。实际发现发生在抓取阶段 app.py:394-398：响应的 Content-Type 要包含 `html`，且正文前 500 个字符不像 feed，才会调用 `discover_feed_url`。
5. README.md:58 默认数据库写成 `data/freshfeeds.db`。app.py:26-27 把它固定在 `app.py` 所在目录下的 `data/freshfeeds.db`，不随进程当前目录变化。
6. README.md:36 的 `py -m venv .venv` 在本机失败，原文见上一节。同机 `python -m venv .venv` 可以建环境。这是本机 py 启动器指向不存在的 `E:\python.exe`，不记成仓库缺陷，也不改 README。

其余对照过的声明与代码一致，这里不展开：默认账号 `admin` / `admin123`（README.md:42，app.py:110）、token 常量 24 小时（README.md:9，app.py:30、app.py:168-169；没有做 24 小时实钟等待）、只监听 `127.0.0.1`（README.md:57，启动日志 `127.0.0.1:8000`）、刷新间隔与调度开关（README.md:59-60，app.py:28-29）、测试命令（README.md:48）。

## 许可证与署名核查

仓库内部是自洽的，本次不改 `LICENSE` 和 `UPSTREAM.md`。

- README.md:72 声明 Apache License 2.0。`LICENSE` 开头是 Apache License Version 2.0（LICENSE:2-3），正文是该许可证全文。
- LICENSE:190 的 `Copyright [yyyy] [name of copyright owner]` 是 Apache 官方附录里的填写模板，还留在标准文本里。UPSTREAM.md:11 也写了上游 LICENSE 的附录同样没有填具体版权人。这不是「本项目版权人叫 [yyyy]」这种事实声明。
- UPSTREAM.md:3-6 把设计来源写成 `https://github.com/miniflux/v2`，commit `bdd8087d9cf7a20ca7e800948389e8a7e86445da`，许可证 Apache-2.0，署名 `Copyright The Miniflux Authors. All rights reserved.`。UPSTREAM.md:12、README.md:5、app.py:5 都写代码是独立实现。在 `*.py`、`*.html`、`*.txt` 里检索 `miniflux`，只出现在 NOTES.md:5 和 UPSTREAM.md。源码里没有上游仓库名，和「未复制上游源码」这句话对得上。
- 任务禁止抓取外部页面，所以没有核对这个 commit 是不是默认分支 HEAD，也没有核对 `main.go` 里的 SPDX 行是不是 UPSTREAM.md:11 说的那句。这两项标「未核实」，不据此改 UPSTREAM。
- app.py:31 的 User-Agent 带了 `https://github.com/ZZmkk88/freshfeeds`。README 和 UPSTREAM 都没写这个地址。同样未联网核实，不改这一行。

## 分级修复清单

### P0

无。安装、测试、监听端口和首页都已经跑通。

### P1

1. 非 http(s) 地址会被当成订阅源去读。app.py:221 `urlopen` 没有 scheme 限制；app.py:697 导入 OPML 时 `xmlUrl` 原样入库。探测 `fetch_url("file:///E:/muse-bridge/work/TASK-031-freshfeeds/localfeed.xml")` 返回 `ok`，正文含 `marker-local-file`。`discover_feed_url` 会把首页里的 `file://` 链接原样返回（`DISCOVER file:///...localfeed.xml`）。从 http 302 到 `file://` 时，Python 自己拒绝了（`Redirection to url 'file:///...' is not allowed`），这条路径读不到文件。修法：抓取前只接受带主机名的 http/https；OPML 里其它 scheme 记失败并且不入库。
2. 恶意源可以把 `javascript:` 链接写进文章，前端放进 `href`。app.py:308 原样保存 `url`；index.html:193 是 `href="${esc(e.url)}"`，`esc` 只转义 HTML，不拦这个 scheme。探测 `STORED_ENTRY_URL javascript:alert(1)`。修法：不是 http(s) 的条目链接存空字符串；前端生成 href 时同样只接受 http(s)。
3. 默认口令在「必须改密」期间仍能用全部接口。app.py:139-152。探测 `FEEDS_WHILE_MUST_CHANGE 200`、`ENTRIES_WHILE_MUST_CHANGE 200`。修法：`must_change=1` 时，除 `/api/me` 和 `/api/change-password` 以外返回 403；前端在改密完成前不进入主界面，并拦截对话框的 cancel。
4. OPML 上传没有大小上限，解析器会展开内部实体。app.py:686 `await file.read()`；app.py:688 `ET.fromstring`。探测 `ENTITY_TEXT EXPANDED-ENTITY`。外部实体没有读到标记文件，接口直接 400（`OPML_XXE 400`「这不是合法的 OPML/XML 文件」）。修法：超过 2MB 拒绝；内容里出现 DTD 或实体声明也拒绝。
5. 抓取订阅源时响应体没有上限。app.py:222 `resp.read()`。修法：最多读 5MB，超出则当作抓取失败。未用超大响应做实测，依据是这里没有上界。
6. 改密后旧 token 仍然有效。app.py:191-194 只更新 `users`，不删除 `tokens`。探测 `OLD_TOKEN_AFTER_PW_CHANGE 200`，响应里 `must_change_password` 已是 false。修法本应让其它 token 失效。本轮不改：`tests/test_app.py:40-44` 的模块级 token，在 `tests/test_app.py:86-91` 两次改密之后，仍被 `tests/test_app.py:96` 以及后面的用例使用。吊销旧 token 会让全量测试变成 401。不许改测试，也不做会把测试改红的实现。

### P2

1. RSS 1.0 源标题和站点链接为空。app.py:343-347。修法：用 `{http://purl.org/rss/1.0/}` 读取 channel 的 title 和 link。本轮不改。
2. `limit=-1` 会绕过 200 条上限。app.py:596 的 `min(limit, 200)` 在 limit 为负时得到负数，SQLite 把负 LIMIT 当成不限制。探测 `LIMIT_NEG 200 count 2`，当时库里就是 2 条。修法：把 limit 夹到 1 到 200。本轮不改。
3. 不存在的分类 id 被报成「已经订阅过了」。app.py:534-536 把外键失败和唯一约束都收成同一句。探测 `BAD_CAT 400`，正文是「这个源已经订阅过了」，该地址并没有订阅过。修法：按约束类型分开返回。本轮不改。
4. 界面没有单个源的刷新按钮。index.html:177。修法：给源条目加上调用已有 `POST /api/feeds/{id}/refresh` 的按钮。本轮不改。
5. 默认库路径的文档和实现不一致。README.md:58 与 app.py:27。修法：在 README 里写明路径相对 `app.py` 所在目录。本轮不改 README 文案。
6. 开发依赖触发 Starlette 弃用警告。requirements-dev.txt:2 锁定 `httpx==0.28.1`。测试仍通过。任务不许改已有依赖的版本号，这里也不是依赖冲突，保持不动。
