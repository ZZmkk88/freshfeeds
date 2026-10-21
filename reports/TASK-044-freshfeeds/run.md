# TASK-044-freshfeeds 执行记录

开工：2026-10-21。工作目录 `E:\muse-bridge\in\TASK-044-freshfeeds`。先审查跑通，再按清单修 P0/P1（最多 5 项）。

## 环境

命令：

```
py -3 --version
```

输出（exit 1）：

```
Unable to create process using 'E:\python.exe --version': ???????????
```

命令：

```
python --version
```

输出（exit 0）：

```
Python 3.11.9
```

说明：README Windows 段写的是 `py -m venv`。本机 `py` 启动器指向损坏的 `E:\python.exe`，无法创建进程。改用已可用的 `python` 3.11.9。虚拟环境放到 `E:\muse-bridge\work\TASK-044-freshfeeds\venv`，避免把 `.venv` 写进待审仓库。

仓库是 git 工作区，`git status --porcelain` 为空（干净）。HEAD：`cf8d2f1 docs(freshfeeds): 新增 DECISIONS.md 记已定决策与不采纳项；README 补 HOST 变量与 DB 路径说明`。

## 装依赖

虚拟环境：`E:\muse-bridge\work\TASK-044-freshfeeds\venv`（`python -m venv`，exit 0）。

命令：

```
E:\muse-bridge\work\TASK-044-freshfeeds\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-044-freshfeeds\requirements-dev.txt
```

输出摘要（exit 0）：`fastapi==0.156.7`、`uvicorn==0.54.0`、`python-multipart==0.0.32`、`httpx==0.28.1`、`pytest==9.1.1` 均安装成功。传递依赖含 `starlette-1.9.0`、`pydantic-2.14.1`。无版本冲突。

## 全量测试（修复前）

命令（通过 `E:\muse-bridge\work\TASK-044-freshfeeds\run_pytest.bat`，把 TEMP/TMP 指到工作目录，`PYTHONDONTWRITEBYTECODE=1`，cwd 为仓库）：

