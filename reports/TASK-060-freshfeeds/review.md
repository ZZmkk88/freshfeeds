# freshfeeds 验收

结论：仓库能装、能测、能起。`pytest` 26 项通过（4.60s）。`127.0.0.1:8000` 首页 200，登录接口 200。没有 P0。有 3 个 P1（抓取连接没钉在已校验地址上、IPv6 内嵌 IPv4 绕过网段清单、登录/改密不限制密码长度）。下面按这 3 项改 `app.py`，P2 不改。

## 本地跑通记录

解释器：`E:\muse-bridge\env\TASK-060-freshfeeds\Scripts\python.exe`，Python 3.11.9。

`py -3 --version` 失败（环境限制，不是仓库缺陷）：

```
Unable to create process using 'E:\python.exe --version'
```

README 写的 Windows 启动器 `py` 在这台机器上不可用。改用上面的 `python`。

安装：`python -m pip install -r requirements-dev.txt`，exit 0。`fastapi==0.156.7`、`uvicorn==0.54.0`、`python-multipart==0.0.32`、`httpx==0.28.1`、`pytest==9.1.1` 都装上了。

测试：`python -m pytest tests/ -q -o cache_dir=E:\muse-bridge\work\TASK-060-freshfeeds\pytest_cache`

```
26 passed, 1 warning in 4.60s
```

警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 出处 `fastapi/testclient.py:1`。DECISIONS.md:25 写明这项不修。

服务：`python E:\muse-bridge\work\TASK-060-freshfeeds\serve.py`（只把库文件放到工作目录，监听仍是 README 的地址）。

```
LISTEN 127.0.0.1:8000 db=E:\muse-bridge\work\TASK-060-freshfeeds\freshfeeds.db
INFO:     Uvicorn running on http://127.0.0.1:8000
```

存活时 `check_http.py`：

```
GET / 200 ctype=text/html; charset=utf-8
GET /health 404 {"detail":"Not Found"}
GET /api/health 404 {"detail":"Not Found"}
GET /docs 404 {"detail":"Not Found"}
GET /openapi.json 404 {"detail":"Not Found"}
GET /api/feeds 401 {"detail":"未登录"}
POST /api/login 200 must_change_password=True token_len=43
```

README 没有健康检查路径，404 不记缺陷。文档页关闭与 app.py:136-138 一致。进程已停。直连 `127.0.0.1:8000` 不再返回页面（`check_port.py`：`TimeoutError` / `CLOSED`）。

本机还有 `HTTP_PROXY=http://127.0.0.1:7890`。停服务后若仍用 urllib 默认代理，请求会被代理拐走，那次结果不作验收证据。

## README 与实际不符处

对照过的、与代码一致的，不重复列：默认 `127.0.0.1:8000`（app.py:926-927）、账号 `admin`/`admin123`、Token 24 小时（app.py:33）、库路径相对 `app.py`（app.py:29-30）、刷新间隔 30 分钟与 `FRESHFEEDS_SCHEDULER=0` 关闭（app.py:31-32）、RSS 2.0 / RSS 1.0 / Atom、分类删除不删源、OPML、pytest 命令。首次登录只提示、不强制也与代码一致：`must_change` 只放进登录响应（app.py:271），其他接口不拦。探测里 `must_change_password=True` 时 `GET /api/categories` 仍是 200。

不符：

1. README.md:9 写「可跳过」。static/index.html:127-132 的改密 `<dialog>` 只有「保存」，没有跳过或取消按钮。页面 static/index.html:69 也写了「可跳过」。代码没有拦截 Esc，浏览器对 `<dialog>` 的默认行为可以关掉它，但界面没有对应控件。
2. README.md:10 写填网站首页就会自动发现源。app.py:535-539 只在响应类型字符串含 `html`，且正文前 500 字符不像 feed 时才找 `<link>`。其它 Content-Type 不会发现。
3. README.md:63-69 的目录没列出仓库里实际有的 `DECISIONS.md`、`LICENSE`、`requirements.txt`、`requirements-dev.txt`、`.gitignore`。

附（不是 README，但是文档和代码相反）：NOTES.md:22 写「首登强制改密」。README.md:9、DECISIONS.md:7、app.py:271 都是只提示。探测已确认未改密仍能调用分类接口。

## 许可证与署名核查

仓内声明彼此一致，上游原文未联网复核（本任务禁止抓取外网页面）。

