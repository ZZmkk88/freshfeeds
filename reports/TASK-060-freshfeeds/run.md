# TASK-060-freshfeeds 执行记录

开工时间：2026-10-21。工作目录 `E:\muse-bridge\in\TASK-060-freshfeeds`。先审查再按清单修 P0/P1。

## 1. 环境探测

命令：`py -3 --version`

```
exit: 1
Unable to create process using 'E:\python.exe --version': ???????????
```

README Windows 步骤写的是 `py -m venv .venv`。本机 `py` 启动器指向 `E:\python.exe`，进程创建失败。

命令：`python --version`

```
Python 3.11.9
```

命令：`python -c "import sys; print(sys.executable); print(sys.version)"`

```
E:\muse-bridge\env\TASK-060-freshfeeds\Scripts\python.exe
3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]
```

PATH 上的 python 已是任务预置 venv（Python 3.11.9，满足 README 的 3.10+）。`python -m pip show fastapi uvicorn python-multipart httpx pytest` 结果：`Package(s) not found`。接下来用该解释器安装 `requirements-dev.txt`（内含 `-r requirements.txt`）。

命令：`git status --porcelain`（开工前）

```
（空，工作区干净）
```

## 2. 安装依赖

命令（工作目录 `E:\muse-bridge\in\TASK-060-freshfeeds`）：`python -m pip install -r requirements-dev.txt`

exit: 0。片段：

```
Collecting fastapi==0.156.7 (from -r requirements.txt (line 1))
Collecting uvicorn==0.54.0 (from -r requirements.txt (line 2))
Collecting python-multipart==0.0.32 (from -r requirements.txt (line 3))
Collecting httpx==0.28.1 (from -r requirements-dev.txt (line 2))
Collecting pytest==9.1.1 (from -r requirements-dev.txt (line 3))
Successfully installed ... fastapi-0.156.7 ... httpx-0.28.1 ... pytest-9.1.1 ... python-multipart-0.0.32 ... uvicorn-0.54.0
```

版本均可安装，无依赖冲突。

## 3. 全量测试

命令（工作目录 `E:\muse-bridge\in\TASK-060-freshfeeds`）：

`python -m pytest tests/ -q -o cache_dir=E:\muse-bridge\work\TASK-060-freshfeeds\pytest_cache`

exit: 0。输出：

```
..........................                                               [100%]
============================== warnings summary ===============================
..\..\env\TASK-060-freshfeeds\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\env\TASK-060-freshfeeds\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
26 passed, 1 warning in 4.60s
```

26 项全过。警告与 DECISIONS.md 第 25 行「httpx 的 Starlette 弃用警告，不修」一致，不记为缺陷。

开工前 `git ls-files`：`.gitignore`、`DECISIONS.md`、`LICENSE`、`NOTES.md`、`README.md`、`UPSTREAM.md`、`app.py`、`requirements-dev.txt`、`requirements.txt`、`static/index.html`、`tests/test_app.py`。

## 4. 行为探测（不改仓库）

脚本在 `E:\muse-bridge\work\TASK-060-freshfeeds\`，不进仓库。

命令：`python E:\muse-bridge\work\TASK-060-freshfeeds\probe_behavior.py`

exit: 0。关键片段：

```
2002:7f00:1::            public=True
64:ff9b::7f00:1          public=True
64:ff9b::a9fe:a9fe       public=True
::7f00:1                 public=True
::ffff:127.0.0.1         public=False
198.18.0.1               public=True
ALLOW http://[2002:7f00:1::]/
ALLOW http://[2002:a9fe:a9fe::]/
ALLOW http://[64:ff9b::7f00:1]/
ALLOW http://[64:ff9b::a9fe:a9fe]/
BLOCK http://127.0.0.1/feed
BLOCK http://2130706433/
BLOCK http://[::ffff:127.0.0.1]/
site_url= 'javascript:alert(1)' entry_url= ''
ET entity expansion title= 'EXPANDED'
GET / -> 200
GET /health -> 404
GET /docs -> 404
login 200 must_change_password=True
categories while must_change 200 []
limit=-5 offset=-1 200 []
change pw len=5000 200 {"ok":true}
```

命令：`python E:\muse-bridge\work\TASK-060-freshfeeds\probe_rebind.py`（导入前清掉代理，避免打到本机 7890）

exit: 0。关键片段：

```
HTTP_PROXY='http://127.0.0.1:7890'
ALLOW http://[::7f00:1]/
ALLOW http://[2002:c612:1::]/
doctype REJECT ValueError: 不接受带 DTD 或实体声明的订阅源
local server port 61103
fetch result status/body: ok hit-127.0.0.1
calls:
  ('check', 'feeds.example.test', ['93.184.216.34'])
  ('connect', 'feeds.example.test', 61103)
