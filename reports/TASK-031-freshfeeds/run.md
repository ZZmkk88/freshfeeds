# TASK-031-freshfeeds 执行记录

开工时间：2026-10-21。执行方：Grok Build。工作目录：E:\muse-bridge\in\TASK-031-freshfeeds。

## 0. 环境探测（2026-10-21 18:55:45）

命令：

```powershell
py -3 --version
python --version
git status --porcelain
git rev-parse --is-inside-work-tree
Get-ChildItem -Force -Name
```

输出摘要：

- `py -3 --version` 失败：`Unable to create process using 'E:\python.exe --version'`（本机 py 启动器指向不存在的 E:\python.exe）。
- `python --version` → `Python 3.11.9`。
- `git rev-parse --is-inside-work-tree` → `true`。
- `git status --porcelain` 无输出（工作区干净）。
- 仓库文件：.git、.gitignore、app.py、LICENSE、NOTES.md、README.md、requirements.txt、requirements-dev.txt、UPSTREAM.md、static/、tests/。
- `.gitignore` 已忽略 `.venv/`、`data/`、`*.db`、`__pycache__/`、`.pytest_cache/`。

## 1. 安装依赖

README Windows 步骤写的是 `py -m venv .venv`。本机 `py` 启动器坏了，改用已验证可用的 `python`（3.11.9，满足 README 的 3.10+）。虚拟环境放在仓库 `.venv`（与 README 一致，已被 gitignore）。

命令（工作目录 `E:\muse-bridge\in\TASK-031-freshfeeds`）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

结果：两条命令退出码均为 0。

pip 关键输出：

```
Collecting fastapi==0.156.7
Collecting uvicorn==0.54.0
Collecting python-multipart==0.0.32
Collecting httpx==0.28.1
Collecting pytest==9.1.1
Successfully installed ... fastapi-0.156.7 ... httpx-0.28.1 ... pytest-9.1.1 ... python-multipart-0.0.32 ... starlette-1.9.0 ... uvicorn-0.54.0
```

依赖版本与 requirements 锁定值一致，无冲突。

## 2. 全量测试（修复前）

命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

输出：

```
..............                                                           [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\in\TASK-031-freshfeeds\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
14 passed, 1 warning in 2.17s
```

结论：14 项测试全部通过。警告来自 Starlette 对 httpx 1.x TestClient 的弃用提示，不是失败。测试进程按 `tests/test_app.py` 自己的 `tempfile.mkdtemp()` 把数据库放到系统临时目录（测试代码如此，未改测试）。pytest 自报耗时 2.17s。

## 3. 按 README 启动服务并探测

数据库放到工作目录，避免在仓库里生成 `data/freshfeeds.db`。调度器保持代码默认（不设置 `FRESHFEEDS_SCHEDULER`）。脚本：`E:\muse-bridge\work\TASK-031-freshfeeds\serve_smoke.py`（子进程执行仓库里的 `python app.py`，探测后 `terminate`）。

命令：

```powershell
.\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-031-freshfeeds\serve_smoke.py
```

输出：

```
INFO:     Started server process [28960]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
READY=True PID=14304 EXIT=None
GET / -> 200 type=text/html; charset=utf-8 body=b'<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, ini'
GET /health -> HTTP 404 type=application/json body=b'{"detail":"Not Found"}'
GET /api/health -> HTTP 404 type=application/json body=b'{"detail":"Not Found"}'
GET /api/feeds -> HTTP 401 type=application/json body=b'{"detail":"\xe6\x9c\xaa\xe7\x99\xbb\xe5\xbd\x95"}'
GET /docs -> 200 type=text/html; charset=utf-8 body=b'\n    <!DOCTYPE html>\n    <html>\n    <head>\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  '
STOPPED exit=1
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:62692 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:62693 - "GET /health HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:62694 - "GET /api/health HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:62695 - "GET /api/feeds HTTP/1.1" 401 Unauthorized
INFO:     127.0.0.1:62696 - "GET /docs HTTP/1.1" 200 OK
```

`/api/feeds` 响应体里的 `\xe6\x9c\xaa\xe7\x99\xbb\xe5\xbd\x95` 是「未登录」的 UTF-8。进程退出码 1 来自探测脚本对子进程调用 `terminate()`，出现在 5 个请求都返回之后。README 没有声明 `/health`。

## 4. 行为探测（修复前，仅本地）

命令：

```powershell
.\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-031-freshfeeds\probe_behavior.py
.\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-031-freshfeeds\probe_behavior2.py
.\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-031-freshfeeds\probe_entity.py
```

`probe_behavior.py` 在创建 TestClient 时没用上下文管理器，lifespan 没跑，登录时报 `sqlite3.OperationalError: no such table: users`。该失败是探测脚本的写法问题。在此之前已经打印出的结果有效：

```
FETCH_FILE ok marker len 225
RDF '' '' 1 RDF 文章
PARSE_JS_URL javascript:alert(1)
```

`probe_behavior2.py`（退出码 0）关键行：

```
LOGIN 200 must_change True
FEEDS_WHILE_MUST_CHANGE 200
ENTRIES_WHILE_MUST_CHANGE 200
CHANGE_PW 200
OLD_TOKEN_AFTER_PW_CHANGE 200 {"username":"admin","must_change_password":false}
STORED_ENTRY_URL javascript:alert(1)
FAKE_FETCH file:///E:/muse-bridge/work/TASK-031-freshfeeds/localfeed.xml
OPML_FILE_URL 200 {"total":1,"added":1,"skipped":0,"failed":1}
OPML_ENTITY 200 {"total":1,"added":1,"skipped":0,"failed":0}
OPML_XXE 400 {"detail":"这不是合法的 OPML/XML 文件"}
REFRESH_ALL 200 {"feeds":3,"added":0,"failed":1}
LIMIT_NEG 200 count 2
BAD_CAT 400 {"detail":"这个源已经订阅过了"}
APP_FETCH_REDIRECT_ERR HTTPError HTTP Error 302: Found - Redirection to url 'file:///E:/muse-bridge/work/TASK-031-freshfeeds/localfeed.xml' is not allowed
```

`probe_entity.py`（退出码 0）：

```
ENTITY_TEXT EXPANDED-ENTITY
DISCOVER file:///E:/muse-bridge/work/TASK-031-freshfeeds/localfeed.xml
```

未访问外网页面。OPML 与订阅探测都把 `fetch_url` 换成了本地桩，或只请求 `127.0.0.1` / `file://` 工作目录里的文件。

## 5. 修复后的测试

每改一条 P1 都重跑了 `.\.venv\Scripts\python.exe -m pytest tests/ -q --tb=line`（或 `--tb=short`），并另跑工作目录里的 `verify1.py` 到 `verify5.py`。五次全量结果都是 14 passed：

- P1-1 之后：`14 passed, 1 warning in 1.94s`
- P1-2 之后：`14 passed, 1 warning in 1.92s`
- P1-3 之后：`14 passed, 1 warning in 1.95s`
- P1-4 之后：`14 passed, 1 warning in 1.92s`
- P1-5 之后：`14 passed, 1 warning in 1.90s`

全部改完后再跑一次：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q --tb=line
```

```
14 passed, 1 warning in 1.89s
```

警告仍是 StarletteDeprecationWarning（httpx / TestClient），没有失败用例。各次 verify 脚本的输出写在 `fix-report.md`。没有浏览器工具，改密弹窗和链接点击没有在浏览器里点过；接口行为由 verify3 / verify2 覆盖，前端改动用源码字符串核对。