- README.md:73 写 Apache License 2.0，指向 `LICENSE`。`LICENSE` 是 Apache-2.0 正文。
- UPSTREAM.md:3-6 把 Apache-2.0 和 `Copyright The Miniflux Authors. All rights reserved.` 标成上游 Miniflux（`miniflux/v2`，commit `bdd8087d9cf7a20ca7e800948389e8a7e86445da`）的信息。UPSTREAM.md:11-12 说明该版权行抄自上游 `main.go` 的 SPDX 行，并写明本仓未复制上游源码。这和「本仓用 Apache-2.0、上游署名单独引用」不打架。`All rights reserved` 是引用句，不是本仓另加的保留条款。
- 本仓没有 NOTICE。UPSTREAM.md:11 说上游也没有 NOTICE。按 UPSTREAM 的「独立实现」说法，Apache 第 4(d) 条的 NOTICE 转发义务在仓内说法下对不上本仓。
- 不完整，但不是互相矛盾：LICENSE:190 附录仍是占位符 `Copyright [yyyy] [name of copyright owner]`。`app.py`、`static/index.html`、`tests/test_app.py` 没有版权头或 SPDX 行（全库检索 `Copyright`/`SPDX` 只命中 UPSTREAM 与 LICENSE 附录）。本仓版权人没有写明。
- app.py:34 的 User-Agent 指向 `https://github.com/ZZmkk88/freshfeeds`。README 与 UPSTREAM 都没写这个地址。未联网，不断言这个仓库是否存在。

未改 `LICENSE` 和 `UPSTREAM.md`。占位符是许可证附录模板没填，不是可以当场改写的事实错误。

## 分级修复清单

### P0

无。测试 26 项通过，服务能监听 8000，首页 200，登录 200。

### P1

1. **抓取没有使用校验过的地址，环境代理会再解析一次。** app.py:119 的 opener 在导入时吃进 `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`（本机是 `http://127.0.0.1:7890`）。app.py:325 先 `ensure_fetch_allowed`，app.py:332 再 `open`，中间没有把连接钉死。探测：校验看到 `93.184.216.34`，第二次解析连上 `127.0.0.1`，正文 `hit-127.0.0.1`。修法：抓取 opener 忽略环境代理；`ensure_fetch_allowed` 返回已通过的地址，单次 `open` 期间 `getaddrinfo` 只返回这些地址。测试把该函数换成返回 `None` 的桩时不钉死，避免弄坏现有用例。
2. **IPv6 里嵌的 IPv4 没按网段清单判。** app.py:70-77 只处理了 `ipv4_mapped`。探测：`http://[2002:7f00:1::]/`（6to4 的 127.0.0.1）、`http://[2002:a9fe:a9fe::]/`（6to4 的 169.254.169.254）、`http://[64:ff9b::7f00:1]/`（NAT64）、`http://[::7f00:1]/`（IPv4 兼容地址）全部放行。`::ffff:127.0.0.1` 已拒绝。修法：在 `_is_public_ip` 里把 6to4（`2002::/16`）、NAT64（`64:ff9b::/96`）、Teredo（`2001::/32` 的服务器地址和异或后的客户端地址）、`::/96` 兼容地址拆出 IPv4，再走同一份拦截清单。`198.18.0.1` 以及它的 6to4 形式 `2002:c612:1::` 继续放行（DECISIONS.md:16，app.py:44-46）。
3. **密码长度没有上限，pbkdf2 在哈希前不拒绝。** app.py:255-257 登录、app.py:284-290 改密。探测：`new_password` 长度 5000 返回 `200 {"ok":true}`。修法：用户名和密码超过 128 个字符时，登录直接 401，改密直接 400，并且在调用 `hash_pw` 之前返回。

### P2（不改）

1. NOTES.md:22「强制改密」与已定口径相反。改措辞即可。不把强制改密加回代码（DECISIONS.md:7-10）。
2. static/index.html:127-132 改密框没有跳过按钮，与 README.md:9 不符。加一个关闭按钮即可。
3. README.md:63-69 目录清单缺文件。补上文件名即可。
4. app.py:535 首页发现源的条件窄于 README.md:10。需要的话放宽 Content-Type 判断。
5. app.py:481-485（Atom 在 app.py:453）站点链接不经 `_clean_url`。探测：`site_url='javascript:alert(1)'`，条目链接已被置空。前端目前不渲染 `site_url`，所以不升到 P1。导出 OPML 前同样走 `_clean_url`。
6. app.py:265 登录只插入 token，没有登出接口，过期行也不删。
7. app.py:249 登录没有失败次数限制。
8. app.py:907 `FRESHFEEDS_REFRESH_MINUTES=0` 时 `sleep(0)` 空转；app.py:911 定时刷新把异常吞掉。
9. DECISIONS.md:25：httpx / Starlette 弃用警告不修。依赖版本不动。
