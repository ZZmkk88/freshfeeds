# freshfeeds 第二轮审查（P2）

结论：全量测试 14 项通过，没有 P0。上一轮 P2 共 6 条，本仓库里 1–5 仍然在，按原顺序修；第 6 条是已锁定的开发依赖版本，不改。行号是修改前的。

## 测试

仓库根执行：

```powershell
E:\muse-bridge\in\TASK-031-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

```
14 passed, 1 warning in 2.99s
```

警告：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 出处 `E:\muse-bridge\in\TASK-031-freshfeeds\.venv\Lib\site-packages\fastapi\testclient.py:1`。本仓库没有 `.venv`，用的是上一轮已装好的同一套依赖。`python --version` 为 `Python 3.11.9`。

## P2 核对

1. RSS 1.0 源标题和站点链接仍为空。`app.py:343-344` 用无命名空间的 `title` / `link` 读 channel；`app.py:346-358` 只在 RDF 分支用 `{http://purl.org/rss/1.0/}` 读条目。探测 `probe_p2.py`：`RDF '' '' 1 'RDF 文章'`。
2. `limit=-1` 仍会变成负数上限。`app.py:596` 是 `min(limit, 200)`。探测：库里 2 条时 `LIMIT_NEG 200 count 2`，`LIMIT_1 200 count 1`。内存库对照：`min(-1, 200)` 为 `-1`；250 行上 `LIMIT -1` 返回 250 行，`LIMIT 200` 返回 200 行（`probe_sql.py`）。
3. 不存在的分类 id 仍报「已经订阅过了」。`app.py:534-536` 把所有 `IntegrityError` 收成这一句。探测 `BAD_CAT 400 {"detail":"这个源已经订阅过了"}`，当时库里只有 `https://blog.example.com/feed`。外键失败原文是 `FOREIGN KEY constraint failed`（`SQLITE_CONSTRAINT_FOREIGNKEY`），唯一约束原文是 `UNIQUE constraint failed: feeds.url`。
4. 界面仍没有单个源的刷新按钮。`static/index.html:177-178` 每个源只有退订；`index.html:99` 只有「刷新全部」。后端 `app.py:555-557` 已有 `POST /api/feeds/{fid}/refresh`。
5. 默认库路径的文档仍和实现不一致。`README.md:58` 写默认 `data/freshfeeds.db`。`app.py:26-27` 是 `os.path.join(BASE_DIR, "data", "freshfeeds.db")`，`BASE_DIR` 为 `app.py` 所在目录。
6. 开发依赖仍会打出 Starlette 弃用警告。`requirements-dev.txt:2` 锁定 `httpx==0.28.1`。测试通过。本条不改，理由见清单。

## 分级修复清单

### P0

无。修改前全量测试 14 项通过。

### P1

本轮不新开 P1。任务限定只收口上一轮 P2。

### P2（本轮按此顺序修，最多 8 条）

1. RSS 1.0 源标题、站点链接为空。`app.py:346-358`。修法：RDF 分支用 `{http://purl.org/rss/1.0/}channel` 读取 `title` 和 `link`。
2. 负数 `limit` 绕过 200 条上限。`app.py:596`。修法：把 `limit` 夹到 1 到 200。
3. 外键失败和重复订阅共用一句错误。`app.py:534-536`。修法：错误文本含 `foreign key` 时返回「分类不存在」，唯一约束仍返回「这个源已经订阅过了」。
4. 源列表没有单个刷新。`static/index.html:177-178`。修法：源条目加按钮，调用已有 `POST /api/feeds/{id}/refresh`。
5. 默认数据库路径文档不准。`README.md:58`。修法：写明默认文件在 `app.py` 所在目录下的 `data/freshfeeds.db`。
6. `httpx==0.28.1` 触发弃用警告。`requirements-dev.txt:2`。不改：任务禁止改已有依赖的版本号，这里不是依赖冲突，测试是通过的。
