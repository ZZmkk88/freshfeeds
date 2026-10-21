# TASK-074-freshfeeds 执行记录

开工时间：2026-10-21。工作目录：E:\muse-bridge\in\TASK-074-freshfeeds。第一步：盘点仓库结构与 README。

## 1. Python 与 README 的 venv 命令

命令：

```
py -0p
py -3.11 --version
C:\Users\xzm\AppData\Local\Programs\Python\Python311\python.exe --version
py -m venv E:\muse-bridge\work\TASK-074-freshfeeds\venv-readme-try
```

输出：

```
 -V:3.14 *        E:\python.exe
 -V:3.11          C:\Users\xzm\AppData\Local\Programs\Python\Python311\python.exe
Python 3.11.9
Unable to create process using 'E:\python.exe -m venv E:\muse-bridge\work\TASK-074-freshfeeds\venv-readme-try': ???????????
```

退出码 1。README 写的是 `py -m venv`。本机 `py` 默认指向 `E:\python.exe`（登记为 3.14），该解释器无法启动。这是本机环境限制，不是仓库缺陷。后续改用 `py -3.11`（Python 3.11.9，满足 README 的 3.10+）。venv 放到 `E:\muse-bridge\work\TASK-074-freshfeeds\venv`，不写进仓库。

## 2. 安装依赖

开始：2026-10-22T00:07:24+08:00

命令：

```
py -3.11 -m venv E:\muse-bridge\work\TASK-074-freshfeeds\venv
E:\muse-bridge\work\TASK-074-freshfeeds\venv\Scripts\python.exe -m pip install --disable-pip-version-check -r E:\muse-bridge\in\TASK-074-freshfeeds\requirements-dev.txt
```

`requirements-dev.txt` 第一行是 `-r requirements.txt`，所以运行依赖和测试依赖一次装齐。退出码 0。钉死版本均能从缓存/索引装上：fastapi==0.156.7、uvicorn==0.54.0、python-multipart==0.0.32、httpx==0.28.1、pytest==9.1.1。末行：

```
Successfully installed annotated-doc-0.0.5 annotated-types-0.8.0 anyio-4.15.1 certifi-2026.10.19 click-8.5.0 colorama-0.4.6 fastapi-0.156.7 h11-0.16.0 httpcore-1.0.9 httpx-0.28.1 idna-3.20 iniconfig-2.3.1 opentelemetry-api-1.45.1 packaging-26.3 pluggy-1.7.0 pydantic-2.14.1 pydantic-core-2.50.1 pygments-2.21.0 pytest-9.1.1 python-multipart-0.0.32 starlette-1.9.0 typing-extensions-4.16.0 typing-inspection-0.4.4 uvicorn-0.54.0
```

## 3. 全量测试

命令（脚本 `E:\muse-bridge\work\TASK-074-freshfeeds\run-pytest.bat`）：

```
set TEMP=E:\muse-bridge\work\TASK-074-freshfeeds\tmp
set TMP=E:\muse-bridge\work\TASK-074-freshfeeds\tmp
set PYTHONDONTWRITEBYTECODE=1
cd /d E:\muse-bridge\in\TASK-074-freshfeeds
E:\muse-bridge\work\TASK-074-freshfeeds\venv\Scripts\python.exe -B -m pytest tests -q -p no:cacheprovider --basetemp E:\muse-bridge\work\TASK-074-freshfeeds\tmp\pytest-basetemp
```

输出：

```
...............................                                          [100%]
============================== warnings summary ===============================
..\..\work\TASK-074-freshfeeds\venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\work\TASK-074-freshfeeds\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
31 passed, 1 warning in 7.07s
PYTEST_EXIT=0
```

31 项全过。唯一警告是 Starlette 对 httpx 的弃用提示（DECISIONS.md 已写明不改依赖版本）。临时库在工作目录的 TEMP 下，未改测试。

## 4. 安全与数据行为抽查（不访问外网）

命令：

```
E:\muse-bridge\work\TASK-074-freshfeeds\venv\Scripts\python.exe -B E:\muse-bridge\work\TASK-074-freshfeeds\probe_ssrf.py
E:\muse-bridge\work\TASK-074-freshfeeds\venv\Scripts\python.exe -B E:\muse-bridge\work\TASK-074-freshfeeds\probe_behavior.py
```

SSRF 抽查要点（退出码 0）：

