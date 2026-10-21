# TASK-063-freshfeeds 执行记录

开始时间：2026-10-21
工作目录：E:\muse-bridge\in\TASK-063-freshfeeds
执行方：Grok Build（本地验收）
状态：开工。先读仓库结构与 README，再装依赖、跑测试、起服务。

## 1. 环境探测（README 的 `py -m venv`）

命令：
```
py -3 --version
py -3.11 --version
py -m venv E:\muse-bridge\work\TASK-063-freshfeeds\venv-readme-try
```

输出：
```
py -3 --version
exit: 1
Unable to create process using 'E:\python.exe --version': ???????????

py -3.11 --version
exit: 0
Python 3.11.9

py -0p（本机此前已看到）
-V:3.14 *        E:\python.exe
-V:3.11          C:\Users\xzm\AppData\Local\Programs\Python\Python311\python.exe

py -m venv E:\muse-bridge\work\TASK-063-freshfeeds\venv-readme-try
exit: 1
Unable to create process using 'E:\python.exe -m venv E:\muse-bridge\work\TASK-063-freshfeeds\venv-readme-try': ???????????
```

判定：README 写的 `py -m venv` 在本机失败，原因是默认 `py` 指向损坏的 `E:\python.exe`（3.14），不是项目代码错误。README 要求 Python 3.10+。改用本机可用的 `py -3.11`（3.11.9）创建虚拟环境。

venv 放在工作目录，不放进仓库：
```
py -3.11 -m venv E:\muse-bridge\work\TASK-063-freshfeeds\.venv
```
exit: 0

## 2. 安装依赖

按 README：先 `pip install -r requirements.txt`，再 `pip install -r requirements-dev.txt`。
使用 venv 的 pip，不改仓库内文件。

命令：
```
E:\muse-bridge\work\TASK-063-freshfeeds\.venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-063-freshfeeds\requirements.txt
```
exit: 0
关键行：
```
Successfully installed annotated-doc-0.0.5 annotated-types-0.8.0 anyio-4.15.1 click-8.5.0 fastapi-0.156.7 h11-0.16.0 idna-3.20 opentelemetry-api-1.45.1 pydantic-2.14.1 pydantic-core-2.50.1 python-multipart-0.0.32 starlette-1.9.0 typing-extensions-4.16.0 typing-inspection-0.4.4 uvicorn-0.54.0
```
直接依赖版本与 requirements.txt 一致：fastapi 0.156.7、uvicorn 0.54.0、python-multipart 0.0.32。传递依赖未钉死（starlette 1.9.0、pydantic 2.14.1 等由 pip 解析）。

命令：
```
E:\muse-bridge\work\TASK-063-freshfeeds\.venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-063-freshfeeds\requirements-dev.txt
```
exit: 0
关键行：
```
Successfully installed certifi-2026.10.19 colorama-0.4.6 httpcore-1.0.9 httpx-0.28.1 iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.1.1
```
httpx 0.28.1、pytest 9.1.1 与 requirements-dev.txt 一致。

## 3. 全量测试

按 README：在仓库目录执行 `python -m pytest tests/ -q`。
pytest 缓存和 basetemp 指到工作目录，避免写入仓库。第一次带 `$env:TEMP` 的命令被环境拒绝执行，未改 TEMP。测试自身的 `tempfile.mkdtemp()` 仍走系统临时目录（测试代码如此，未改测试）。

命令（在仓库目录执行）：
```
Set-Location E:\muse-bridge\in\TASK-063-freshfeeds; E:\muse-bridge\work\TASK-063-freshfeeds\.venv\Scripts\python.exe -m pytest tests\ -q --tb=short -p no:cacheprovider --basetemp=E:\muse-bridge\work\TASK-063-freshfeeds\pytest-tmp
```
exit: 0
```
...........................                                              [100%]
============================== warnings summary ===============================
..\..\work\TASK-063-freshfeeds\.venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\work\TASK-063-freshfeeds\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
27 passed, 1 warning in 6.86s
```
27 项全部通过。唯一警告是 Starlette 弃用 httpx TestClient（DECISIONS.md 已记录不修，且不许改依赖版本号）。

## 4. 安全与行为探测（不访问外网）

命令：
```
E:\muse-bridge\work\TASK-063-freshfeeds\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-063-freshfeeds\probe_security.py
```
exit: 0
关键输出（登录 token 已从本记录删去，原文里有一串 token）：
```
BLOCK http://127.0.0.1/feed ...拒绝抓取内网/保留地址
BLOCK http://2130706433/ ...（127.0.0.1）
BLOCK http://0x7f000001/
BLOCK http://0177.0.0.1/
BLOCK http://localhost/feed
BLOCK http://[::1]/
BLOCK http://[::ffff:127.0.0.1]/
BLOCK http://[2002:7f00:1::]/
BLOCK http://[64:ff9b::7f00:1]/
ALLOW http://[fec0::1]/ ['fec0::1']
BLOCK http://169.254.169.254/latest/meta-data
ALLOW http://198.18.0.1/ ['198.18.0.1']
ALLOW http://192.0.2.1/ ['192.0.2.1']
ALLOW http://198.51.100.1/ ['198.51.100.1']
ALLOW http://[2001:db8::1]/ ['2001:db8::1']
BLOCK http://127.0.0.1%23@8.8.8.8/feed 网址主机名含混
=== parse_feed site_url javascript ===
('T', '', [{'guid': 'g', ... 'url': ''}])
GET /health 404 {"detail":"Not Found"}
GET /docs 404
LOGOUT 404 {"detail":"Not Found"}
ME_AFTER_LOGOUT_ATTEMPT 200
OFFSET-1 200 []
SQLI 200 []
OPML 200 {"total":1,"added":1,"skipped":0,"failed":0}
FEED https://news.example.com/rss site= 'javascript:alert(1)'
EXPORT_HAS_JS True
... htmlUrl="javascript:alert(1)" ...
```

