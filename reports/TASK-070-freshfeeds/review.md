# freshfeeds 验收审查

结论：仓库能装、测试 30 项全过、服务能在 `127.0.0.1:8000` 起来并返回首页。没有 P0。有 2 个 P1：SSRF 校验漏了两种内嵌私网 IPv4 的写法，校验函数把它们放行。许可证文本与仓库内署名彼此不冲突；上游 commit / 文件头未联网核实。

## 本地跑通记录

环境：本机 `python --version` → `Python 3.11.9`。README 要求 3.10+。README 的 Windows 入口 `py -m venv` 在本机失败，原文：

```
py -3 --version
exit: 1
Unable to create process using 'E:\python.exe --version': ???????????
```

这是本机 `py` 启动器指向不存在的 `E:\python.exe`，不是仓库缺陷。随后用已能工作的 `python` 在工作目录建虚拟环境（未建在仓库内）：

```
python -m venv E:\muse-bridge\work\TASK-070-freshfeeds\.venv
```

依赖（在仓库目录执行，版本按 requirements 钉死的号安装成功）：

```
E:\muse-bridge\work\TASK-070-freshfeeds\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

装上的钉死版本：`fastapi-0.156.7`、`uvicorn-0.54.0`、`python-multipart-0.0.32`、`httpx-0.28.1`、`pytest-9.1.1`。结尾 `Successfully installed ...`。

全量测试（工作目录即仓库）：

```
E:\muse-bridge\work\TASK-070-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short -o cache_dir=E:\muse-bridge\work\TASK-070-freshfeeds\pytest-cache
```

```
..............................                                           [100%]
============================== warnings summary ===============================
fastapi\testclient.py:1
  StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
30 passed, 1 warning in 7.08s
```

这条警告与 `DECISIONS.md:25`、`DECISIONS.md:42` 已记录的「不许改依赖版本号、警告无害、不修」一致。不记为缺陷。

测试文件 `tests/test_app.py:6` 用 `tempfile.mkdtemp()` 建库。覆盖 `TEMP` 的命令被会话拦住，因此这次 pytest 的临时库落在系统 TEMP。探针脚本和探针库在 `E:\muse-bridge\work\TASK-070-freshfeeds`。

按 README 起服务：

```
E:\muse-bridge\work\TASK-070-freshfeeds\.venv\Scripts\python.exe app.py
```

启动日志：

```
INFO:     Started server process [33372]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

用标准库 `urllib` 打本机（未用 curl / wget）。摘要：

| 请求 | 状态 | 正文要点 |
| --- | --- | --- |
| `GET /` | 200 | `text/html; charset=utf-8`，开头 `<!DOCTYPE html>`，标题 freshfeeds · 清泉阅读 |
| `GET /health` | 404 | `{"detail":"Not Found"}` |
| `GET /api/health` | 404 | 同上 |
| `GET /docs`、`/redoc`、`/openapi.json` | 404 | 同上 |
| `GET /api/feeds` 无登录 | 401 | `{"detail":"未登录"}` |
| `POST /api/login` 错密码 | 401 | `{"detail":"用户名或密码不对"}` |
| `POST /api/login` admin / admin123 | 200 | `must_change_password: true`（token 不写入本报告） |
| `GET /api/me` 带令牌 | 200 | `{"username":"admin","must_change_password":true}` |
| `POST /api/feeds/refresh-all` | 200 | `{"feeds":0,"added":0,"failed":0}` |
| `GET /api/entries?limit=-1&offset=-5` | 200 | `[]`（当时库是空的） |

README 没有健康检查路径。`/` 返回 200 即首页正常；`/health` 404 不是文档承诺落空。`/docs` 关闭与 `app.py:203-208`、`DECISIONS.md:50` 一致。

检查做完后结束该进程（会话终止，不是 shell 里的 taskkill）。进程从启动到结束约 746 秒，其中大部分是检查期间的空闲，不是启动耗时。启动日志在 15 秒等待内已经出现。