```
nat64/96 127.0.0.1: public=False
nat64/48 127.0.0.1 suffix public: ip=64:ff9b:1:7f00:0:108:808:800 embedded=8.8.8.0 public=True
nat64/48 169.254.169.254 suffix public: embedded=8.8.8.0 public=True
OK  http://[64:ff9b:1:7f00:0:108:808:800]/x: 'ALLOW'
OK  http://[fec0::1]/x: 'ALLOW'
EXC http://127.0.0.1/x: BlockedUrlError
EXC http://169.254.169.254/latest/meta-data: BlockedUrlError
EXC http://127.0.0.1%23@8.8.8.8/x: BlockedUrlError: 网址主机名含混，已拒绝抓取
```

发现源改写抽查（退出码 0）：

```
REFRESH_EXC HTTPException 502: 抓取失败：syntax error: line 1, column 0
FEED_URL http://feeds.example/rss
LAST_ERROR syntax error: line 1, column 0
REDIRECT_EXC BlockedUrlError second hop blocked
```

原订阅地址是 `http://blog.example/home`。发现的地址解析失败后，库里的 url 仍被改成 `http://feeds.example/rss`。重定向第二跳拦截有效。

## 5. 起服务并关掉

开始：2026-10-22T00:17:43+08:00。数据库改到工作目录，避免在仓库里生成 `data/`。调度保持 README 默认（开）。

命令（`E:\muse-bridge\work\TASK-074-freshfeeds\start-server.bat`）：

```
set FRESHFEEDS_DB=E:\muse-bridge\work\TASK-074-freshfeeds\tmp\server.db
set PYTHONDONTWRITEBYTECODE=1
cd /d E:\muse-bridge\in\TASK-074-freshfeeds
E:\muse-bridge\work\TASK-074-freshfeeds\venv\Scripts\python.exe -B app.py
```

`server.log`：

```
INFO:     Started server process [26592]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:52022 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:52024 - "GET /health HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:52025 - "GET /api/health HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:52026 - "GET /api/me HTTP/1.1" 401 Unauthorized
INFO:     127.0.0.1:52027 - "GET /docs HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:52028 - "GET /openapi.json HTTP/1.1" 404 Not Found
```

检查脚本输出：

```
UP
STATUS 200 / CT=text/html; charset=utf-8 BODY=b'<!DOCTYPE html>\n<html lang="zh-CN">\n...\n<title>freshfeeds \xc2\xb7 \xe6\xb8\x85\xe6\xb3\x89\xe9\x98\x85\xe8\xaf\xbb</title>\n...
STATUS 404 /health BODY=b'{"detail":"Not Found"}'
STATUS 404 /api/health BODY=b'{"detail":"Not Found"}'
STATUS 401 /api/me BODY=b'{"detail":"\xe6\x9c\xaa\xe7\x99\xbb\xe5\xbd\x95"}'
STATUS 404 /docs BODY=b'{"detail":"Not Found"}'
STATUS 404 /openapi.json BODY=b'{"detail":"Not Found"}'
```

首页 200，标题是 freshfeeds · 清泉阅读。未登录访问 `/api/me` 返回 401，正文是「未登录」。代码没有健康检查路由，`/health` 与 `/api/health` 为 404，这不是故障。`/docs` 与 `/openapi.json` 按 `app.py` 关闭文档页，返回 404。

约 00:18:04 结束进程。之后 `netstat -ano | findstr :8000` 只剩 TIME_WAIT，没有 LISTENING。服务已停。

## 6. 修复后的测试

P1-1 之后：

```
...\venv\Scripts\python.exe -B E:\muse-bridge\work\TASK-074-freshfeeds\probe_ssrf.py
E:\muse-bridge\work\TASK-074-freshfeeds\run-pytest.bat
```

`64:ff9b:1::/48` 内嵌 127.0.0.1 变为 `public=False`，`ensure_fetch_allowed` 抛出 BlockedUrlError。pytest：`31 passed, 1 warning in 6.61s`，`PYTEST_EXIT=0`。

P1-2 之后（也是改动后的全量重跑）：

```
...\venv\Scripts\python.exe -B E:\muse-bridge\work\TASK-074-freshfeeds\verify_discover.py
E:\muse-bridge\work\TASK-074-freshfeeds\run-pytest.bat
```

解析失败时 url 仍是 `http://blog.example/home`。解析成功时 url 改为 `http://feeds.example/good.xml`，`added=1`。pytest：`31 passed, 1 warning in 6.79s`，`PYTEST_EXIT=0`。

收尾 `git status --porcelain`：

```
 M app.py
```
