# freshfeeds 修复记录

只改了 review.md 里的 P1。P0 没有。P2 未动。

## P1-1 NAT64 本地前缀内嵌 IPv4

文件：`app.py:81-88`（原 `app.py:81-82` 把 `/96` 和 `/48` 合成一条，都取最低 32 位）。

改法：`64:ff9b::/96` 仍取最低 32 位。`64:ff9b:1::/48` 改为按 RFC 6052 前缀长度 48，用第 48–63 位和第 72–87 位拼回 IPv4，再交给原来的网段黑名单。

验证命令：

```
E:\muse-bridge\work\TASK-074-freshfeeds\venv\Scripts\python.exe -B E:\muse-bridge\work\TASK-074-freshfeeds\probe_ssrf.py
E:\muse-bridge\work\TASK-074-freshfeeds\run-pytest.bat
```

抽查输出（退出码 0）：

```
nat64/96 127.0.0.1: embedded=127.0.0.1 public=False
nat64/48 127.0.0.1 suffix public: embedded=127.0.0.1 public=False
nat64/48 169.254.169.254 suffix public: embedded=169.254.169.254 public=False
nat64/48 10.1.2.3 suffix public: embedded=10.1.2.3 public=False
nat64/48 8.8.8.8 suffix 127.0.0.1: embedded=8.8.8.8 public=True
6to4 127.0.0.1: embedded=127.0.0.1 public=False
198.18.0.1: public=True
EXC http://[64:ff9b:1:7f00:0:108:808:800]/x: BlockedUrlError: 拒绝抓取内网/保留地址：64:ff9b:1:7f00:0:108:808:800（64:ff9b:1:7f00:0:108:808:800）
```

修复前同一地址的结果是 `embedded=8.8.8.0 public=True`，并且 `ensure_fetch_allowed` 返回 ALLOW。

全量测试（退出码 0）：

```
31 passed, 1 warning in 6.61s
PYTEST_EXIT=0
```

警告仍是 Starlette 弃用 httpx，与改动无关。

## P1-2 解析失败仍改写订阅地址

文件：`app.py:668-676`（原 `app.py:662-666` 在 `parse_feed` 之前就 `UPDATE feeds.url`）。

改法：先抓发现到的地址并解析。`parse_feed` 成功之后才 `UPDATE` url。解析或再次抓取抛错时，失败分支只写 `last_error`，原订阅地址不动。发现成功且解析成功时仍改写地址。

验证命令：

```
E:\muse-bridge\work\TASK-074-freshfeeds\venv\Scripts\python.exe -B E:\muse-bridge\work\TASK-074-freshfeeds\verify_discover.py
E:\muse-bridge\work\TASK-074-freshfeeds\run-pytest.bat
```

抽查输出（退出码 0）：

```
BAD_REFRESH_EXC HTTPException 502: 抓取失败：syntax error: line 1, column 0
id=1 url=http://blog.example/home title='' entries=0 err='syntax error: line 1, column 0'
GOOD_REFRESH {'added': 1, 'total_in_feed': 1}
id=2 url=http://feeds.example/good.xml title='发现到的源' entries=1 err=''
```

修复前，同一失败路径会把 url 改成 `http://feeds.example/rss`。现在失败保留 `http://blog.example/home`，成功路径仍改写成发现到的源并入库 1 篇。

## 改动后全量测试

两条 P1 都落地之后重跑（上面 P1-2 的那次 `run-pytest.bat`，退出码 0）：

```
...............................                                          [100%]
31 passed, 1 warning in 6.79s
PYTEST_EXIT=0
```

没有失败项。警告仍是 Starlette 弃用 httpx，不计入本次改动。

未改测试、未改依赖版本、未改 LICENSE / UPSTREAM。P2 未修。

## git status --porcelain

命令：

```
git status --porcelain
```

输出：

```
 M app.py
```
