# TASK-067-freshfeeds 执行记录

开工时间：2026-10-21。工作目录：E:\muse-bridge\in\TASK-067-freshfeeds。临时目录：E:\muse-bridge\work\TASK-067-freshfeeds。

## 1. 环境探测

命令：

```
python --version
py -3 --version
netstat -ano | Select-String ":8000"
```

输出摘要：

- `python --version` → `Python 3.11.9`（满足 README 的 3.10+）
- `py -3 --version` 退出码 1：`Unable to create process using 'E:\python.exe --version'`（本机 py 启动器指向损坏的 E:\python.exe）。README Windows 步骤写的是 `py -m venv .venv`，在本机不可用。改用 `python -m venv`。
- 本机 8000 端口没有 LISTENING（netstat 命中的是远端 IPv6 地址里的 `:8000:`，不是本机监听）。

## 2. 安装依赖

虚拟环境放在工作目录，避免写进仓库（禁止 del/rm，不能事后删仓库里的 .venv）：

```
python -m venv E:\muse-bridge\work\TASK-067-freshfeeds\venv
E:\muse-bridge\work\TASK-067-freshfeeds\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-067-freshfeeds\requirements.txt
```

`requirements.txt` 安装成功（fastapi==0.156.7、uvicorn==0.54.0、python-multipart==0.0.32，以及传递依赖 starlette-1.9.0、pydantic-2.14.1 等）。无依赖冲突。

接着：

```
E:\muse-bridge\work\TASK-067-freshfeeds\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-067-freshfeeds\requirements-dev.txt
```

安装成功：httpx==0.28.1、pytest==9.1.1（以及 httpcore、certifi 等）。无版本冲突。

## 3. 全量测试（修之前）

临时目录指到任务工作目录（测试文件自己调用 tempfile.mkdtemp）。命令：

```
E:\muse-bridge\work\TASK-067-freshfeeds\venv\Scripts\python.exe E:\muse-bridge\work\TASK-067-freshfeeds\run_pytest.py
```

`run_pytest.py` 在导入 pytest 之前把 tempfile.tempdir 设为 `E:\muse-bridge\work\TASK-067-freshfeeds`，然后 `pytest.main(["tests/", "-q", "--tb=short"])`，工作目录为仓库根。

输出：

```
..............................                                           [100%]
============================== warnings summary ===============================
..\..\work\TASK-067-freshfeeds\venv\Lib\site-packages\fastapi\testclient.py:1
  StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
30 passed, 1 warning in 6.02s
```

退出码 0。30 项全过。警告来自 fastapi/starlette 与 httpx 的弃用提示，不是测试失败（DECISIONS.md 已记录此项不改依赖版本）。

## 4. 起服务（冒烟后已关）

数据库改到工作目录，避免按默认路径在仓库里创建 `data/`（本任务禁止 del/rm，创建了就删不掉）。`FRESHFEEDS_SCHEDULER` 未设置，走代码默认开启。命令：

```
E:\muse-bridge\work\TASK-067-freshfeeds\venv\Scripts\python.exe E:\muse-bridge\work\TASK-067-freshfeeds\smoke_server.py
```

脚本用上述 venv 执行 `app.py`，环境变量 `HOST=127.0.0.1`、`PORT=8000`、`FRESHFEEDS_DB=E:\muse-bridge\work\TASK-067-freshfeeds\smoke.db`。请求用 urllib，不用 curl/wget。结束后 `proc.terminate()`。

输出片段：

```
PID 5024
PORT_OPEN 8000
GET / -> 200 ctype=text/html; charset=utf-8 len=16132 body=b'<!DOCTYPE html>...<title>freshfeeds ...
GET /health -> 404 body=b'{"detail":"Not Found"}'
GET /api/health -> 404 body=b'{"detail":"Not Found"}'
GET /docs -> 404 body=b'{"detail":"Not Found"}'
GET /redoc -> 404 body=b'{"detail":"Not Found"}'
GET /openapi.json -> 404 body=b'{"detail":"Not Found"}'
GET /api/me -> 401 body=b'{"detail":"\xe6\x9c\xaa\xe7\x99\xbb\xe5\xbd\x95"}'
POST /api/login -> 200 {"token":"...","must_change_password":true}
GET /api/me -> 200 body=b'{"username":"admin","must_change_password":true}'
POST /api/feeds/refresh-all -> 200 body=b'{"feeds":0,"added":0,"failed":0}'
GET /api/feeds -> 200 body=b'[]'
STOPPED 1
PORT_AFTER False
```

