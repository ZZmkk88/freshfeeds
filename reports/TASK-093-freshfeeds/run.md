# TASK-093-freshfeeds 执行记录

开工：2026-10-22 工作目录 E:\muse-bridge\in\TASK-093-freshfeeds

## 1. 查 Python

命令：`py -3 --version`
退出码：1
输出原文：
```
Unable to create process using 'E:\python.exe --version': ???????????
```
（py 启动器指向不存在的 E:\python.exe。改用已安装的 Python 3.11.9。）

命令：`C:\Users\xzm\AppData\Local\Programs\Python\Python311\python.exe --version`
退出码：0
输出：`Python 3.11.9`

命令：`Test-Path E:\muse-bridge\in\TASK-093-freshfeeds\.venv\Scripts\python.exe`
输出：`False`（仓库内尚无 .venv）

## 2. 按 README 建虚拟环境

README Windows 步骤是 `py -m venv .venv`。本机 `py` 不可用，改用 Python 3.11.9 的绝对路径执行等价命令。

命令：`C:\Users\xzm\AppData\Local\Programs\Python\Python311\python.exe -m venv .venv`
退出码：0
输出：（无）

## 3. 安装运行依赖

命令：`.venv\Scripts\python.exe -m pip install -r requirements.txt`
退出码：0
关键输出：
```
Successfully installed annotated-doc-0.0.5 annotated-types-0.8.0 anyio-4.15.1 click-8.5.0 fastapi-0.156.7 h11-0.16.0 idna-3.20 opentelemetry-api-1.45.1 pydantic-2.14.1 pydantic-core-2.50.1 python-multipart-0.0.32 starlette-1.9.0 typing-extensions-4.16.0 typing-inspection-0.4.4 uvicorn-0.54.0
```
钉死版本 fastapi==0.156.7、uvicorn==0.54.0、python-multipart==0.0.32 均安装成功。

## 4. 安装测试依赖

命令：`.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`
退出码：0
关键输出：
```
Successfully installed certifi-2026.10.19 colorama-0.4.6 httpcore-1.0.9 httpx-0.28.1 iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.1.1
```

## 5. 全量测试（修复前）

命令：`.venv\Scripts\python.exe -m pytest tests/ -q --tb=short`
工作目录：`E:\muse-bridge\in\TASK-093-freshfeeds`
退出码：0
输出：
```
....................................                                     [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\in\TASK-093-freshfeeds\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
36 passed, 1 warning in 7.95s
```

## 6. 本地探针（不访问外网；DNS 已打桩）

脚本：`E:\muse-bridge\work\TASK-093-freshfeeds\probe.py`、`probe2.py`  
命令：`.venv\Scripts\python.exe E:\muse-bridge\work\TASK-093-freshfeeds\probe.py`  
退出码：0  
关键输出：
```
in_transaction after SELECT: False
ALLOW http://8.8.8.8/ http://93.184.216.34/ http://198.18.0.1/ http://192.0.2.1/ http://198.51.100.1/ http://203.0.113.1/ http://[2002:0808:0808::]/ http://[64:ff9b::808:808]/ http://[::ffff:0:8.8.8.8]/ http://[fec0::1]/
BLOCK 127.0.0.1、2130706433、0x7f000001、0177.0.0.1、127.1、0、10/8、172.16/12、192.168/16、169.254.169.254、100.64.0.1、192.0.0.1、224、240、255.255.255.255、::1、::、::ffff:127.0.0.1、SIIT ::ffff:0:127.0.0.1、6to4 2002:7f00:1::、NAT64 64:ff9b::127.0.0.1 与 64:ff9b::a00:1、64:ff9b:1:7f00:0:100::、Teredo 2001:0::80ff:fffe、fd00::1、fc00::1、fe80::1、file://、javascript:、gopher://、userinfo 混淆样例
mocked DNS evil.example -> 127.0.0.1 BLOCK；解析结果同时含 10.0.0.1 BLOCK；只含 93.184.216.34 ALLOW
pin_ok 200 b'ok'（钉死期间未调用真实 getaddrinfo）
WRITE_OK after 0.01s（fetch_url 睡眠 6 秒期间另一连接插入成功）
refresh_result {'added': 0, 'not_modified': True}
offset -1 200 []（当时库内无文章）
```

