# freshfeeds 修复记录

只改了 `review.md` 清单里的两项 P1，都在 `app.py` 的 `_embedded_ipv4`。没有 P0。P2 未动。测试文件未改。

## P1-1 SIIT 内嵌 IPv4

- 问题：`app.py:76-88`（修前）不识别 `::ffff:0:0:0/96`，`::ffff:0:127.0.0.1`、`::ffff:0:10.0.0.1`、`::ffff:0:169.254.169.254` 被放行。
- 文件：最终在 `app.py:89-91`。刚写完时在 85-87 行；P1-2 在它前面加了 4 行，行号下移。
- 改法：在 Teredo 判断之后增加 SIIT 前缀，取出末 32 位再交给现有 `_addr_blocked`。公网内嵌地址和 198.18/15 仍放行。

验证：

```
E:\muse-bridge\work\TASK-070-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short -o cache_dir=E:\muse-bridge\work\TASK-070-freshfeeds\pytest-cache
```

```
30 passed, 1 warning in 6.63s
```

警告仍是 StarletteDeprecationWarning（httpx / starlette.testclient），与修前相同。

```
E:\muse-bridge\work\TASK-070-freshfeeds\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-070-freshfeeds\check_p1.py
```

```
BLOCK http://[::ffff:0:127.0.0.1]/ -> 拒绝抓取内网/保留地址：::ffff:0:127.0.0.1（::ffff:0:7f00:1）
BLOCK http://[::ffff:0:10.0.0.1]/ -> 拒绝抓取内网/保留地址：::ffff:0:10.0.0.1（::ffff:0:a00:1）
BLOCK http://[::ffff:0:169.254.169.254]/ -> 拒绝抓取内网/保留地址：::ffff:0:169.254.169.254（::ffff:0:a9fe:a9fe）
ALLOW http://[::ffff:0:8.8.8.8]/ -> ['::ffff:0:808:808']
ALLOW http://[::ffff:0:198.18.0.1]/ -> ['::ffff:0:c612:1']
BLOCK http://[::ffff:127.0.0.1]/ -> 拒绝抓取内网/保留地址：::ffff:127.0.0.1（::ffff:7f00:1）
ALLOW http://198.18.0.1/ -> ['198.18.0.1']
ALLOW http://93.184.216.34/ -> ['93.184.216.34']
```

此时 `http://[64:ff9b:1:7f00:0:100:808:808]/` 仍是 ALLOW，留给 P1-2。

## P1-2 NAT64 /48 取错比特

- 问题：修前 `app.py:81-82` 把 `64:ff9b:1::/48` 的最后 32 位当成内嵌 IPv4。RFC 6052 里这 32 位是后缀。`64:ff9b:1:7f00:0:100:808:808`（内嵌 127.0.0.1，后缀 8.8.8.8）修前 ALLOW。
- 文件：`app.py:78-86`。
- 改法：`/96` 仍取末 4 字节。`/48` 改为 `raw[6:8] + raw[9:11]`。6to4、Teredo、SIIT 分支没改判断。

验证：

```
E:\muse-bridge\work\TASK-070-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short -o cache_dir=E:\muse-bridge\work\TASK-070-freshfeeds\pytest-cache
```

```
30 passed, 1 warning in 6.89s
```

警告仍是同一条 StarletteDeprecationWarning。没有失败项。

```
E:\muse-bridge\work\TASK-070-freshfeeds\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-070-freshfeeds\check_p1.py
```

```
layout 0064:ff9b:0001:0808:0008:0800:7f00:0001 rfc6052 8.8.8.8 tail 127.0.0.1 in48 True
BLOCK http://[64:ff9b:1:7f00:0:100:808:808]/ -> 拒绝抓取内网/保留地址：64:ff9b:1:7f00:0:100:808:808（64:ff9b:1:7f00:0:100:808:808）
ALLOW http://[64:ff9b:1:808:8:800:7f00:1]/ -> ['64:ff9b:1:808:8:800:7f00:1']
BLOCK http://[64:ff9b::7f00:1]/ -> 拒绝抓取内网/保留地址：64:ff9b::7f00:1（64:ff9b::7f00:1）
ALLOW http://[64:ff9b::808:808]/ -> ['64:ff9b::808:808']
BLOCK http://[::ffff:0:127.0.0.1]/
BLOCK http://[::ffff:0:169.254.169.254]/
ALLOW http://[::ffff:0:8.8.8.8]/
ALLOW http://[::ffff:0:198.18.0.1]/
ALLOW http://198.18.0.1/
ALLOW http://93.184.216.34/
```

内嵌私网的 `/48` 改为拒绝；内嵌 8.8.8.8、后缀却是 127.0.0.1 的地址改为放行（修前会因为后缀被误拦）。`/96`、SIIT、字面量 198.18.0.1 与 93.184.216.34 保持原口径。

## 全量测试（两项都改完之后）

上面 P1-2 的那次就是最后一次全量测试，此后没有再改仓库源码。

```
30 passed, 1 warning in 6.89s
```

没有失败项。仍在的警告是依赖组合里的 StarletteDeprecationWarning，不是断言失败。`DECISIONS.md` 已写明不改依赖版本号，本次也没改。

## git status --porcelain

```
git -C E:\muse-bridge\in\TASK-070-freshfeeds status --porcelain
```

```
 M app.py
```
