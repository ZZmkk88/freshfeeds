# TASK-048 freshfeeds P2 执行记录

开工：2026-10-21。工作目录 `E:\muse-bridge\in\TASK-048-freshfeeds-p2`。先读上一轮审查 `E:\muse-bridge\out\TASK-031-freshfeeds\review.md`，本轮只处理其中 P2，按报告顺序最多 8 条。

## 1. 环境

`python --version` → `Python 3.11.9`（退出码 0）。

本仓库 `Test-Path .venv\Scripts\python.exe` → `False`。上一轮环境 `E:\muse-bridge\in\TASK-031-freshfeeds\.venv\Scripts\python.exe` 存在（`True`）。requirements 版本与上一轮锁定一致，本轮直接用该解释器，工作目录仍是本仓库根。不新建 venv，不改依赖版本。

## 2. 修改前全量测试

命令（仓库根）：

```powershell
E:\muse-bridge\in\TASK-031-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

退出码 0。摘要：

```
14 passed, 1 warning in 2.99s
```

警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 来自 `E:\muse-bridge\in\TASK-031-freshfeeds\.venv\Lib\site-packages\fastapi\testclient.py:1`。

## 3. 修前行为探测

命令：

```powershell
E:\muse-bridge\in\TASK-031-freshfeeds\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-048-freshfeeds-p2\probe_p2.py
```

工作目录为仓库根。退出码 0。输出：

```
RDF '' '' 1 'RDF 文章'
LOGIN 200
ADD 200 {"id":1,"added":2}
LIMIT_NEG 200 count 2
LIMIT_1 200 count 1
BAD_CAT 400 {"detail":"这个源已经订阅过了"}
FEEDS [('https://blog.example.com/feed', None)]
```

SQLite 行为（内存库，`probe_sql.py`，退出码 0）：

```
FK IntegrityError 'FOREIGN KEY constraint failed' SQLITE_CONSTRAINT_FOREIGNKEY
UNIQ 'UNIQUE constraint failed: feeds.url' SQLITE_CONSTRAINT_UNIQUE
LIMIT_NEG_ROWS 250
LIMIT_200_ROWS 200
MIN_NEG -1
```

`min(-1, 200)` 得到 `-1`。同一张 250 行的表，`LIMIT -1` 返回 250 行，`LIMIT 200` 返回 200 行。

## 4. P2-1 之后的全量测试

改 `app.py:347-352` 后：

```powershell
E:\muse-bridge\in\TASK-031-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

退出码 0。`14 passed, 1 warning in 2.26s`。

`probe_rdf.py` 退出码 0：`RDF 'RDF 源标题' 'http://example.com/rdf' 1 'RDF 文章'`。

## 5. P2-2 之后的全量测试

改 `app.py:600-604` 后：

```powershell
E:\muse-bridge\in\TASK-031-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

退出码 0。`14 passed, 1 warning in 2.21s`。

`probe_limit.py` 退出码 0：

```
LIMIT_NEG 200 count 1
LIMIT_500 200 count 200
LIMIT_1 200 count 1
```

## 6. P2-3 之后的全量测试

改 `app.py:538-542` 后：

```powershell
E:\muse-bridge\in\TASK-031-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

退出码 0。`14 passed, 1 warning in 2.11s`。

`probe_cat.py` 退出码 0：

```
BAD_CAT 400 {"detail":"分类不存在"}
DUP 400 {"detail":"这个源已经订阅过了"}
FEEDS ['https://blog.example.com/feed']
```

## 7. P2-4 之后的全量测试

改 `static/index.html:39`、`179`、`210-219` 后：

```powershell
E:\muse-bridge\in\TASK-031-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

退出码 0。`14 passed, 1 warning in 2.25s`。

`probe_page.py` 退出码 0：

```
STATUS 200 text/html; charset=utf-8
HAS_REFRESH_ONE True
HAS_TITLE True
HAS_ENDPOINT True
HAS_REFRESH_ALL True
HAS_UNSUB True
```

## 8. P2-5 之后的全量测试

改 `README.md:58` 后：

```powershell
E:\muse-bridge\in\TASK-031-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

退出码 0。`14 passed, 1 warning in 2.10s`。

P2-6 未改 `requirements-dev.txt`。
