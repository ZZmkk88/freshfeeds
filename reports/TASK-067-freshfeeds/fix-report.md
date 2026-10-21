# freshfeeds 修复记录

只修 review.md 分级清单里的 P1。无 P0。P2 未改。

## P1-1 发现失败仍改掉订阅地址

- 问题编号：P1-1
- 文件：app.py:662-674（原问题在修改前的 app.py:664-666，解析前就 UPDATE）
- 改法：先把发现到的地址放在 `discovered_url`，`parse_feed` 成功之后才 `UPDATE feeds.url`。解析抛错时走原有 except，不执行这条 UPDATE，用户填写的地址保留。发现到合法订阅源时仍会改写地址。

验证命令：

```
E:\muse-bridge\work\TASK-067-freshfeeds\venv\Scripts\python.exe E:\muse-bridge\work\TASK-067-freshfeeds\verify_p1_1.py
E:\muse-bridge\work\TASK-067-freshfeeds\venv\Scripts\python.exe E:\muse-bridge\work\TASK-067-freshfeeds\run_pytest.py
```

`verify_p1_1.py` 输出：

```
bad create 200 {'id': 1, 'warning': '抓取失败：syntax error: line 1, column 0', 'added': 0}
bad stored http://orig.example/ syntax error: line 1, column 0
good create 200 {'id': 2, 'added': 1}
good stored http://orig.example/good.xml 发现后的标题
P1-1 OK
```

非法目标不再把地址改成 `bad.xml`。合法 RSS 仍改写到 `http://orig.example/good.xml`，标题为「发现后的标题」，added=1。

pytest：

```
30 passed, 1 warning in 4.61s
```

退出码 0。警告仍是 StarletteDeprecationWarning，与修改前相同。

## P1-2 OPML 的 htmlUrl 不清洗

- 问题编号：P1-2
- 文件：app.py:1012（修改前是 app.py:1005；P1-1 插入了几行，行号下移）
- 改法：`o.get("htmlUrl")` 先经过已有的 `_clean_url` 再写入 `site_url`。非 http(s) 变成空串。app.py:697 的「新链接为空就沿用旧 site_url」没改：合法的 http(s) htmlUrl 在源本身没有链接时仍然保留；javascript: 因为入库时已经是空串，回退不到。

验证命令：

```
E:\muse-bridge\work\TASK-067-freshfeeds\venv\Scripts\python.exe E:\muse-bridge\work\TASK-067-freshfeeds\verify_p1_2.py
E:\muse-bridge\work\TASK-067-freshfeeds\venv\Scripts\python.exe E:\muse-bridge\work\TASK-067-freshfeeds\run_pytest.py
```

`verify_p1_2.py` 输出：

```
import 200 {'total': 3, 'added': 3, 'skipped': 0, 'failed': 1}
stored https://js-opml.example/rss '' simulated down
stored https://nolink.example/rss ''
stored https://keep.example/rss 'https://keep.example/'
export has javascript False
P1-2 OK
```

抓取失败的 `javascript:alert(1)` 和空链接源上的 `javascript:alert(2)` 都不再入库，导出里没有 `javascript:`。`https://keep.example/` 仍然保留。

## 全量测试（两处都改完之后）

命令：

```
E:\muse-bridge\work\TASK-067-freshfeeds\venv\Scripts\python.exe E:\muse-bridge\work\TASK-067-freshfeeds\run_pytest.py
```

结果：

```
..............................                                           [100%]
30 passed, 1 warning in 4.63s
```

退出码 0。没有失败项。警告仍是修改前就有的 StarletteDeprecationWarning（P2-7，不改依赖版本）。

## git status --porcelain

工作目录：E:\muse-bridge\in\TASK-067-freshfeeds

命令：

```
git status --porcelain
```

输出：

```
 M app.py
```