```

含义：校验阶段看到公网 IP `93.184.216.34` 并放行，真正连接时再次解析，探测把第二次解析指到 `127.0.0.1`，响应正文是 `hit-127.0.0.1`。另一次未清代理的探测里，`getaddrinfo` 的目标是 `127.0.0.1:7890`（环境代理），并得到 `HTTP Error 502`。

## 5. 起服务并关掉

数据库放到工作目录，避免在仓库里生成 `data/freshfeeds.db`。监听仍是 README 的 `127.0.0.1:8000`。

命令：`python E:\muse-bridge\work\TASK-060-freshfeeds\serve.py`

启动输出：

```
LISTEN 127.0.0.1:8000 db=E:\muse-bridge\work\TASK-060-freshfeeds\freshfeeds.db
INFO:     Started server process [33176]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

命令：`python E:\muse-bridge\work\TASK-060-freshfeeds\check_http.py`（服务存活时）

```
GET / 200 ctype=text/html; charset=utf-8 body=b'<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n...'
GET /health 404 body=b'{"detail":"Not Found"}'
GET /api/health 404 body=b'{"detail":"Not Found"}'
GET /docs 404 body=b'{"detail":"Not Found"}'
GET /openapi.json 404 body=b'{"detail":"Not Found"}'
GET /api/feeds 401 body=b'{"detail":"\xe6\x9c\xaa\xe7\x99\xbb\xe5\xbd\x95"}'
POST /api/login 200 must_change_password= True token_len= 43
```

`/api/feeds` 的 401 正文是「未登录」。README 没有健康检查路径，`/health` 与 `/api/health` 为 404，不记为缺陷。`/docs` 与 `/openapi.json` 关闭，与 app.py:132-138 一致。

随后终止该服务进程。再用直连套接字确认端口不再提供本服务：`python E:\muse-bridge\work\TASK-060-freshfeeds\check_port.py` 输出 `TimeoutError timed out` / `CLOSED`。

停进程之后再用 urllib 打了一次，部分请求被本机 `HTTP_PROXY=http://127.0.0.1:7890` 拐走（`/api/feeds` 变成 404 而不是本应用的 401）。那次输出不作本应用的验收证据。

命令：`git status --porcelain`（起服务之后）

```
（空）
```

## 6. 按清单修 P1 并复测

P1-1 验证：`python E:\muse-bridge\work\TASK-060-freshfeeds\verify_p1_1.py`

```
connect_targets [('93.184.216.34', 9)]
unpinned_targets [('127.0.0.1', 9)]
```

对应测试：`python -m pytest tests/test_app.py -q -k "ssrf or real_http or create_feed or add_feed" -o cache_dir=E:\muse-bridge\work\TASK-060-freshfeeds\pytest_cache`

```
6 passed, 20 deselected, 1 warning in 1.96s
```

P1-2 验证：`python E:\muse-bridge\work\TASK-060-freshfeeds\verify_p1_2.py`，exit 0，`failed 0`。6to4/NAT64/兼容地址里的回环和 169.254.169.254 被拒绝，`198.18.0.1` 与 `2002:c612:1::` 仍放行。

对应测试：`python -m pytest tests/test_app.py -q -k ssrf -o cache_dir=E:\muse-bridge\work\TASK-060-freshfeeds\pytest_cache`

```
3 passed, 23 deselected, 1 warning in 1.10s
```

P1-3 验证：`python E:\muse-bridge\work\TASK-060-freshfeeds\verify_p1_3.py`

```
long_login 401 {'detail': '用户名或密码不对'} elapsed=0.002s
long_new 400 {'detail': '密码过长'}
still_old 200
```

对应测试：`python -m pytest tests/test_app.py -q -k "login or password" -o cache_dir=E:\muse-bridge\work\TASK-060-freshfeeds\pytest_cache`

```
3 passed, 23 deselected, 1 warning in 1.61s
```

全量：`python -m pytest tests/ -q -o cache_dir=E:\muse-bridge\work\TASK-060-freshfeeds\pytest_cache`

```
26 passed, 1 warning in 4.93s
```

收尾：`git status --porcelain`

```
 M app.py
```

`git diff --stat`：`app.py | 93 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-----`，`1 file changed, 86 insertions(+), 7 deletions(-)`。
