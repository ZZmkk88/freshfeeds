# TASK-077-freshfeeds 执行记录

开工: 2026-10-22 工作目录 E:\muse-bridge\in\TASK-077-freshfeeds

说明: 本机 `python` 实际指向任务预置虚拟环境 `E:\muse-bridge\env\TASK-077-freshfeeds\Scripts\python.exe`。依赖装在该环境，未在仓库内创建 `.venv`（避免把虚拟环境写进待审仓库）。临时库与探测脚本在 `E:\muse-bridge\work\TASK-077-freshfeeds`。

## 1. Python / py 启动器

命令:

```
py -3 --version
```

输出（exit 1）:

```
Unable to create process using 'E:\python.exe --version': ???????????
```

命令:

```
python --version
where.exe python
```

输出:

```
Python 3.11.9
E:\muse-bridge\env\TASK-077-freshfeeds\Scripts\python.exe
C:\Users\xzm\AppData\Local\Programs\Python\Python311\python.exe
C:\Users\xzm\AppData\Local\Microsoft\WindowsApps\python.exe
```

Python 3.11.9 满足 README 的 3.10+。`py` 启动器在本机不可用，属环境问题，不是仓库代码错误。

## 2. 安装依赖

工作目录即仓库。命令:

```
python -m pip install -r requirements.txt
```

输出摘要（exit 0）:

```
Collecting fastapi==0.156.7
Collecting uvicorn==0.54.0
Collecting python-multipart==0.0.32
Successfully installed annotated-doc-0.0.5 annotated-types-0.8.0 anyio-4.15.1 click-8.5.0 fastapi-0.156.7 h11-0.16.0 idna-3.20 opentelemetry-api-1.45.1 pydantic-2.14.1 pydantic-core-2.50.1 python-multipart-0.0.32 starlette-1.9.0 typing-extensions-4.16.0 typing-inspection-0.4.4 uvicorn-0.54.0
```

命令:

```
python -m pip install -r requirements-dev.txt
```

输出摘要（exit 0）:

```
Successfully installed certifi-2026.10.19 colorama-0.4.6 httpcore-1.0.9 httpx-0.28.1 iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.1.1
```

## 3. 本地探测（未改仓库，脚本在 work 目录）

命令:

```
python E:\muse-bridge\work\TASK-077-freshfeeds\probe_ssrf.py
```

要点（exit 0）:

- 常见内网字面量（127.0.0.1、10/8、169.254.169.254、localhost、::1、6to4/Teredo/64:ff9b::/96 内嵌私网）均 BlockedUrlError。
- `http://[64:ff9b:1:7f00:0:1:808:808]/feed` 被 ALLOW，嵌入抽取结果是 8.8.8.8（只取了末 32 位）。
- 直接请求 127.0.0.1 的“重定向”探测在第一跳就被拦，不能证明 302 跟随。
- 把 `_is_public_ip` 临时改成恒真后，钉死 DNS 的本地抓取返回 `PIN ok application/rss+xml`。
- TestClient: `GET /` 200 `text/html`；`/health`、`/api/health`、`/docs`、`/openapi.json`、`/redoc` 均为 404；登录 200；`POST /api/feeds/refresh-all` 200 `{"feeds":0,"added":0,"failed":0}`。
- 另有 StarletteDeprecationWarning: `Using httpx with starlette.testclient is deprecated; install httpx2 instead.`

## 4. 全量测试（修复前）

命令（工作目录为仓库）:

```
python -m pytest tests/ -q --tb=line
```

输出（exit 0）:

```
...............................                                          [100%]
============================== warnings summary ===============================
..\..\env\TASK-077-freshfeeds\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\env\TASK-077-freshfeeds\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
31 passed, 1 warning in 7.43s
```

## 5. 重定向 / NAT64 / 发现源（probe2，修复前）

命令:

```
python E:\muse-bridge\work\TASK-077-freshfeeds\probe2.py
```

输出要点（exit 0）:

