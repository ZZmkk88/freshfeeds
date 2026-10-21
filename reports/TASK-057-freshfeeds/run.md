# TASK-057-freshfeeds 执行记录

开工时间：2026-10-21。工作目录：E:\muse-bridge\in\TASK-057-freshfeeds。先审查再按清单修 P0/P1。

## 步骤 1：确认 Python

命令：

```powershell
py -0p
py -3.11 -c "import sys; print(sys.executable); print(sys.version)"
py -c "import sys; print(sys.version)"
```

输出摘要：

```
 -V:3.14 *        E:\python.exe
 -V:3.11          C:\Users\xzm\AppData\Local\Programs\Python\Python311\python.exe
C:\Users\xzm\AppData\Local\Programs\Python\Python311\python.exe
3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]
---- py default ----
Unable to create process using 'E:\python.exe -c "import sys; print(sys.version)"': ???????????
```

结论：本机默认 `py` 指向损坏的 `E:\python.exe`（退出码 1）。可用解释器是 `py -3.11`（Python 3.11.9，满足 README 的 3.10+）。后续 venv 用 `py -3.11` 创建，不记为项目缺陷。

## 步骤 2：创建 venv 并安装依赖

venv 放在 `E:\muse-bridge\work\TASK-057-freshfeeds\.venv`（不写进仓库，避免污染 git status）。

命令：

```powershell
py -3.11 -m venv E:\muse-bridge\work\TASK-057-freshfeeds\.venv
E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-057-freshfeeds\requirements-dev.txt
```

结果：退出码 0。装上 fastapi==0.156.7、uvicorn==0.54.0、python-multipart==0.0.32、httpx==0.28.1、pytest==9.1.1 及其传递依赖（starlette==1.9.0、pydantic==2.14.1 等）。pip 提示可升级 24.0 -> 26.2.2，未升级（任务不许改依赖版本，也不擅自升级工具）。

## 步骤 3：跑全量测试

工作目录：`E:\muse-bridge\in\TASK-057-freshfeeds`（工具默认 cwd）。

命令：

```powershell
E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q -o cache_dir=E:\muse-bridge\work\TASK-057-freshfeeds\pytest-cache
```

输出：

```
..........................                                               [100%]
============================== warnings summary ===============================
..\..\work\TASK-057-freshfeeds\.venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
26 passed, 1 warning in 6.51s
```

退出码 0。26 项全过。警告是 Starlette 对 httpx TestClient 的弃用提示（DECISIONS.md 已记 P2-6 不修）。cache 目录指到工作目录，未在仓库生成 `.pytest_cache`。

## 步骤 4：按 README 起服务并探测首页

数据库放到工作目录，避免在仓库里生成 `data/freshfeeds.db`。启动脚本：`E:\muse-bridge\work\TASK-057-freshfeeds\start_server.py`（设置 `FRESHFEEDS_DB`、`FRESHFEEDS_SCHEDULER=0`、`HOST=127.0.0.1`、`PORT=8000` 后以 `__main__` 运行 `app.py`）。

命令：

```powershell
E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-057-freshfeeds\start_server.py
```

启动输出：

```
INFO:     Started server process [35540]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

探测命令（标准库 urllib，未用 curl/wget）：

```powershell
E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-057-freshfeeds\probe_http.py
```

输出摘要：

```
server up status=200
POST /api/login status=200 ctype=application/json body={"token":"<redacted>","must_change_password":true}
GET / status=200 ctype=text/html; charset=utf-8 body=<!DOCTYPE html> ... <title>freshfeeds · 清泉阅读</title> ...
GET /health status=404 ctype=application/json body={"detail":"Not Found"}
GET /api/health status=404 ctype=application/json body={"detail":"Not Found"}
GET /docs status=404
GET /redoc status=404
GET /openapi.json status=404
GET /api/feeds noauth status=401 body={"detail":"未登录"}
GET /api/me status=200 body={"username":"admin","must_change_password":true}
GET /api/feeds status=200 body=[]
POST mark-all-read empty json status=200 body={"ok":true}
```

登录 token 是本次临时库的会话密钥，报告里不贴原文。

关服务：停掉上述后台进程（会话内结束，未使用 taskkill）。进程日志：`terminated by signal killed`。端口 8000 的进程已退出。

## 步骤 5：本地行为探针（不抓外网页面）

```powershell
E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-057-freshfeeds\probe_logic.py
E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-057-freshfeeds\probe_hosts.py
E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-057-freshfeeds\probe_proxy.py
E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-057-freshfeeds\probe_gai.py
```

关键输出：

- `http://[2002:7f00:1::]/`、`http://[64:ff9b::7f00:1]/`、`http://[64:ff9b:1::7f00:1]/`、`http://[::7f00:1]/` 均为 ALLOW。`_is_public_ip("2001:0:4136:e378:8000:63bf:80ff:fffe")`（Teredo 内嵌 127.0.0.1）为 True。
- `http://198.18.0.1/`、`http://8.8.8.8/`、`http://93.184.216.34/` 为 ALLOW。`http://127.0.0.1/`、`http://localhost/`、`http://[::ffff:127.0.0.1]/`、`http://2130706433/`、`http://0x7f000001/` 为 BLOCK。
- 重定向探针：第一跳放行后，302 到 `169.254.169.254`、`10.1.2.3`、`file://`、`javascript:` 均 BlockedUrlError。
- `parse_feed` 把 channel link `javascript:alert(1)` 留在 site_url，条目 url 被置空。BOM 的 RSS 能解析。
- `http://127.0.0.1%23@8.8.8.8/feed`：`urlsplit.hostname='8.8.8.8'`（因此 ALLOW），urllib 实际 `getaddrinfo` 主机是 `127.0.0.1#@8.8.8.8`。
- 本机 `getaddrinfo("127.0.0.1#@8.8.8.8")` → `gaierror: [Errno 11003] getaddrinfo failed`，没有解析成 127.0.0.1。
- 环境代理：`HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`=`http://127.0.0.1:7890`，`NO_PROXY`=`127.0.0.1,localhost,::1`。默认 opener 会把外网请求交给该代理。关掉代理后，`example.com` 的解析主机才是 `example.com`。

## 步骤 6：确认仓库未被测试弄脏

```powershell
git status --porcelain
```

输出为空（退出码 0）。未在仓库生成 `__pycache__`、`.pytest_cache` 或 `data/`。

## 步骤 7：按清单修 P1-1、P1-2 并复测

P1-1 后：

```powershell
E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Scripts\python.exe -m pytest tests/test_app.py::test_ssrf_blocked_targets tests/test_app.py::test_ssrf_allows_public_and_fakeip_range tests/test_app.py::test_ssrf_redirect_to_internal_blocked tests/test_app.py::test_create_feed_internal_url_rejected -q -p no:cacheprovider
E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-057-freshfeeds\probe_p1_1.py
```

`4 passed, 2 warnings in 1.71s`；探针 `failures 0`。详情在 fix-report.md。

P1-2 后：

```powershell
E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-057-freshfeeds\probe_p1_2.py
E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q -o cache_dir=E:\muse-bridge\work\TASK-057-freshfeeds\pytest-cache
```

探针末行：`pin ok host feed.test:52280 added_dns [] has_item True`。全量：`26 passed, 1 warning in 6.10s`。

## 步骤 8：收尾 git status

```powershell
git status --porcelain
```

```
 M app.py
```