```
E:\muse-bridge\work\TASK-044-freshfeeds\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

输出：

```
..........................                                               [100%]
============================== warnings summary ===============================
..\..\work\TASK-044-freshfeeds\venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\work\TASK-044-freshfeeds\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
26 passed, 1 warning in 6.23s
EXIT=0
```

26 项全部通过。1 条警告是 DECISIONS.md 已记录、明确不修的 httpx/Starlette 弃用警告。

## 起服务并探测本机路由

数据库与临时目录都放在 `E:\muse-bridge\work\TASK-044-freshfeeds\`，避免在仓库里生成 `data\freshfeeds.db`。调度器设为 `0`，避免进程空转 30 分钟。入口仍是 `python app.py`（脚本 `smoke_server.py` 用子进程启动，探测完 `terminate`，未使用 taskkill / curl）。

环境变量：`FRESHFEEDS_DB=E:\muse-bridge\work\TASK-044-freshfeeds\freshfeeds.db`，`FRESHFEEDS_SCHEDULER=0`，`HOST=127.0.0.1`，`PORT=8000`。

输出摘要（exit 0，服务进程自身退出码 1，原因是探测结束后被终止，日志里没有应用异常）：

```
PORT_8000_READY True
PID 14964
GET / status 200 ctype text/html; charset=utf-8
b'<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n...\n<title>freshfeeds \xc2\xb7 \xe6\xb8\x85\xe6\xb3\x89\xe9\x98\x85\xe8\xaf\xbb</title>\n'
GET /health status 404 ctype application/json
b'{"detail":"Not Found"}'
GET /api/health status 404 ctype application/json
b'{"detail":"Not Found"}'
GET /api/me status 401 ctype application/json
b'{"detail":"\xe6\x9c\xaa\xe7\x99\xbb\xe5\xbd\x95"}'
SERVER_EXIT 1
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:64859 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:64860 - "GET /health HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:64861 - "GET /api/health HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:64862 - "GET /api/me HTTP/1.1" 401 Unauthorized
```

首页 200，标题为 freshfeeds · 清泉阅读。未登录访问 `/api/me` 返回 401，正文是「未登录」。`/health` 与 `/api/health` 均为 404。README 没有健康检查路径，此 404 不记为缺陷。

## 安全探针（不抓外网页面）

脚本：`probe_security.py`、`probe_more.py`、`probe_cases.py`。OPML/添加订阅的用例把 `refresh_feed` 换成空操作，避免真的向外连。

要点：

- `ftp://93.184.216.34/feed.xml`、`gopher://93.184.216.34:70/x`：`ensure_fetch_allowed` 结果为 ALLOW。
- 模拟 `resolve_host_addresses` 抛 `OSError`：`http://example.test/feed.xml` 结果为 `FAIL_OPEN`（函数直接 return）。
- `socket.inet_aton`：`2130706433`、`0x7f000001`、`127.1`、`0177.0.0.1` 都解析成 `127.0.0.1`；`ipaddress.ip_address` 对这四个都是 `ValueError`。
- 本机 `getaddrinfo` 对上述四个主机名为 `gaierror [Errno 11001]`。`ensure_fetch_allowed` 因此 ALLOW：`http://2130706433/`、`http://0x7f000001/`、`http://127.1/`、`http://0177.0.0.1/`。
- 字面内网地址（`127.0.0.1`、`10.1.2.3`、`192.168.1.1`、`172.16.0.1`、`169.254.169.254`、`0.0.0.0`、`::1`、`::ffff:127.0.0.1`、`::ffff:10.1.2.3`）为 BLOCK。`http://198.18.0.1/` 为 ALLOW（与 DECISIONS 一致）。
- `parse_feed` 对含内部实体的小文档返回 `title='XYXYXY'`（实体被展开）。外部实体 `SYSTEM file:///C:/Windows/win.ini` 为 `ParseError undefined entity`，没有读出文件。
- `_clean_url('https://example.com/"onmouseover="alert(1)')` 原样返回该字符串。`javascript:alert(1)` 返回空串。
- OPML 导入 `ftp://93.184.216.34/feed.xml`：`200 {"total":1,"added":1,"skipped":0,"failed":0}`，库里有这条 URL。
- `POST /api/feeds` `http://2130706433/feed.xml`：`200 {"id":2,"added":0}`，URL 入库。
- `POST /api/feeds` `gopher://...`：`400 {"detail":"请填 http(s) 开头的源地址"}`（添加接口有 scheme 前缀检查，OPML 路径没有）。
- `parse_feed` 的 channel `<link>javascript:alert(1)</link>`：`site_url` 为 `'javascript:alert(1)'`。
- `GET /api/entries?offset=-1` 在有 1 条数据时返回 200，并仍返回该条。不是 500。
- `urllib.request.Request.add_header("If-None-Match", "abc\\r\\nX-Injected: 1")` 被收下。本机 Python 3.11 `http/client.py` 的 `putheader`（约 1280 行）会在发送前用 `_is_illegal_header_value` 拒绝这种值。未观察到成功的头注入。

## 修复后的测试

每改完一条都用同一条命令重跑全量测试（`run_pytest.bat`）：

```
E:\muse-bridge\work\TASK-044-freshfeeds\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

- P1-1 之后：`26 passed, 1 warning in 6.09s`，EXIT=0
- P1-2 之后：`26 passed, 1 warning in 6.08s`，EXIT=0
- P1-3 之后：`26 passed, 1 warning in 6.01s`，EXIT=0
- 三处都改完后再跑一次：`26 passed, 1 warning in 6.52s`，EXIT=0

P1-2 探针 `verify_ssrf.py`：ftp/gopher/十进制回环被 BLOCK，`198.18.0.1` 与 `93.184.216.34` 仍 ALLOW，DNS 失败为 FAIL_CLOSED，OPML 的 ftp 源 `added:0 failed:1`，库中 URL 为空。

P1-3 探针 `verify_dtd.py`：带内部实体和外部实体的文档都被拒绝；普通 RSS 标题「示例」、链接 `https://example.com/a` 仍能解析。

Node v24.21.0 执行页面里的 `esc`：带引号的 URL 变成 `&quot;`，属性引号没有被截断。

收尾 `git status --porcelain`：

```
 M app.py
 M static/index.html
```

