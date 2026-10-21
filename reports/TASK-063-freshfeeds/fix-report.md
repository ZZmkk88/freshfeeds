# freshfeeds 修复记录

只改了 review.md 清单里的 P1-1。P0 没有。P2 不改。

## P1-1 OPML 的 htmlUrl 未过滤 javascript:

- 问题编号：P1-1
- 文件：`app.py:998`（改前是 `o.get("htmlUrl") or ""`）
- 改法：导入写入 `site_url` 时改为 `_clean_url(o.get("htmlUrl") or "")`。非 http(s) 入库为空串，与 `parse_feed` 已有的站点链接规则一致。`https://` 链接保持原样。没有改导出、没有改刷新时「空则保留旧值」的逻辑：脏值不再被写进去，空链接就不会再把 `javascript:` 留住。
- 验证命令：
```
E:\muse-bridge\work\TASK-063-freshfeeds\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-063-freshfeeds\verify_p1_opml.py
```
- 真实输出（exit 0）：
```
IMPORT 200 {"total":2,"added":2,"skipped":0,"failed":0}
JS_SITE ''
OK_SITE 'https://ok.example/'
EXPORT_HAS_JS False
EXPORT_HAS_OK True
VERIFY_OK
```
`htmlUrl="javascript:alert(1)"` 的源，`site_url` 为空，导出里没有 `javascript:`。`htmlUrl="https://ok.example/"` 仍保留。另有 Starlette 弃用警告，与改动无关。

## 未改的项

- P0：无。
- P2 全部不改。原因：不是跑不起来，也不是本轮要收口的那条安全缺口。其中默认口令不强制改密（DECISIONS.md:7）、httpx 弃用警告（不许改依赖版本）、两处测试缺口（不许改测试）明确不动。`fec0::/10`、文档地址段、注销接口、userinfo 拒绝，留在 review.md 的 P2，避免顺手改 SSRF 比较或加新接口。

## 改动后全量测试

命令（仓库目录）：
```
E:\muse-bridge\work\TASK-063-freshfeeds\.venv\Scripts\python.exe -m pytest tests\ -q --tb=short -p no:cacheprovider --basetemp=E:\muse-bridge\work\TASK-063-freshfeeds\pytest-tmp
```
exit 0。结果行：
```
...........................                                              [100%]
============================== warnings summary ===============================
..\..\work\TASK-063-freshfeeds\.venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\work\TASK-063-freshfeeds\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
27 passed, 1 warning in 6.04s
```
没有失败项。警告与修前相同，来自依赖，不是断言失败。

## git status

命令：
```
git -C E:\muse-bridge\in\TASK-063-freshfeeds status --porcelain
```
输出：
```
 M app.py
```
工作区只改了 `app.py`，改动还在。没有 commit，没有 push。
