# freshfeeds 修复记录

只修 `review.md` 里的 P1。P0 没有。P2 未改。

## P1-1 过渡地址内嵌私网 IPv4

- 文件：`app.py:71-102`（新增 `_addr_blocked`、`_embedded_ipv4`，改写 `_is_public_ip`。随后 P1-2 在文件头加了 `import http.client`，这三处从 70 行移到 71 行）
- 改法：6to4（`2002::/16`）、NAT64（`64:ff9b::/96` 与 `64:ff9b:1::/48`）、Teredo（`2001::/32`，客户端 IPv4 与 `0xffffffff` 异或）、IPv4-compatible（`::/96`）先抽出内嵌 IPv4，再走原来的黑名单。`198.18.0.0/15` 和公网内嵌地址仍然放行。`::ffff:0:0/96` 仍先转成 IPv4。

验证命令：

```powershell
E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Scripts\python.exe -m pytest tests/test_app.py::test_ssrf_blocked_targets tests/test_app.py::test_ssrf_allows_public_and_fakeip_range tests/test_app.py::test_ssrf_redirect_to_internal_blocked tests/test_app.py::test_create_feed_internal_url_rejected -q -p no:cacheprovider
E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-057-freshfeeds\probe_p1_1.py
```

pytest 真实输出（退出码 0）：

```
4 passed, 2 warnings in 1.71s
```

其中一条警告是这次多加了 `-p no:cacheprovider` 导致 `cache_dir` 不被识别，与产品无关。另一条仍是 StarletteDeprecationWarning。

探针真实输出（退出码 0，`failures 0`）：

```
OK public=False want=False 2002:7f00:1::
OK public=False want=False 2002:a9fe:a9fe::
OK public=False want=False 64:ff9b::7f00:1
OK public=True want=True 64:ff9b::808:808
OK public=False want=False ::7f00:1
OK public=True want=True ::ffff:198.18.0.1
OK public=False want=False 2001:0:4136:e378:8000:63bf:80ff:fffe
OK public=True want=True 198.18.0.1
BLOCK http://[2002:7f00:1::]/ 拒绝抓取内网/保留地址：2002:7f00:1::（2002:7f00:1::）
BLOCK http://[64:ff9b::7f00:1]/ 拒绝抓取内网/保留地址：64:ff9b::7f00:1（64:ff9b::7f00:1）
BLOCK http://[::7f00:1]/ 拒绝抓取内网/保留地址：::7f00:1（::7f00:1）
ALLOW http://198.18.0.1/
ALLOW http://8.8.8.8/
```

字面地址，没有 DNS，没有抓外网页。

## P1-2 校验主机与实际连接不一致，且代理 / 二次解析绕过已放行的 IP

- 文件：`app.py:10`（`import http.client`）、`app.py:106-159`（`_host_key`、`_connect_host`、`ensure_fetch_allowed`）、`app.py:183-188`（opener）、`app.py:402-452`（`_open_pinned` 与 `fetch_url`）
- 改法：`urlparse` 的主机和 urllib 交给 `getaddrinfo` 的主机不一致，或端口解析抛 `InvalidURL`，就拒绝。抓取 opener 传入空的 `ProxyHandler({})`，默认环境代理不再登记（handler 列表里没有 ProxyHandler）。`ensure_fetch_allowed` 返回已放行的 IP；`fetch_url` 在本次 `open` 期间把目标主机的 `getaddrinfo` 钉成这些 IP。测试若把 `ensure_fetch_allowed` 换成返回 `None`，则不钉，原有用例仍走原 URL。

验证命令：

```powershell
E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-057-freshfeeds\probe_p1_2.py
```

真实输出（退出码 0）：

```
proxy-handlers ['UnknownHandler', 'HTTPHandler', 'HTTPDefaultErrorHandler', 'FTPHandler', 'FileHandler', 'DataHandler', 'HTTPSHandler', '_NoRedirectHandler', 'HTTPErrorProcessor']
ambiguous BLOCK 网址主机名含混，已拒绝抓取
userinfo BLOCK 网址主机名含混，已拒绝抓取
dns_calls_after_reject []
name http://example.com/feed ['93.184.216.34']
name http://Example.COM/feed ['93.184.216.34']
literal http://198.18.0.1/ ['198.18.0.1']
literal http://8.8.8.8/ ['8.8.8.8']
literal http://93.184.216.34/ ['93.184.216.34']
loop BLOCK 拒绝抓取内网/保留地址：127.0.0.1（127.0.0.1）
pin ok host feed.test:52280 added_dns [] has_item True
```

`http://127.0.0.1%23@8.8.8.8/feed` 与带用户名的 URL 在解析前被拒绝（`dns_calls_after_reject []`）。`example.com` 的解析函数被探针换成返回 `93.184.216.34`，没有真实 DNS。钉死探针把 `feed.test` 的解析结果换成 `127.0.0.1`，本地 HTTP 服务收到 `Host: feed.test:52280`，正文被解析；外层 `getaddrinfo` 没有被调用（`added_dns []`）。本机 `HTTP_PROXY` 仍是 `http://127.0.0.1:7890`，请求没有被送去代理端口。

## 全量测试（两项都改完之后）

```powershell
E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q -o cache_dir=E:\muse-bridge\work\TASK-057-freshfeeds\pytest-cache
```

真实输出（退出码 0）：

```
..........................                                               [100%]
============================== warnings summary ===============================
..\..\work\TASK-057-freshfeeds\.venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
26 passed, 1 warning in 6.10s
```

没有失败。剩下的 1 条警告是修前就有的 Starlette/httpx 弃用提示，`DECISIONS.md` 已决定不修，依赖版本未改。测试文件未改。

P2 六项未改。

## git status --porcelain

```
 M app.py
```
