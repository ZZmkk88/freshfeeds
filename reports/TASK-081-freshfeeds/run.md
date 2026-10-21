# TASK-081-freshfeeds 执行记录

开工时间：2026-10-22

第一步：写本文件首行，随后读仓库结构与 README，再装依赖、跑测试、起服务。

## 环境

- 仓库：`E:\muse-bridge\in\TASK-081-freshfeeds`
- `git status --porcelain`：空（工作区干净）
- `git log -1 --oneline`：`b9b6b10 docs(freshfeeds): DECISIONS.md 记 TASK-063（P1-1 采纳、P2-5~P2-8 关闭理由）`
- `python -V`：`Python 3.11.9`
- `py -0p`：默认 `-V:3.14 * E:\python.exe`（该解释器起不来）；另有 `-V:3.11 C:\Users\xzm\AppData\Local\Programs\Python\Python311\python.exe`
- `py -V:3.11 -V`：`Python 3.11.9`

## 按 README 用 py 建 venv（失败，环境限制）

命令：

```
py -m venv E:\muse-bridge\work\TASK-081-freshfeeds\venv-py-default
```

输出（exit 1）：

```
Unable to create process using 'E:\python.exe -m venv E:\muse-bridge\work\TASK-081-freshfeeds\venv-py-default': ???????????
```

README（Windows）写的是 `py -m venv .venv`。本机 `py` 默认指向损坏的 `E:\python.exe`，不是项目缺陷。改用 `py -V:3.11` 在工作目录建 venv，避免把 `.venv` 写进仓库。

命令：

```
py -V:3.11 -m venv E:\muse-bridge\work\TASK-081-freshfeeds\venv
```

输出：exit 0，无额外输出。

## 装依赖

命令：

```
E:\muse-bridge\work\TASK-081-freshfeeds\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-081-freshfeeds\requirements.txt
```

结果：exit 0。装上 fastapi==0.156.7、uvicorn==0.54.0、python-multipart==0.0.32，以及 starlette 1.9.0、pydantic 2.14.1 等传递依赖。末行：`Successfully installed ... fastapi-0.156.7 ... uvicorn-0.54.0`。

命令：

```
E:\muse-bridge\work\TASK-081-freshfeeds\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-081-freshfeeds\requirements-dev.txt
```

结果：exit 0。装上 httpx==0.28.1、pytest==9.1.1。运行依赖已满足，未改版本号。

## 跑测试（第一次，执行方式错误，不是项目缺陷）

用 `pytest.main()` 从工作目录脚本启动，没有把仓库根放进 `sys.path`，收集阶段失败：

```
ERROR tests/test_app.py
ModuleNotFoundError: No module named 'app'
1 warning, 1 error in 1.06s
```

同时出现已知警告（DECISIONS 记过、明确不改依赖）：

```
fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

下面改用 README 的 `python -m pytest tests/ -q`，在仓库根目录执行。

## 跑测试（README 命令）

工作目录临时库，避免写到系统 TEMP 和仓库：

```
set TEMP=E:\muse-bridge\work\TASK-081-freshfeeds\tmp
set TMP=E:\muse-bridge\work\TASK-081-freshfeeds\tmp
cd /d E:\muse-bridge\in\TASK-081-freshfeeds
E:\muse-bridge\work\TASK-081-freshfeeds\venv\Scripts\python.exe -m pytest tests/ -q -o cache_dir=E:\muse-bridge\work\TASK-081-freshfeeds\pytest_cache --basetemp E:\muse-bridge\work\TASK-081-freshfeeds\tmp
```

输出（exit 0）：

```
...............................                                          [100%]
31 passed, 1 warning in 6.63s
```

警告原文：

```
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

31 项全部通过。警告与 DECISIONS 里「不改依赖版本」的记录一致，不记为项目缺陷。

## 起服务

数据库放到工作目录，避免在仓库里生成 `data/freshfeeds.db`。`HOST`/`PORT` 用 README 默认值。未设置 `FRESHFEEDS_SCHEDULER`，代码默认开启（`app.py:33`）。

命令：

```
E:\muse-bridge\work\TASK-081-freshfeeds\venv\Scripts\python.exe E:\muse-bridge\work\TASK-081-freshfeeds\start_server.py
```

`start_server.py` 设置 `FRESHFEEDS_DB`、`HOST=127.0.0.1`、`PORT=8000` 后以 `__main__` 执行仓库里的 `app.py`。

启动日志：

```
INFO:     Started server process [10500]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

## 首页 / 健康检查 / 登录

命令：

```
E:\muse-bridge\work\TASK-081-freshfeeds\venv\Scripts\python.exe E:\muse-bridge\work\TASK-081-freshfeeds\probe_http.py
```

输出：

```
READY 200
/	200	text/html; charset=utf-8	<!DOCTYPE html> ... <title>freshfeeds · 清泉阅读</title>
/health	404	application/json	{"detail":"Not Found"}
/docs	404	application/json	{"detail":"Not Found"}
/redoc	404	application/json	{"detail":"Not Found"}
/openapi.json	404	application/json	{"detail":"Not Found"}
/api/me	401	application/json	{"detail":"未登录"}
/api/feeds	401	application/json	{"detail":"未登录"}
LOGIN 200 must_change True token_len 43
ME 200 {"username":"admin","must_change_password":true}
REFRESH_ALL 200 {"feeds":0,"added":0,"failed":0}
```

服务访问日志对应：`GET /` 200，`GET /health` 404，`GET /docs` 404，`GET /redoc` 404，`GET /openapi.json` 404，未登录 `GET /api/me` 与 `GET /api/feeds` 401，`POST /api/login` 200，带 token 的 `GET /api/me` 200，`POST /api/feeds/refresh-all` 200。

README 没有写健康检查路径。代码里也没有 `/health`，所以 404 与文档一致，不记缺陷。

## 关掉服务

命令：`Stop-Process -Id 10500`（exit 0）。后台任务随后退出，exit code 1（进程被结束，不是启动失败）。存活约 220 秒。

确认：

- `Get-Process -Id 10500`：exit 1，`FullyQualifiedErrorId : NoProcessFoundForGivenId`
- `netstat -ano -p tcp | findstr :8000`：exit 1，无输出（没有 :8000 的 TCP 行）
- 再连 `127.0.0.1:8000`：`CLOSED TimeoutError timed out`（本机无监听时这次是超时，不是 HTTP 200）

## 行为探针（不访问外网）

`probe_behavior.py`：SSRF 字面量、八进制/十进制/十六进制、IPv6 映射、6to4、NAT64、localhost、重定向第二跳、重定向跟随、DNS 钉死、HTML 发现改写地址、空 JSON 的「全部标已读 / 刷新全部」、`offset=-1`、`/docs`。结果全部符合当前实现（细节见 review.md）。`probe_ssrf2.py`：文档网段与 `fec0::/10` 放行；带 userinfo 的地址报「网址主机名含混」并拒绝。`probe_clean.py`：`parse_feed` 把频道和条目的 `javascript:` 置成空串，正常 https 保留。

## 收尾全量测试（无源码改动后再跑一遍）

同一条 `run_pytest.cmd`（仓库根目录 `python -m pytest tests/ -q`）。

```
...............................                                          [100%]
31 passed, 1 warning in 9.37s
PYTEST_EXIT:0
```

警告仍是 StarletteDeprecationWarning。没有失败项。

## git status --porcelain（收尾）

```
git -C E:\muse-bridge\in\TASK-081-freshfeeds status --porcelain
```

exit 0，无输出。仓库工作区干净。未改源码。