另外用工作目录里的探针打了 SSRF、重定向和解析（不改仓库、不访问外网页面）。与「跑通」直接相关的结果：

- 重定向第二跳会重新校验。本地 302 到 `http://10.1.2.3/x`、`http://2130706433/`、`file:///C:/Windows/win.ini` 分别被拒绝，错误原文含 `10.1.2.3`、`2130706433（127.0.0.1）`、`只允许抓取 http(s) 地址`。`seen` 列表里第一跳和第二跳的 URL 都出现了。
- 条件请求 304 返回 `('not_modified', '', '"abc"', '', '')`。
- DNS 钉死：把已放行 IP 换成 `203.0.113.9` 时，连接超时且没有落到本机监听，也没有回退到真实 `getaddrinfo`。
- `javascript:` 的频道链接和条目标题链接经 `parse_feed` 后都是空字符串；正常 `https` 保留。

## README 与实际不符处

1. `README.md:10` 写「响应是 HTML 且正文前 500 字符不含订阅源」才自动发现并改写地址。`app.py:662` 的条件是 Content-Type 含子串 `html`，且正文前 500 字符里没有 `<feed`、也没有 `<rss`。不是按正文判断 HTML；RSS 1.0 的 `<rdf:RDF` 也不算「已有订阅源」。发现实现在 `app.py:484-499`。

2. `README.md:12` 写进程内定时刷新默认每 30 分钟一轮。`app.py:32` 默认 30 分钟，这一点相符。`app.py:1036-1037` 是先 `sleep` 再抓，进程起来后不会马上抓一轮，要等满一个间隔。

3. `README.md:16` 写按标题与正文关键词搜索。`app.py:870-872` 把关键词原样放进 `LIKE %...%`，用户输入里的 `%` 和 `_` 是 SQL 通配符，不是字面关键词。

4. `README.md:63-72` 的目录清单没有 `.gitignore`。仓库根目录 `.gitignore:1` 起忽略了 `.venv/`、`data/`、`*.db` 等。

5. 下面这些是 README 没写、代码有的行为，不是把某一句写反：
   - 密码超过 128 在哈希前拒绝：`app.py:35`、`app.py:322-323`、`app.py:358-359`
   - OPML 超过 2MB 拒绝：`app.py:38`、`app.py:966-967`
   - 关闭 `/docs`、`/redoc`、`/openapi.json`：`app.py:206-208`
   - `FRESHFEEDS_REFRESH_MINUTES<=0` 时定时线程直接返回：`app.py:1034-1035`
   - 抓取前按网段拒绝内网地址：`app.py:43-48`、`app.py:136-160`

下列 README 说法与代码一致，不记不符：Python 3.10+ 语法（本机 3.11.9 已跑通；没有另开 3.10 解释器）；`HOST`/`PORT`/`FRESHFEEDS_DB`/`FRESHFEEDS_REFRESH_MINUTES`/`FRESHFEEDS_SCHEDULER` 的默认值（`app.py:31-33`、`app.py:1052-1056`）；默认账号 `admin`/`admin123` 且只提示改密（`app.py:273-274`、`static/index.html:69`、`static/index.html:131`）；删分类不删源（`app.py:761`）；重复订阅返回「已经订阅过了」（`app.py:814`）。

## 许可证与署名核查

仓库内部是对齐的，没有改 `LICENSE` 或 `UPSTREAM.md`。

