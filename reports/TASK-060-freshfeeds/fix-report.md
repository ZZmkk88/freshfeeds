# freshfeeds 修复记录

只改了 review.md 清单里的 P1，共 3 项。没有 P0。P2 未改。测试文件、依赖版本、`LICENSE`、`UPSTREAM.md` 未改。

## P1-1 抓取连接钉在已校验地址上，并忽略环境代理

- 问题编号：P1-1
- 文件：`app.py:111`（`ensure_fetch_allowed` 改为返回已通过的地址）、`app.py:131`（`_open_pinned`）、`app.py:187-191`（opener 使用空的 `ProxyHandler`，并加 `_pin_lock`）、`app.py:404-411`（`fetch_url` 把这些地址交给 `_open_pinned`）。
- 改法：校验函数返回地址列表。单次 `open` 期间 `socket.getaddrinfo` 只返回这些地址。opener 传入 `ProxyHandler({})`，默认的环境代理处理器不再装上，本机 `HTTP_PROXY=http://127.0.0.1:7890` 不参与抓取。测试桩若让校验函数返回 `None`，则不钉死，原有用例仍直接连接。
- 验证命令：`python E:\muse-bridge\work\TASK-060-freshfeeds\verify_p1_1.py`
- 真实输出：

```
fetch URLError <urlopen error pinned-stop>
connect_targets [('93.184.216.34', 9)]
unpinned URLError <urlopen error pinned-stop>
unpinned_targets [('127.0.0.1', 9)]
```

校验结果是公网 `93.184.216.34` 时，`connect` 的目标就是这个地址，不再是二次解析得到的 `127.0.0.1`。环境代理开着时也没有连到 `127.0.0.1:7890`。桩返回 `None` 时仍直接连 URL 里的 `127.0.0.1`。

- 对应测试：`python -m pytest tests/test_app.py -q -o cache_dir=E:\muse-bridge\work\TASK-060-freshfeeds\pytest_cache -k "ssrf or real_http or create_feed or add_feed"`
- 真实输出：`6 passed, 20 deselected, 1 warning in 1.96s`

## P1-2 IPv6 内嵌 IPv4 走同一份网段清单

- 问题编号：P1-2
- 文件：`app.py:71-107`（`_embedded_ipv4s`、`_blocked_ipv4`、`_is_public_ip`）。
- 改法：6to4（`2002::/16`）、NAT64（`64:ff9b::/96`）、Teredo（`2001::/32` 的服务器地址和异或后的客户端地址）、`::/96` 兼容地址先拆出 IPv4，再查原来的拦截清单。`ipv4_mapped` 仍走这条路径。`198.18.0.1` 和它的 6to4 形式 `2002:c612:1::` 继续放行。
- 验证命令：`python E:\muse-bridge\work\TASK-060-freshfeeds\verify_p1_2.py`
- 真实输出（节选，脚本以 `failed 0` 结束，exit 0）：

```
OK 2002:7f00:1:: public=False expect=False
OK 2002:a9fe:a9fe:: public=False expect=False
OK 2002:c612:1:: public=True expect=True
OK 64:ff9b::7f00:1 public=False expect=False
OK 64:ff9b::a9fe:a9fe public=False expect=False
OK ::7f00:1 public=False expect=False
OK 198.18.0.1 public=True expect=True
OK http://[2002:7f00:1::]/ blocked=True 拒绝抓取内网/保留地址：2002:7f00:1::（2002:7f00:1::）
OK http://[2002:a9fe:a9fe::]/ blocked=True 拒绝抓取内网/保留地址：2002:a9fe:a9fe::（2002:a9fe:a9fe::）
OK http://[2002:c612:1::]/ blocked=False ALLOW
failed 0
```

- 对应测试：`python -m pytest tests/test_app.py -q -o cache_dir=E:\muse-bridge\work\TASK-060-freshfeeds\pytest_cache -k "ssrf"`
- 真实输出：`3 passed, 23 deselected, 1 warning in 1.10s`

## P1-3 密码长度上限

- 问题编号：P1-3
- 文件：`app.py:34`（`MAX_PASSWORD_CHARS = 128`）、`app.py:323-324`（登录）、`app.py:358-362`（改密）。
- 改法：用户名或密码超过 128 个字符时，登录在调用 `hash_pw` 之前返回 401。改密的旧密码或新密码超过 128 个字符时返回 400「密码过长」，仍保留「至少 6 位」的检查。
- 验证命令：`python E:\muse-bridge\work\TASK-060-freshfeeds\verify_p1_3.py`
- 真实输出：

```
normal 200 True
long_login 401 {'detail': '用户名或密码不对'} elapsed=0.002s
short_new 400 {'detail': '新密码至少 6 位'}
long_old 400 {'detail': '密码过长'}
long_new 400 {'detail': '密码过长'}
still_old 200
```

129 字符的登录在 0.002 秒内被拒绝，原密码 `admin123` 仍能登录。

- 对应测试：`python -m pytest tests/test_app.py -q -o cache_dir=E:\muse-bridge\work\TASK-060-freshfeeds\pytest_cache -k "login or password"`
- 真实输出：`3 passed, 23 deselected, 1 warning in 1.61s`

## 全量测试

命令：`python -m pytest tests/ -q -o cache_dir=E:\muse-bridge\work\TASK-060-freshfeeds\pytest_cache`

```
..........................                                               [100%]
============================== warnings summary ===============================
..\..\env\TASK-060-freshfeeds\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\env\TASK-060-freshfeeds\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
26 passed, 1 warning in 4.93s
```

26 项全部通过。警告与修之前相同，DECISIONS.md:25 标明不修。没有失败项。

## git status

命令：`git status --porcelain`

```
 M app.py
```