```
priv-pub-suffix 64:ff9b:1:7f00:0:100:808:808 embedded_fn= 8.8.8.8 public= True
  ALLOW ['64:ff9b:1:7f00:0:100:808:808']
meta-pub-suffix 64:ff9b:1:a9fe:a9:fe00:101:101 embedded_fn= 1.1.1.1 public= True
  ALLOW ['64:ff9b:1:a9fe:a9:fe00:101:101']
public0 64:ff9b:1:808:8:800:: embedded_fn= 0.0.0.0 public= False
  BLOCK 拒绝抓取内网/保留地址：64:ff9b:1:808:8:800::（64:ff9b:1:808:8:800::）
REDIR-OK ok application/rss+xml <?xml version='1.0'?><rss version='2.0'>
REDIR-INTERNAL BlockedUrlError 拒绝抓取内网/保留地址：10.1.2.3（10.1.2.3）
DISCOVER {'added': 1, 'total_in_feed': 1} url http://127.0.0.1:<port>/real.xml title Disc err  entries 1
```

说明: 302 跟随和首页发现源是通的。`64:ff9b:1::/48` 的内嵌 IPv4 被按末 32 位（后缀）判断，私网地址可被放行。hostname 钉死探测连的是 127.0.0.1:80（本机无服务，WinError 10061 拒绝连接），没有回落到真实 DNS 失败，钉死路径生效。

## 6. 起服务并关掉

启动命令（后台，数据库与调度都指到 work 目录，避免把库写进仓库）:

```
python E:\muse-bridge\work\TASK-077-freshfeeds\serve.py
```

`serve.py` 在导入 app 前设置 `FRESHFEEDS_DB=E:\muse-bridge\work\TASK-077-freshfeeds\smoke.db`、`FRESHFEEDS_SCHEDULER=0`、`HOST=127.0.0.1`、`PORT=8000`，然后 `uvicorn.run`。

服务日志:

```
INFO:     Started server process [36648]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

探测命令:

```
python E:\muse-bridge\work\TASK-077-freshfeeds\smoke_client.py
```

输出（exit 0）:

```
GET / 200 text/html; charset=utf-8 b'<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n<meta name="vi'
GET /health 404 b'{"detail":"Not Found"}'
GET /api/health 404 b'{"detail":"Not Found"}'
GET /docs 404 b'{"detail":"Not Found"}'
GET /openapi.json 404 b'{"detail":"Not Found"}'
GET /redoc 404 b'{"detail":"Not Found"}'
GET /app.py 404 b'{"detail":"Not Found"}'
GET /data/freshfeeds.db 404 b'{"detail":"Not Found"}'
LOGIN 200 keys ['must_change_password', 'token'] must_change True
ME 200 {"username":"admin","must_change_password":true}
FEEDS_NOAUTH 401 {"detail":"未登录"}
```

随后用会话的进程停止方式关掉该 uvicorn（未使用 taskkill）。

停服确认:

```
tasklist /FI "PID eq 36648"
```

输出为「没有运行的任务匹配指定条件」（控制台编码乱码，含义是进程已不在）。

```
netstat -ano | findstr :8000
```

只有 `127.0.0.1:8000` 的 TIME_WAIT，没有 LISTENING。

```
python E:\muse-bridge\work\TASK-077-freshfeeds\check_port.py
```

输出: `CLOSED TimeoutError timed out`。进程已退出且没有 LISTENING，但本机对 8000 的新 SYN 没有立刻收到 RST，而是超时。服务进程本身已经停掉。

## 7. 修复 P1-1 后的验证

改的是 `app.py` 里 `64:ff9b:1::/48` 的内嵌 IPv4 抽取（改后 `app.py:81-87`）。

命令：

```
python E:\muse-bridge\work\TASK-077-freshfeeds\verify_p1.py
```

输出末行：`FAILED 0`。私网后缀绕过地址改为拒绝，公网内嵌地址仍放行。完整输出见 fix-report.md。

命令：

```
python -m pytest tests/ -q --tb=line
```

输出（exit 0）：

```
31 passed, 1 warning in 6.71s
```

命令：

```
git status --porcelain
```

输出原文：

```
 M app.py
```