命令：`.venv\Scripts\python.exe E:\muse-bridge\work\TASK-093-freshfeeds\probe2.py`  
退出码：0  
关键输出：
```
DEFAULT_DB_PATH E:\muse-bridge\in\TASK-093-freshfeeds\data\freshfeeds.db
REFRESH_MINUTES 30
SCHEDULER_ON True
TOKEN_TTL_HOURS 24
BLOCK http://user:pass@8.8.8.8/ 网址主机名含混
BLOCK http://8.8.8.8@127.0.0.1/ 以及其它 userinfo 样例
BLOCK http://[ff02::1]/
ALLOW http://[2001:db8::1]/
ALLOW http://[100::1]/
ALLOW HTTP://8.8.8.8/ （ensure_fetch_allowed）
BLOCK Http://127.0.0.1/
'HTTP://8.8.8.8/feed' startswith False
offset -1 200 ['title0', 'title1']
offset 0 200 ['title0', 'title1']
offset 1 200 ['title1', 'title2']
```
有 3 篇文章、limit=2 时，offset=-1 与 offset=0 结果相同。

## 7. 起服务并关掉

数据库改到工作目录，避免在仓库里生成 `data\freshfeeds.db`。HOST / PORT / FRESHFEEDS_SCHEDULER 用默认值。  
脚本：`E:\muse-bridge\work\TASK-093-freshfeeds\smoke_server.py`  
命令：`.venv\Scripts\python.exe E:\muse-bridge\work\TASK-093-freshfeeds\smoke_server.py`  
退出码：0  
关键输出：
```
PORT_FREE_BEFORE 8000 TimeoutError
PID 9024
LISTENING True EXIT None
HIT GET / 200 ctype=text/html; charset=utf-8 len=16132 body 以 <!DOCTYPE html> 开头，title 为 freshfeeds · 清泉阅读
HIT GET /health 404 {"detail":"Not Found"}
HIT GET /api/health 404 {"detail":"Not Found"}
HIT GET /docs 404
HIT GET /redoc 404
HIT GET /openapi.json 404
HIT GET /api/me 401 {"detail":"未登录"}
HIT POST /api/login 200 {"token":"...","must_change_password":true}
HIT GET /api/me 200 {"username":"admin","must_change_password":true}
HIT GET /api/feeds 200 []
STOPPED 1
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
PORT_CLOSED_AFTER TimeoutError
```
`STOPPED 1` 是进程被 `Process.terminate()` 结束时的退出码，不是启动失败。启动日志已打印 `Application startup complete` 与 `Uvicorn running on http://127.0.0.1:8000`。  
随后 `Get-Process -Id 9024,34688` 无进程（命令退出码 1，无输出）。端口已关闭。  
未用浏览器点选界面。登录、未登录 401、首页 HTML 用本机 HTTP 请求确认。  
定时线程按默认开启，`_scheduler_loop` 先睡眠一个间隔；进程在数秒内被关掉，没有等到 30 分钟，也就没有第一轮外网抓取。

## 8. 全量测试（审查结束后再跑一次）

命令：`.venv\Scripts\python.exe -m pytest tests/ -q --tb=line`  
退出码：0  
输出：
```
....................................                                     [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\in\TASK-093-freshfeeds\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
36 passed, 1 warning in 7.49s
```

## 9. 收尾 git status

命令：`git status --porcelain`  
工作目录：`E:\muse-bridge\in\TASK-093-freshfeeds`  
退出码：0  
原始输出：（无任何行）

仓库源码未改。`.venv/` 被 `.gitignore` 忽略。报告在 `E:\muse-bridge\out\TASK-093-freshfeeds\`，探针与临时库在 `E:\muse-bridge\work\TASK-093-freshfeeds\`。