- `README.md:76` 写 Apache License 2.0，见 `LICENSE`。`LICENSE:1-4` 是 Apache License Version 2.0 标准正文。
- `LICENSE:190` 仍是附录模板 `Copyright [yyyy] [name of copyright owner]`。这是 Apache 许可证原文附录，不是把本项目版权人写成占位符的另一份声明。
- 源码没有版权头。`app.py:1-6` 只说明设计思路来自社区、代码独立实现。仓库里没有 `NOTICE`。
- `UPSTREAM.md:5-6` 写上游 license 为 Apache-2.0，attribution 为 `Copyright The Miniflux Authors. All rights reserved.`。`UPSTREAM.md:11-12` 说这行是上游 `main.go` 的 SPDX 版权行逐字复制，并声明本项目未复制上游源码。
- 「All rights reserved」出现在上游署名的引用里，不是本项目在 Apache-2.0 之外又加的权利保留。按 `UPSTREAM.md:11-12` 的写法，三份文件不互相打架。
- 未访问 GitHub。`UPSTREAM.md:3-4` 的 `source_url`、`source_commit`，以及「文件头逐字复制」这一句，均未核实。本仓库是单个 Python 文件，从语言上看不像把上游 Go 源码贴进来；没有做逐文件对照。

## 分级修复清单

### P0

无。pytest 30 通过；`python app.py` 监听 `127.0.0.1:8000`；`GET /` 返回 200。

### P1

1. `app.py:76-88` `_embedded_ipv4` 没有识别 SIIT（RFC 2765）前缀 `::ffff:0:0:0/96`。`http://[::ffff:0:127.0.0.1]/`、`http://[::ffff:0:10.0.0.1]/`、`http://[::ffff:0:169.254.169.254]/` 实测都被 `ensure_fetch_allowed` 放行。修法：该前缀取出末 32 位 IPv4，再走现有黑名单。本机没有 SIIT 转换，连 `::ffff:0:7f00:1` 超时，没有打进 127.0.0.1 监听；漏洞在校验被绕过。
2. `app.py:81-82` 把 `64:ff9b::/96` 和 `64:ff9b:1::/48` 都当成「最后 32 位就是内嵌 IPv4」。`/96` 这样是对的；`/48` 按 RFC 6052，内嵌 IPv4 在第 48–87 位，最后 32 位是后缀。构造地址 `64:ff9b:1:7f00:0:100:808:808`（内嵌 127.0.0.1，后缀 8.8.8.8）实测放行。修法：`/48` 按 `raw[6:8] + raw[9:11]` 取 IPv4 再走黑名单。

### P2

1. `README.md:10` 与 `app.py:662` 的自动发现条件不一致。修法：改 README 那一句，写明看 Content-Type 是否含 `html`，以及前 500 字符只排除 `<rss` / `<feed`。
2. `README.md:12` 与 `app.py:1037`：启动后先睡眠满间隔才第一次定时抓取。修法：README 补一句。
3. `app.py:872` 搜索不转义 `%` `_`。修法：把这两个字符转义后再拼 `LIKE`。
4. `README.md:63-72` 未列 `.gitignore`。修法：目录清单补上。
5. `app.py:61-68` 黑名单没有已废弃的站点本地 `fec0::/10`。`http://[fec0::1]/` 实测放行。修法：把该前缀加进 `_BLOCKED_NETWORKS`。本机未证明它能到达内网服务。
6. `app.py:447` 文档写 `fetch_url` 返回 4 元组，`app.py:474-480` 实际返回 5 元组（含 Content-Type）。`tests/test_app.py:490` 的桩只返回 4 元组，`app.py:651` 拆包会抛错，订阅仍以空 `site_url` 留下，`tests/test_app.py:496` 的断言照样过。产品路径用 5 元组时 `javascript:` 会被清空（探针已看到）。修法：改文档字符串；测试桩应返回 5 元组。本次不改测试。
7. `tests/test_app.py:277-285` 名为重定向第二跳，但第一跳就是 `http://127.0.0.1:{port}/go`，真实 `ensure_fetch_allowed` 在连上服务器之前就拒绝。302 逻辑靠本次探针另行证实，不靠这条测试。修法：测试里只放行第一跳端口。本次不改测试。
8. `DECISIONS.md:25` 已决定不处理 httpx / Starlette 弃用警告，且不许改依赖版本号。不修。
