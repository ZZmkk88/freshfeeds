# freshfeeds 修复记录

只修 review.md 清单中的 P1-1、P1-2、P1-3。P0 无。P2 不改。

## P1-1 属性里的引号未转义

问题编号：P1-1

文件：`static/index.html:147-151`（原 `esc` 在 static/index.html:147，单行）。`safeHref` 仍在 static/index.html:152，继续调用 `esc`。

改法：`esc` 改为一次替换，把 `& < > " '` 分别写成 `&amp; &lt; &gt; &quot; &#39;`。`title` 属性和 `href` 都走这个函数。

验证命令：

```
E:\muse-bridge\work\TASK-044-freshfeeds\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

（经 `run_pytest.bat`，cwd 为仓库）

输出：

```
26 passed, 1 warning in 6.09s
EXIT=0
```

警告仍是 StarletteDeprecationWarning，与本次改动无关。

另用与 `esc` 相同的替换检查样本 `https://example.com/"onmouseover="alert(1)`：

```
OUT https://example.com/&quot;onmouseover=&quot;alert(1)
QUOTE_LEFT False
ATTR <a href="https://example.com/&quot;onmouseover=&quot;alert(1)">
BREAKS_ATTR False
```

没有浏览器工具，页面点击流程未在浏览器里重放。测试文件不覆盖这段前端脚本。

Node.js v24.21.0 直接执行文件里的 `esc`（`node E:\muse-bridge\work\TASK-044-freshfeeds\verify_esc.js`）：

```
OUT https://example.com/&quot;onmouseover=&quot;alert(1)
QUOTE_LEFT false
ATTR <a href="https://example.com/&quot;onmouseover=&quot;alert(1)">
BREAKS_ATTR false
```

## P1-2 抓取校验放行非 http(s)、解析失败和回环别名

问题编号：P1-2

文件：`app.py:80-111`（原校验在 app.py:80-95）。新增 `_addresses_for_host`。

改法：scheme 不是 `http`/`https` 就拒绝；`inet_aton` 能解析的主机按得到的 IPv4 做网段判断；DNS 失败改为抛 `BlockedUrlError`，不再直接 return。`198.18.0.1` 仍不在拦截清单里。

验证命令：

```
E:\muse-bridge\work\TASK-044-freshfeeds\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

输出：

```
26 passed, 1 warning in 6.08s
EXIT=0
```

探针 `verify_ssrf.py`（`refresh_feed` 换成空操作，没有向外抓页面）：

```
BLOCK ftp://93.184.216.34/feed.xml | 只允许抓取 http(s) 地址
BLOCK gopher://93.184.216.34:70/x | 只允许抓取 http(s) 地址
BLOCK http://2130706433/feed.xml | 拒绝抓取内网/保留地址：2130706433（127.0.0.1）
BLOCK http://0x7f000001/ | 拒绝抓取内网/保留地址：0x7f000001（127.0.0.1）
BLOCK http://127.1/ | 拒绝抓取内网/保留地址：127.1（127.0.0.1）
BLOCK http://0177.0.0.1/ | 拒绝抓取内网/保留地址：0177.0.0.1（127.0.0.1）
BLOCK http://127.0.0.1/feed.xml | 拒绝抓取内网/保留地址：127.0.0.1（127.0.0.1）
ALLOW http://93.184.216.34/
ALLOW http://198.18.0.1/
BLOCK http://[::1]/ | 拒绝抓取内网/保留地址：::1（::1）
BLOCK file:///etc/passwd | 只允许抓取 http(s) 地址
FAIL_CLOSED 域名解析失败，已拒绝抓取：example.test
LOGIN 200
OPML_FTP 200 {"total":1,"added":0,"skipped":0,"failed":1}
CREATE_DECIMAL 400 {"detail":"拒绝抓取内网/保留地址：2130706433（127.0.0.1）"}
FEED_URLS []
```

## P1-3 订阅源 XML 展开内部实体

问题编号：P1-3

文件：`app.py:418-420`（`parse_feed` 在解析前拒绝声明）。

改法：去掉 NUL 后做大写匹配，正文含 `<!DOCTYPE` 或 `<!ENTITY` 时抛 `ValueError("不接受带 DTD 或实体声明的订阅源")`，不交给 `ET.fromstring`。正常 RSS 仍走原来的解析。OPML 原有检查未改。

验证命令：

```
E:\muse-bridge\work\TASK-044-freshfeeds\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

输出：

```
26 passed, 1 warning in 6.01s
EXIT=0
```

探针 `verify_dtd.py`：

```
BOMB_REJECTED 不接受带 DTD 或实体声明的订阅源
EXT_REJECTED 不接受带 DTD 或实体声明的订阅源
PLAIN 示例 https://example.com/ 第一篇 https://example.com/a
```

限制：正文 CDATA 里若出现字面量 `<!DOCTYPE`，整份源会被拒绝。现有测试源没有这种文档。

## 全量测试（三处都改完之后）

命令：

```
E:\muse-bridge\work\TASK-044-freshfeeds\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

经 `E:\muse-bridge\work\TASK-044-freshfeeds\run_pytest.bat` 执行，cwd 为仓库。输出：

```
..........................                                               [100%]
============================== warnings summary ===============================
..\..\work\TASK-044-freshfeeds\venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\work\TASK-044-freshfeeds\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
26 passed, 1 warning in 6.52s
EXIT=0
```

没有失败项。剩下的 1 条是 StarletteDeprecationWarning。DECISIONS.md:25 写明不修。测试文件和依赖版本都没改。

`git diff --stat`：`app.py` 与 `static/index.html` 两个文件，+34 / -11。

## git status

```
git -C "E:\muse-bridge\in\TASK-044-freshfeeds" status --porcelain
```

```
 M app.py
 M static/index.html
```