`server.log`：

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:50471 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:50481 - "POST /api/feeds/refresh-all HTTP/1.1" 200 OK
```

`STOPPED 1` 是进程被 terminate 之后的退出码，日志里没有 traceback。`PORT_AFTER False` 表示 8000 已不再监听。

README 没有写健康检查路径。`/health` 与 `/api/health` 的 404 按「没有这个接口」记录，不记成项目跑不起来。

## 5. 缺陷探针（修之前）

```
E:\muse-bridge\work\TASK-067-freshfeeds\venv\Scripts\python.exe E:\muse-bridge\work\TASK-067-freshfeeds\probe_logic.py
```

数据库 `E:\muse-bridge\work\TASK-067-freshfeeds\probe.db`，调度关闭。退出码 0。关键输出：

```
== discovery URL clobber on bad target
 fetch http://orig.example/
 fetch http://orig.example/bad.xml
create 200 {'id': 1, 'warning': '抓取失败：syntax error: line 1, column 0', 'added': 0}
stored urls [(1, 'http://orig.example/bad.xml', 'syntax error: line 1, column 0')]

== opml javascript htmlUrl fetch fails
import 200 {'total': 1, 'added': 1, 'skipped': 0, 'failed': 1}
stored [('https://js-opml.example/rss', 'javascript:alert(1)', 'simulated down')]
export has javascript True

== opml javascript kept when parsed site_url empty
import 200 {'total': 1, 'added': 1, 'skipped': 0, 'failed': 0}
stored [('https://nolink.example/rss', "'javascript:alert(2)'")]
export has javascript True

== parse path javascript site link
create 200 {'id': 4, 'added': 1}
site_url ''

== negative offset
offset -1 200 [有文章数组]

== refresh-all
refresh-all 200 {"feeds":4,"added":0,"failed":4}

== logout
POST /api/logout 404 {"detail":"Not Found"}

== ssrf literals
BLOCK http://127.0.0.1/ 、127.1、2130706433、0x7f000001、0177.0.0.1、0、0.0.0.0、
  [::1]、[::ffff:127.0.0.1]、[2002:7f00:1::]、[64:ff9b::7f00:1]、[2001::80ff:fffe]、
  169.254.169.254、10.1.2.3、192.168.0.1、172.16.0.1、localhost、file:///etc/passwd、
  主机名含混的 userinfo 写法
ALLOW http://8.8.8.8/ 、http://93.184.216.34/ 、http://198.18.0.1/

== redirect hop
redirect blocked 拒绝抓取内网/保留地址：127.0.0.1（127.0.0.1）

== dns pin
pin result ok PINNED ctype text/plain
```

`refresh-all` 的 `failed:4` 是探针把 `fetch_url` 恢复成真实抓取后，库里的 example 地址连不上，不是路由 422。冒烟时零订阅的 refresh-all 返回 `failed:0`。

## 6. P1-1 修复后验证

```
E:\muse-bridge\work\TASK-067-freshfeeds\venv\Scripts\python.exe E:\muse-bridge\work\TASK-067-freshfeeds\verify_p1_1.py
E:\muse-bridge\work\TASK-067-freshfeeds\venv\Scripts\python.exe E:\muse-bridge\work\TASK-067-freshfeeds\run_pytest.py
```

verify 退出码 0：失败发现后地址仍是 `http://orig.example/`；成功发现后地址改为 `http://orig.example/good.xml`，标题「发现后的标题」。

pytest：`30 passed, 1 warning in 4.61s`，退出码 0。

## 7. P1-2 修复后验证与收尾全量测试

```
E:\muse-bridge\work\TASK-067-freshfeeds\venv\Scripts\python.exe E:\muse-bridge\work\TASK-067-freshfeeds\verify_p1_2.py
E:\muse-bridge\work\TASK-067-freshfeeds\venv\Scripts\python.exe E:\muse-bridge\work\TASK-067-freshfeeds\run_pytest.py
```

verify 退出码 0：`javascript:alert(1)` 与 `javascript:alert(2)` 的 site_url 均为空，导出不含 `javascript:`；`https://keep.example/` 仍保留。

全量测试（两处修改都落地之后）：

```
30 passed, 1 warning in 4.63s
```

退出码 0。无失败。

## 8. 工作区

```
git status --porcelain
```

```
 M app.py
```