命令：
```
E:\muse-bridge\work\TASK-063-freshfeeds\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-063-freshfeeds\probe_pin.py
```
exit: 0
关键输出：
```
http://user:pass@8.8.8.8/feed
  connect ERR InvalidURL nonnumeric port: 'pass@8.8.8.8'
  BLOCK 网址主机名含混，已拒绝抓取
http://8.8.8.8#@127.0.0.1/feed
  ALLOW ['8.8.8.8']
PIN_RESULT_EXC URLError <urlopen error [WinError 10061] 由于目标计算机积极拒绝，无法连接。>
```
钉死解析生效：校验结果被换成 127.0.0.2 后，没有连上监听在 127.0.0.1 上的本地服务（连接被拒绝）。`#@127.0.0.1` 在 fragment 里，主机仍是 8.8.8.8，放行不是 SSRF。

## 5. 起服务

端口 8000 没有本地监听。`netstat -ano | findstr :8000` 只命中一条远端 IPv6 地址里的字面量 `8000`，不是本机 8000 端口。

没有直接把 `python app.py` 丢在后台后用 taskkill 结束（任务禁止 taskkill）。用工作目录脚本以与 `app.py` 的 `__main__` 相同的方式调用 `uvicorn`（同一 app 对象，HOST 默认 127.0.0.1，PORT 默认 8000）。数据库放到工作目录 `smoke.db`，避免在仓库里生成 `data/`。调度器保持默认开启；空库，线程先 sleep，冒烟期间不会去抓外网。

命令：
```
E:\muse-bridge\work\TASK-063-freshfeeds\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-063-freshfeeds\smoke_server.py
```
exit: 0
输出片段（token 已省略）：
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
START host=127.0.0.1 port=8000
SERVER_STARTED True thread True
INFO:     127.0.0.1:54408 - "GET / HTTP/1.1" 200 OK
HIT / 200 text/html; charset=utf-8 b'<!DOCTYPE html>\n<html lang="zh-CN">...\n<title>freshfeeds \xc2\xb7 \xe6\xb8\x85\xe6\xb3\x89\xe9\x98\x85\xe8\xaf\xbb</title>\n<st'
INFO:     127.0.0.1:54409 - "GET /health HTTP/1.1" 404 Not Found
HIT /health HTTP 404 application/json b'{"detail":"Not Found"}'
INFO:     127.0.0.1:54410 - "GET /api/me HTTP/1.1" 401 Unauthorized
HIT /api/me HTTP 401 application/json b'{"detail":"\xe6\x9c\xaa\xe7\x99\xbb\xe5\xbd\x95"}'
INFO:     127.0.0.1:54411 - "GET /docs HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:54412 - "GET /openapi.json HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:54413 - "POST /api/login HTTP/1.1" 200 OK
LOGIN 200 b'{"token":"<已省略>","must_change_password":true}'
INFO:     Shutting down
STOPPED True
INFO:     Application shutdown complete.
INFO:     Finished server process [36924]
```
首页 200，正文是 freshfeeds 清泉阅读页面。没有 `/health`（404）。未登录访问 `/api/me` 返回 401。默认账号可以登录，`must_change_password` 为 true。`/docs` 与 `/openapi.json` 关闭。进程已退出。

## 6. P1-1 修复后验证

只改 `app.py` 导入 OPML 时的 `htmlUrl`，改为 `_clean_url(...)`。

命令：
```
E:\muse-bridge\work\TASK-063-freshfeeds\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-063-freshfeeds\verify_p1_opml.py
```
exit: 0
```
IMPORT 200 {"total":2,"added":2,"skipped":0,"failed":0}
JS_SITE ''
OK_SITE 'https://ok.example/'
EXPORT_HAS_JS False
EXPORT_HAS_OK True
VERIFY_OK
```

全量测试重跑：
```
Set-Location E:\muse-bridge\in\TASK-063-freshfeeds; E:\muse-bridge\work\TASK-063-freshfeeds\.venv\Scripts\python.exe -m pytest tests\ -q --tb=short -p no:cacheprovider --basetemp=E:\muse-bridge\work\TASK-063-freshfeeds\pytest-tmp
```
exit: 0
```
27 passed, 1 warning in 6.04s
```

```
git -C E:\muse-bridge\in\TASK-063-freshfeeds status --porcelain
```
```
 M app.py
```

耗时：修前 pytest 自报 6.86s，修后 pytest 自报 6.04s。pip 与服务冒烟没有单独计时，都是一次成功退出。


