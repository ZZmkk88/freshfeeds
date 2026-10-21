# TASK-091-freshfeeds 执行记录

开工时间：2026-10-22。工作目录 `E:\muse-bridge\in\TASK-091-freshfeeds`。先读 README 与源码，再按说明装环境、跑测试、起服务。

## 1. 环境探测

命令：

```
py -3 -V
```

输出（exit 1）：

```
Unable to create process using 'E:\python.exe -V': ???????????
```

README 写的 Windows 入口 `py -m venv` 在本机不可用（py 启动器指向坏掉的 `E:\python.exe`）。

命令：

```
python -V
where.exe python
python -c "import sys; print(sys.executable); print(sys.version)"
git status --porcelain
git rev-parse --show-toplevel
```

输出：

```
Python 3.11.9
E:\muse-bridge\env\TASK-091-freshfeeds\Scripts\python.exe
C:\Users\xzm\AppData\Local\Programs\Python\Python311\python.exe
C:\Users\xzm\AppData\Local\Microsoft\WindowsApps\python.exe
E:\muse-bridge\env\TASK-091-freshfeeds\Scripts\python.exe
3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]
```

`git status --porcelain` 为空（工作区干净）。仓库根：`E:/muse-bridge/in/TASK-091-freshfeeds`。无 `.gitignore`。

本机已有任务专用 venv：`E:\muse-bridge\env\TASK-091-freshfeeds`（Python 3.11.9，满足 README 的 3.10+）。该 venv 目前只有 pip/setuptools，还没装项目依赖。为避免把 `.venv` 写进仓库，后续安装与测试都用这个 venv，不在仓库内建 `.venv`。

## 2. 安装依赖

命令（在仓库根目录，使用上述 venv 的 python）：

```
python -m pip install -r requirements.txt
```

结果：exit 0。装上 fastapi==0.156.7、uvicorn==0.54.0、python-multipart==0.0.32，以及传递依赖 starlette-1.9.0、pydantic-2.14.1、pydantic-core==2.50.1 等。末尾：

```
Successfully installed annotated-doc-0.0.5 annotated-types-0.8.0 anyio-4.15.1 click-8.5.0 fastapi-0.156.7 h11-0.16.0 idna-3.20 opentelemetry-api-1.45.1 pydantic-2.14.1 pydantic-core-2.50.1 python-multipart-0.0.32 starlette-1.9.0 typing-extensions-4.16.0 typing-inspection-0.4.4 uvicorn-0.54.0
```

命令：

```
python -m pip install -r requirements-dev.txt
```

结果：exit 0。运行依赖已满足，新装 httpx==0.28.1、pytest==9.1.1。末尾：

```
Successfully installed certifi-2026.10.19 colorama-0.4.6 httpcore-1.0.9 httpx-0.28.1 iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.1.1
```

## 3. 全量测试

直接 `python -m pytest` 会在仓库里写 `.pytest_cache` / `__pycache__`，测试文件里的 `tempfile.mkdtemp()` 还会落到系统 TEMP。任务要求临时文件只放 `E:\muse-bridge\work\TASK-091-freshfeeds`，所以用该目录下的 `run_pytest.py` 把 TEMP/TMP 指过去、关掉 bytecode，再调用 pytest。等价于 README 的 `python -m pytest tests/ -q`，工作目录是仓库根。

命令：

```
python E:\muse-bridge\work\TASK-091-freshfeeds\run_pytest.py
```

第一次（exit 1）收集失败，因为脚本把 `sys.path[0]` 占成了 work 目录，`import app` 找不到模块：

```
E   ModuleNotFoundError: No module named 'app'
ERROR tests/test_app.py
1 warning, 1 error in 1.02s
```

这是启动脚本的问题，不是仓库缺陷。脚本改为 `chdir` 到仓库并把仓库插入 `sys.path` 后重跑。

第二次（exit 0）：

```
...............................                                          [100%]
============================== warnings summary ===============================
..\..\env\TASK-091-freshfeeds\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\env\TASK-091-freshfeeds\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa
31 passed, 1 warning in 6.94s
```

31 项全部通过。警告来自 fastapi/starlette 对 httpx 的弃用提示，不是失败。耗时 6.94s（pytest 自己打印的）。

## 4. 本地行为探针（不访问外网）

命令：

```
python E:\muse-bridge\work\TASK-091-freshfeeds\probe_behavior.py
```

片段：

