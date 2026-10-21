# TASK-070-freshfeeds 执行记录

开工: 2026-10-21
工作目录: E:\muse-bridge\in\TASK-070-freshfeeds
虚拟环境与探针: E:\muse-bridge\work\TASK-070-freshfeeds
报告: E:\muse-bridge\out\TASK-070-freshfeeds

## 1. 解释器

```
python --version
Python 3.11.9
```

```
py -3 --version
exit: 1
Unable to create process using 'E:\python.exe --version': ???????????
```

README 的 `py -m venv` 在本机走不通。改用 `python`。这是本机启动器问题。

## 2. 装依赖

```
python -m venv E:\muse-bridge\work\TASK-070-freshfeeds\.venv
```

exit 0。

```
Set-Location E:\muse-bridge\in\TASK-070-freshfeeds
E:\muse-bridge\work\TASK-070-freshfeeds\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

exit 0。钉死版本装上：fastapi==0.156.7、uvicorn==0.54.0、python-multipart==0.0.32、httpx==0.28.1、pytest==9.1.1。结尾 `Successfully installed ... fastapi`。未单独计时。

## 3. 全量测试（修复前）

```
E:\muse-bridge\work\TASK-070-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short -o cache_dir=E:\muse-bridge\work\TASK-070-freshfeeds\pytest-cache
```

```
..............................                                           [100%]
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
30 passed, 1 warning in 7.08s
```

覆盖 TEMP 的命令被会话拦住，`tests/test_app.py` 里的 `tempfile.mkdtemp()` 仍写系统 TEMP。

## 4. 起服务并检查

```
E:\muse-bridge\work\TASK-070-freshfeeds\.venv\Scripts\python.exe app.py
```

```
INFO:     Started server process [33372]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

`urllib` 结果摘要：`GET /` 200 `text/html`，正文以 `<!DOCTYPE html>` 开头；`GET /health` 与 `GET /api/health` 404 `{"detail":"Not Found"}`；`/docs` `/redoc` `/openapi.json` 404；无登录 `GET /api/feeds` 401 `未登录`；错密码登录 401 `用户名或密码不对`；`admin` / `admin123` 登录 200 且 `must_change_password` 为 true；`GET /api/me` 200；`POST /api/feeds/refresh-all` 200 `{"feeds":0,"added":0,"failed":0}`。

检查结束后终止该后台进程。工具回执：`killed: Task was terminated successfully`。自启动到终止约 746 秒（含检查空闲）。

## 5. 探针（工作目录脚本，未改仓库）

`probe_logic.py` 要点：

- `http://127.1/`、`http://2130706433/`、`http://0x7f000001/`、`http://0177.0.0.1/`、`http://[::ffff:127.0.0.1]/`、`http://[2002:7f00:1::]/`、`http://169.254.169.254/`、`http://10.1.2.3/` 均 BLOCK。
- `http://198.18.0.1/` 与 `http://93.184.216.34/` ALLOW（与既有口径一致）。
- `http://[::ffff:0:7f00:1]/` ALLOW。
- `http://[fec0::1]/` ALLOW。
- `parse_feed`：`javascript:` 的 site 与条目 url 都变成 `''`；Atom 的 `https://ok.example/a` 保留。
- DNS 钉死：匹配时 `fallback_calls=[]` 且读到 `b'ok'`；换成 `203.0.113.9` 时 `URLError: timed out`，本机监听命中数不增加。
- 304：`fetch 304 ('not_modified', '', '"abc"', '', '')`。

`probe_embed.py` 要点：

```
::ffff:0:127.0.0.1 exploded 0000:0000:0000:0000:ffff:0000:7f00:0001 in_siit True mapped None
::ffff:0:169.254.169.254 in_siit True
craft 0064:ff9b:0001:7f00:0000:0100:0808:0808 rfc6052_v4 127.0.0.1 last32 8.8.8.8
ALLOW http://[::ffff:0:127.0.0.1]/
ALLOW http://[::ffff:0:169.254.169.254]/
ALLOW http://[::ffff:0:10.0.0.1]/
ALLOW http://[64:ff9b:1:7f00:0:100:808:808]/
BLOCK http://[64:ff9b::7f00:1]/
CONNECT fail ::ffff:0:7f00:1 TimeoutError: timed out
CONNECT fail ::ffff:127.0.0.1 OSError: [WinError 10049]
/go10 BlockedUrlError 拒绝抓取内网/保留地址：10.1.2.3（10.1.2.3） seen ['http://127.0.0.1:60349/go10', 'http://10.1.2.3/x']
/godec BlockedUrlError 拒绝抓取内网/保留地址：2130706433（127.0.0.1） seen [..., 'http://2130706433/']
/gofile BlockedUrlError 只允许抓取 http(s) 地址 seen [..., 'file:///C:/Windows/win.ini']
```

## 6. 修复与复测

P1-1 之后：

```
E:\muse-bridge\work\TASK-070-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short -o cache_dir=E:\muse-bridge\work\TASK-070-freshfeeds\pytest-cache
30 passed, 1 warning in 6.63s
```

`check_p1.py`：`::ffff:0:127.0.0.1`、`::ffff:0:10.0.0.1`、`::ffff:0:169.254.169.254` 为 BLOCK；`::ffff:0:8.8.8.8` 与 `::ffff:0:198.18.0.1` 为 ALLOW。此时 NAT64 `/48` 构造地址仍 ALLOW。

P1-2 之后（最后一次全量测试，此后未再改源码）：

```
30 passed, 1 warning in 6.89s
```

`check_p1.py`：`64:ff9b:1:7f00:0:100:808:808` 改为 BLOCK；`64:ff9b:1:808:8:800:7f00:1`（内嵌 8.8.8.8，后缀 127.0.0.1）为 ALLOW。SIIT 私网地址仍 BLOCK。

```
git -C E:\muse-bridge\in\TASK-070-freshfeeds status --porcelain
 M app.py
```
