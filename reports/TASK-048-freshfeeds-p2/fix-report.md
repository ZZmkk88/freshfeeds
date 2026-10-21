# freshfeeds P2 修复记录

## P2-1 RSS 1.0 源标题和站点链接

- 文件：`app.py:347-352`
- 改法：RDF 分支先取 `{http://purl.org/rss/1.0/}`，从 `channel` 子元素读取带该命名空间的 `title` 和 `link`，再解析条目。
- 验证命令（仓库根）：`E:\muse-bridge\in\TASK-031-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short`
- 结果：`14 passed, 1 warning in 2.26s`（退出码 0）
- 行为：`probe_rdf.py` 输出 `RDF 'RDF 源标题' 'http://example.com/rdf' 1 'RDF 文章'`（修前是 `RDF '' '' 1 'RDF 文章'`）

## P2-2 负数 limit 绕过 200 条上限

- 文件：`app.py:600-604`
- 改法：查询前把 `limit` 小于 1 的改成 1，大于 200 的改成 200，再放进 `LIMIT`。
- 验证命令（仓库根）：`E:\muse-bridge\in\TASK-031-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short`
- 结果：`14 passed, 1 warning in 2.21s`（退出码 0）
- 行为：`probe_limit.py` 在 251 条文章上输出 `LIMIT_NEG 200 count 1`、`LIMIT_500 200 count 200`、`LIMIT_1 200 count 1`。修前同样两篇文章时 `LIMIT_NEG 200 count 2`。

## P2-3 不存在的分类被报成已经订阅

- 文件：`app.py:538-542`
- 改法：`IntegrityError` 的文本含 `foreign key` 时返回「分类不存在」；其余（唯一约束）仍返回「这个源已经订阅过了」。
- 验证命令（仓库根）：`E:\muse-bridge\in\TASK-031-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short`
- 结果：`14 passed, 1 warning in 2.11s`（退出码 0）
- 行为：`probe_cat.py` 输出 `BAD_CAT 400 {"detail":"分类不存在"}`、`DUP 400 {"detail":"这个源已经订阅过了"}`，源列表只有 `https://blog.example.com/feed`。修前不存在的分类也是「这个源已经订阅过了」。

## P2-4 界面没有单个源的刷新按钮

- 文件：`static/index.html:39`（按钮样式）、`static/index.html:179`（源条目按钮）、`static/index.html:210-219`（`refreshOne`）
- 改法：每个源在退订按钮旁加「⟳」，`stopPropagation` 后调用已有 `POST /api/feeds/{id}/refresh`，把新增篇数或失败原因写到 `feedMsg`。
- 验证命令（仓库根）：`E:\muse-bridge\in\TASK-031-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short`
- 结果：`14 passed, 1 warning in 2.25s`（退出码 0）
- 行为：`probe_page.py` 对 `GET /` 输出 `STATUS 200 text/html; charset=utf-8`，`HAS_REFRESH_ONE True`，`HAS_TITLE True`，`HAS_ENDPOINT True`。没有浏览器工具，没有在页面上点按按钮。该接口原有用例 `tests/test_app.py` 的刷新请求仍在这 14 项里通过。窄屏样式原来就把侧栏藏掉（`index.html:57`），单个源按钮跟侧栏一起不可见，刷新全部仍在主栏。

## P2-5 默认库路径文档和实现不一致

- 文件：`README.md:58`
- 改法：默认值改为「`app.py` 所在目录下的 `data/freshfeeds.db`」，说明里写明未设置环境变量时按 `app.py` 的位置解析。对应实现是 `app.py:26-27` 的 `BASE_DIR` 与 `os.path.join(BASE_DIR, "data", "freshfeeds.db")`。
- 验证命令（仓库根）：`E:\muse-bridge\in\TASK-031-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short`
- 结果：`14 passed, 1 warning in 2.10s`（退出码 0）

## P2-6 开发依赖触发 Starlette 弃用警告

- 不改。`requirements-dev.txt:2` 仍是 `httpx==0.28.1`。
- 原因：任务禁止改 requirements 里已有依赖的版本号，除非修的是依赖冲突。全量测试 14 项通过，警告来自虚拟环境里的 `fastapi\testclient.py:1`，不是安装冲突。换 `httpx2` 会改锁定版本，所以保持不动。