```
BLOCK http://127.0.0.1/ 拒绝抓取内网/保留地址：127.0.0.1（127.0.0.1）
BLOCK http://2130706433/ 拒绝抓取内网/保留地址：2130706433（127.0.0.1）
BLOCK http://[::ffff:127.0.0.1]/ 拒绝抓取内网/保留地址
BLOCK http://localhost/ 拒绝抓取内网/保留地址：localhost（127.0.0.1）
ALLOW http://[fec0::1]/ ['fec0::1']
ALLOW http://198.18.0.1/ ['198.18.0.1']
ALLOW http://93.184.216.34/ ['93.184.216.34']
LOGIN 200 must_change_password True
REFRESH-ALL 200 {"feeds":0,"added":0,"failed":0}
GET /health 404
GET / 200 text/html
PIN_FETCH ok application/rss+xml
REDIR_FETCH ok
```

钉死路径能连上本机测试服务器；重定向第二跳会再次进入校验。`fec0::1` 与 `198.18.0.1` 被放行。

命令：

```
python E:\muse-bridge\work\TASK-091-freshfeeds\probe_ssrf2.py
```

6to4 / NAT64 / Teredo / IPv4-mapped 内嵌私网地址全部 BLOCK。文档地址 `192.0.2.1`、`198.51.100.1`、`203.0.113.1`、`2001:db8::1`、`100::1`、`fec0::1` 为 ALLOW。脚本在打印 `urlsplit(...).port` 时抛了 `ValueError: Port could not be cast to integer value as 'alert(1)'`，exit 1，后面的 offset/代理检查没跑到。这是探针自己的写法问题。

命令：

```
python E:\muse-bridge\work\TASK-091-freshfeeds\probe3.py
```

片段（exit 0）：

```
in_transaction_after_select False
offset -1 200 ['g2', 'g1', 'g0']
offset 0 200 ['g2', 'g1', 'g0']
offset 2 200 ['g0']
q_percent 200 3
PROXY_TEST ok direct-ok
```

进程环境里设了 `HTTP_PROXY=http://127.0.0.1:1`，抓取仍直接打到本机测试服务器，没有走代理。`offset=-1` 与 `offset=0` 返回同一批行。`q=%` 命中全部 3 条。

## 5. 起服务

按默认端口先起一次。命令：

```
python E:\muse-bridge\work\TASK-091-freshfeeds\run_server.py
```

当时脚本里的 PORT 是 8000。输出（进程随即退出，exit 1）：

```
INFO:     Started server process [32872]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
ERROR:    [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): 通常每个套接字地址(协议/网络地址/端口)只允许使用一次。
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
```

`netstat -ano -p tcp | findstr :8000`：

```
TCP    127.0.0.1:8000         0.0.0.0:0              LISTENING       35756
```

用 urllib 请求这个已占用的 8000，返回的是别的程序，不是本仓库：

```
GET8000 200 text/html; charset=utf-8 b'<!doctype html>...<title>weblens · 网站访问统计</title>...'
/health 404
```

这是本机端口占用，不是 freshfeeds 绑定逻辑错误。没有结束 PID 35756。数据库用 `FRESHFEEDS_DB` 指到 work 目录，避免在仓库里生成 `data/freshfeeds.db`。

把 PORT 改成 18765 后再起。日志：

```
INFO:     Started server process [28172]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:18765 (Press CTRL+C to quit)
```

命令：

```
python E:\muse-bridge\work\TASK-091-freshfeeds\probe_live.py
```

输出：

```
GET / 200 text/html; charset=utf-8 b'<!DOCTYPE html>...<title>freshfeeds · 清泉阅读</title>...'
GET /health 404 b'{"detail":"Not Found"}'
GET /api/health 404 b'{"detail":"Not Found"}'
GET /docs 404 b'{"detail":"Not Found"}'
GET /openapi.json 404 b'{"detail":"Not Found"}'
POST /api/login 200 application/json b'{"token":"A58x5Po2...","must_change_password":true}'
GET /api/me 200 application/json b'{"username":"admin","must_change_password":true}'
GET /api/feeds 200 application/json b'[]'
GET /api/feeds 401 b'{"detail":"未登录"}'
```

未带 token 的 `/api/feeds` 是 401。默认账号可以登录。仓库没有 `/health`。

## 6. 关掉服务

停掉 18765 那个进程后：

```
netstat -ano -p tcp | findstr 18765
```

只有 `TIME_WAIT`，没有 `LISTENING`。`probe_down.py` 对 `127.0.0.1:18765` 连接得到 `18765_CLOSED TimeoutError timed out`。监听已经不在。

## 7. 收尾再跑全量测试

命令：

```
python E:\muse-bridge\work\TASK-091-freshfeeds\run_pytest.py
```

```
31 passed, 1 warning in 6.92s
```

警告仍是同一条 StarletteDeprecationWarning。

## 8. git status

命令：

```
git status --porcelain
```

无输出，退出码 0。仓库工作区没有改动。
