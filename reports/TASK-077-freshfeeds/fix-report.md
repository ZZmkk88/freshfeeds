# freshfeeds 修复记录

只修了 review.md 清单里的 P1-1。P0 没有。P2 未改。

## P1-1 NAT64 前缀 64:ff9b:1::/48 内嵌 IPv4 抽错位

问题：`app.py` 原 81–82 行把 `64:ff9b::/96` 和 `64:ff9b:1::/48` 都取末 32 位。前缀长 48 时末 32 位是后缀。后缀写成公网地址时，内嵌的 127.0.0.1、169.254.169.254 会被放行。

文件：`app.py:81-87`（改后行号）。

改法：两条前缀分开。`/96` 仍取末 32 位。`/48` 按 RFC 6052，用地址第 48–63 位和第 72–87 位拼出 IPv4，再走原来的网段黑名单。

验证命令：

```
python E:\muse-bridge\work\TASK-077-freshfeeds\verify_p1.py
```

真实输出（exit 0，`FAILED 0`）：

```
OK 127.0.0.1 addr 64:ff9b:1:7f00:0:100:808:808 embedded 127.0.0.1 public False allowed False 拒绝抓取内网/保留地址：64:ff9b:1:7f00:0:100:808:808（64:ff9b:1:7f00:0:100:808:808）
OK 169.254.169.254 addr 64:ff9b:1:a9fe:a9:fe00:101:101 embedded 169.254.169.254 public False allowed False 拒绝抓取内网/保留地址：64:ff9b:1:a9fe:a9:fe00:101:101（64:ff9b:1:a9fe:a9:fe00:101:101）
OK 10.1.2.3 addr 64:ff9b:1:a01:2:300:808:808 embedded 10.1.2.3 public False allowed False 拒绝抓取内网/保留地址：64:ff9b:1:a01:2:300:808:808（64:ff9b:1:a01:2:300:808:808）
OK 192.168.1.1 addr 64:ff9b:1:c0a8:1:100:: embedded 192.168.1.1 public False allowed False 拒绝抓取内网/保留地址：64:ff9b:1:c0a8:1:100::（64:ff9b:1:c0a8:1:100::）
OK 8.8.8.8 addr 64:ff9b:1:808:8:800:: embedded 8.8.8.8 public True allowed True ['64:ff9b:1:808:8:800::']
OK 8.8.8.8 addr 64:ff9b:1:808:8:800:102:304 embedded 8.8.8.8 public True allowed True ['64:ff9b:1:808:8:800:102:304']
OK 93.184.216.34 addr 64:ff9b:1:5db8:d8:2200:909:909 embedded 93.184.216.34 public True allowed True ['64:ff9b:1:5db8:d8:2200:909:909']
well-priv 127.0.0.1 False
well-pub 8.8.8.8 True
6to4 127.0.0.1 False
fakeip True
FAILED 0
```

修前同一地址 `64:ff9b:1:7f00:0:100:808:808` 的结果是 `embedded_fn= 8.8.8.8 public= True` 且 ALLOW。修后 embedded 为 127.0.0.1 且拒绝。`198.18.0.1` 仍放行（`fakeip True`），6to4 与 `64:ff9b::/96` 的原判断没有改。

## 全量测试（修复后）

命令：

```
python -m pytest tests/ -q --tb=line
```

真实输出（exit 0）：

```
...............................                                          [100%]
============================== warnings summary ===============================
..\..\env\TASK-077-freshfeeds\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\env\TASK-077-freshfeeds\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
31 passed, 1 warning in 6.71s
```

没有失败项。警告与修复前相同，来自依赖组合，未改测试、未改依赖版本。

## git status --porcelain

命令：

```
git status --porcelain
```

输出原文：

```
 M app.py
```
