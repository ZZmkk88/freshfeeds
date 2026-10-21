# freshfeeds 修复记录

行号是修改之后的位置。验证都在仓库目录 `E:\muse-bridge\in\TASK-031-freshfeeds` 里，用 `.venv` 的 Python。

## P1-1 非 http(s) 地址会被抓取

- 文件：`app.py:36-42` 增加 `_require_http_url`；`app.py:225` 在 `fetch_url` 发请求前调用；`app.py:708-714` OPML 的 `xmlUrl` 校验失败则 `failed += 1` 并且不入库。
- 改法：scheme 必须是 http 或 https，且必须有主机名。`file://` 在打开连接之前就抛出 `ValueError`。
- 验证命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q --tb=line
.\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-031-freshfeeds\verify1.py
```

- pytest 输出：`14 passed, 1 warning in 1.94s`（警告仍是 Starlette 对 httpx TestClient 的弃用提示）。
- verify1.py 输出：

```
FILE_BLOCKED 只允许 http(s) 地址
DISCOVER file:///E:/muse-bridge/work/TASK-031-freshfeeds/localfeed.xml
DISCOVER_FETCH_BLOCKED 只允许 http(s) 地址
HTTP_OK http://127.0.0.1:9/feed.xml
OPML 200 {"total":1,"added":0,"skipped":0,"failed":1}
FEED_URLS []
```

首页发现逻辑仍会抽出 `file://` 链接，随后的抓取被拒绝，文件内容没有被读入。OPML 不再把该地址写入订阅表。

## P1-2 条目链接里的 javascript: URL

- 文件：`app.py:45-50` 增加 `_http_url_or_blank`；`app.py:327` 入库前丢掉非 http(s) 链接。`static/index.html:148` 增加 `safeHref`；`static/index.html:194` 的 href 改为 `safeHref(e.url)`。
- 改法：`javascript:` 等 scheme 存成空字符串。前端只有以 `http://` 或 `https://` 开头的地址才会写进 href。
- 验证命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q --tb=line
.\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-031-freshfeeds\verify2.py
```

- pytest 输出：`14 passed, 1 warning in 1.92s`。
- verify2.py 输出：

```
PARSED [('点我', ''), ('正常', 'https://js.example/ok')]
ADD 200 {"id":1,"added":2}
STORED [('点我', ''), ('正常', 'https://js.example/ok')]
FRONT_SAFEHREF True
FRONT_OLD_HREF False
```

## P1-3 未改密时仍能调用业务接口

- 文件：`app.py:157-171`。`must_change` 为 1 时，路径不是 `/api/me` 或 `/api/change-password` 就返回 403。`static/index.html:158-159` 未改密不进入主界面；`static/index.html:165-166` 改密成功后再进入；`static/index.html:232-236` 拦截对话框 cancel，并用 `/api/me` 的标志决定是否弹窗。
- 改法：服务端把「必须改密」做成鉴权条件。前端在改密完成前不请求订阅和文章接口。
- 验证命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short
.\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-031-freshfeeds\verify3.py
```

- pytest 输出：`14 passed, 1 warning in 1.95s`。
- verify3.py 输出：

```
LOGIN 200 True
ME 200 {'username': 'admin', 'must_change_password': True}
FEEDS_BEFORE 403 {"detail":"请先修改密码"}
ENTRIES_BEFORE 403
CHANGE 200 {"ok":true}
FEEDS_AFTER 200
CANCEL_GUARD True
LOGIN_GATE True
```

## P1-4 OPML 无大小上限且会展开内部实体

- 文件：`app.py:34` 常量 `MAX_OPML_BYTES = 2_000_000`；`app.py:708-713` 限制读取长度，并拒绝含 DTD 或实体声明的内容（去掉 NUL 后再匹配，覆盖 UTF-16）。
- 改法：超过 2MB 返回 400。内部实体在解析前被拒绝，不再交给 `ElementTree` 展开。
- 验证命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q --tb=line
.\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-031-freshfeeds\verify4.py
```

- pytest 输出：`14 passed, 1 warning in 1.92s`。
- verify4.py 输出：

```
ENTITY 400 {"detail":"不接受带 DTD 或实体声明的 OPML"}
UTF16 400 {"detail":"不接受带 DTD 或实体声明的 OPML"}
BIG 400 {"detail":"OPML 文件超过 2MB"}
GOOD 200 {"total":1,"added":1,"skipped":0,"failed":0}
```

## P1-5 抓取响应体没有上限

- 文件：`app.py:35` 常量 `MAX_FEED_BYTES = 5_000_000`；`app.py:245-247` 最多读 5MB + 1 字节，超出则抛出 `ValueError`。`refresh_feed` 原有的异常处理会把它记进 `last_error` 并返回 502。
- 改法：不再把订阅源的响应一次性读完。
- 验证命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q --tb=line
.\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-031-freshfeeds\verify5.py
```

- pytest 输出：`14 passed, 1 warning in 1.90s`。
- verify5.py 输出（本机 `127.0.0.1` 上分别返回小 RSS 和 5MB+1 字节）：

```
SMALL ok <?xml version="1.0"?><rss version="2.0">
BIG_BLOCKED 订阅源响应超过 5MB
VERIFY5_DONE
```

## P1-6 改密不吊销旧 token（未改）

- 文件：`app.py` 的 `change_password` 仍只更新 `users`。修复前探测 `OLD_TOKEN_AFTER_PW_CHANGE 200`。
- 未改原因：`tests/test_app.py` 的 `auth` fixture 在模块里只登录一次。`test_me_and_change_password` 会改密再改回来，后面的 `test_add_feed_and_dedup` 等继续用最初那个 token。把旧 token 删掉，全量测试会变成 401。不许改测试，所以这条保持原样。

## 全量测试（全部改完之后）

命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q --tb=line
```

输出：

```
..............                                                           [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\in\TASK-031-freshfeeds\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
14 passed, 1 warning in 1.89s
```

没有失败的用例。警告与修复前相同，来自依赖里的 TestClient，不是断言失败。

前端改密弹窗和文章链接没有在浏览器里点击。本环境没有浏览器工具。`verify2.py` 核对了接口不再返回 `javascript:` 链接，以及 `index.html` 已改用 `safeHref`。`verify3.py` 核对了未改密时接口返回 403，以及页面源码里的 cancel 拦截和登录分流。

## git status --porcelain

命令（仓库目录）：

```powershell
git status --porcelain
```

输出原样：

```
 M app.py
 M static/index.html
```






