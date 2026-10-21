# freshfeeds 验收审查

结论：依赖与测试能跑通（pytest 26 passed），服务在 `127.0.0.1:8000` 首页返回 200，没有健康检查路由。P0 没有。P1 有 2 项，都在 `app.py` 的抓取校验。许可证种类是 Apache-2.0，版权人没有闭合；未改 `LICENSE` / `UPSTREAM.md`。下面按原文件行号记录，修完前的代码。

## 本地跑通记录

解释器：本机默认 `py` 指向损坏的 `E:\python.exe`（`Unable to create process using 'E:\python.exe ...'`，退出码 1）。改用 `py -3.11`，版本 `3.11.9`，满足 README 的 Python 3.10+。这是本机环境问题，不是仓库缺陷。venv 放在 `E:\muse-bridge\work\TASK-057-freshfeeds\.venv`，没有写进仓库。

安装（退出码 0）：

```powershell
py -3.11 -m venv E:\muse-bridge\work\TASK-057-freshfeeds\.venv
E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-057-freshfeeds\requirements-dev.txt
```

装上 `fastapi==0.156.7`、`uvicorn==0.54.0`、`python-multipart==0.0.32`、`httpx==0.28.1`、`pytest==9.1.1`。`requirements-dev.txt` 用 `-r requirements.txt` 带上运行依赖。

全量测试（cwd = 仓库根，退出码 0）：

```powershell
E:\muse-bridge\work\TASK-057-freshfeeds\.venv\Scripts\python.exe -m pytest tests/ -q -o cache_dir=E:\muse-bridge\work\TASK-057-freshfeeds\pytest-cache
```

```
26 passed, 1 warning in 6.51s
```

警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 来自 `fastapi/testclient.py:1`。与 `DECISIONS.md:25` 已决定不修的 P2-6 是同一条。

服务：`FRESHFEEDS_DB` 指到工作目录，`FRESHFEEDS_SCHEDULER=0`，`PORT=8000`。

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

进程号 35540。用标准库 urllib 探测（未使用 curl/wget）：

| 请求 | 结果 |
| --- | --- |
| `GET /` | 200，`text/html; charset=utf-8`，正文含 `<title>freshfeeds · 清泉阅读</title>` |
| `POST /api/login` `admin` / `admin123` | 200，`must_change_password` 为 true |
| `GET /api/feeds` 无令牌 | 401，`未登录` |
| `GET /api/me` | 200，`username=admin` |
| `POST /api/entries/mark-all-read` 空 JSON | 200，`{"ok":true}` |
| `GET /health`、`GET /api/health` | 404 `Not Found` |
| `GET /docs`、`/redoc`、`/openapi.json` | 404（`app.py:136-138` 显式关闭，与 `DECISIONS.md:33` 一致） |

README 没有承诺 `/health`。首页 200 即进程存活。探测后已结束该进程（`terminated by signal killed`）。没有外网抓取页面；依赖安装走了 pip。

## README 与实际不符处

1. `README.md:9` 写「可跳过」。`static/index.html:127-132` 的改密对话框只有「保存」，没有跳过按钮。代码没有拦截 `cancel`，Esc 能关掉（与 `DECISIONS.md:8-10` 一致）。文案比界面多承诺了一个可见的跳过动作。`README.md:42` 只写「只提示、不强制」，这句和 `app.py:233-246`（`current_user` 不看 `must_change`）一致。
2. `README.md:10` 写「填网站首页地址时会自动发现源」。`app.py:535-539` 只在 Content-Type 含 `html`，且正文前 500 字符不含 `<feed` / `<rss` 时才发现，并会改写该订阅的 `url`。README 没写这两个前提。
3. `README.md:63-69` 的目录清单没有仓库里实际存在的 `DECISIONS.md`、`LICENSE`、`requirements.txt`、`requirements-dev.txt`。
4. `README.md:68` 把 `NOTES.md` 列为项目文档。`NOTES.md:22` 写「默认 admin/admin123 首登强制改密」。代码不强制：`app.py:200-205` 只把 `must_change` 设为 1，没有任何接口因此返回 403。`README.md:9` 本身写的是「不强制」。不符的是 NOTES，不是 README 正文那句。

其余抽查过的 README 说法与代码一致：Token 24 小时（`app.py:33`）、默认 `admin` / `admin123`（`app.py:204`）、监听 `127.0.0.1:8000`（`app.py:923-927`）、`FRESHFEEDS_DB` 相对 `app.py` 目录（`app.py:30`）、刷新间隔 30 分钟且 `FRESHFEEDS_SCHEDULER=0` 关闭（`app.py:31-32`）、RSS 2.0 / RSS 1.0 / Atom（`app.py:423-509`）、删分类不删源（`app.py:631-637`）、OPML 按地址判重（`app.py:886-887`）。

## 许可证与署名核查

- `README.md:73` 写 Apache License 2.0。`LICENSE` 是 Apache-2.0 标准文本（第 1–9 条 + 附录）。种类一致。
- `LICENSE:190` 仍是附录模板 `Copyright [yyyy] [name of copyright owner]`。这是许可证文件里的填写说明，不是已经填上的版权人。
- `UPSTREAM.md:3-6` 写上游 `https://github.com/miniflux/v2`，commit `bdd8087d9cf7a20ca7e800948389e8a7e86445da`，许可证 Apache-2.0，attribution 为 `Copyright The Miniflux Authors. All rights reserved.`。`UPSTREAM.md:12` 同时写「未复制上游源码」。
- 仓库源码（`app.py`、`static/index.html`、`tests/test_app.py`）没有这行版权声明，也没有 `NOTICE`。
- `app.py:34` 的 User-Agent 指向 `https://github.com/ZZmkk88/freshfeeds`，和 UPSTREAM 的 miniflux 不是同一个仓库。
- 未访问 GitHub。`source_commit` 是否仍是 miniflux 默认分支 HEAD、`main.go` 的 SPDX 行是否与 UPSTREAM 逐字相同，均未核实。不能把「未核实」当成事实错误。
- 结论：许可证种类自洽；版权主体不闭合（附录未填版权人、源码无版权头、UPSTREAM 把上游版权行当作本仓 attribution，又声明没有复制源码）。不修改 `LICENSE` 与 `UPSTREAM.md`。

## 分级修复清单

### P0

无。测试 26 项通过，`python app.py` 能在 `127.0.0.1:8000` 完成启动，首页 200。

### P1

1. **过渡地址里的私网 IPv4 被放行。** `app.py:70-77` 的 `_is_public_ip` 只对照 `app.py:59-67` 的网段。探针：`http://[2002:7f00:1::]/`（6to4 的 127.0.0.1）、`http://[2002:a9fe:a9fe::]/`（6to4 的 169.254.169.254）、`http://[64:ff9b::7f00:1]/` 与 `http://[64:ff9b:1::7f00:1]/`（NAT64）、`http://[::7f00:1]/`（IPv4-compatible）、Teredo `2001:0:4136:e378:8000:63bf:80ff:fffe` 全部 ALLOW。`::ffff:127.0.0.1` 已被映射逻辑拦住。修法：解出 6to4 / NAT64（含 `64:ff9b:1::/48`）/ Teredo / IPv4-compatible 的内嵌 IPv4，命中现有黑名单就拒绝；`198.18.0.0/15` 仍放行（`DECISIONS.md:16`，探针 `http://198.18.0.1/` 为 ALLOW，保持）。
2. **校验的主机不是 urllib 实际解析的主机，连接也没有钉在已放行的地址上。** `app.py:84-95` 用 `urlparse().hostname` 做决定；`app.py:119` 的 `build_opener` 使用默认代理处理；`app.py:325-332` 通过后仍用原始 URL 再解析一次。证据：`http://127.0.0.1%23@8.8.8.8/feed` 被 ALLOW（hostname=`8.8.8.8`），关掉代理后 urllib 调用的是 `getaddrinfo("127.0.0.1#@8.8.8.8", 9)`。本机这次解析失败（`gaierror 11003`），没有连上 127.0.0.1，但放行对象已经错了。另外本机 `HTTP_PROXY=http://127.0.0.1:7890`，默认 opener 会把外网请求交给代理，代理自己再解析，进程内的 IP 判断约束不到最终连接。修法：主机名对不上就拒绝；抓取 opener 使用空的 `ProxyHandler`；本次连接把已放行的 IP 钉进 `getaddrinfo`。

### P2

1. `README.md:9` 与 `static/index.html:127-132`：对话框加一个不改密码也能关闭的按钮，或改掉「可跳过」。不强制改密是 `DECISIONS.md:7` 的已定决策，不能改成 403。
2. `README.md:10` 与 `app.py:535`：README 补上自动发现的 Content-Type / 前 500 字符条件。
3. `README.md:63-69`：目录清单补上 `DECISIONS.md`、`LICENSE`、`requirements.txt`、`requirements-dev.txt`。
4. `NOTES.md:22`：把「首登强制改密」改成「只提示、不强制」，与 `README.md:9` 和 `app.py:233-246` 对齐。
5. `app.py:481-482` 与 `app.py:567-570`：channel `site_url` 不经过 `app.py:414-420` 的 `_clean_url`。探针里 `javascript:alert(1)` 会进 `site_url`，并经 `app.py:814` 写进 OPML `htmlUrl`。本应用前端没有把 `site_url` 放进 `href`。修法：入库前同样只留 http(s)。
6. `requirements-dev.txt:2` 的 httpx 与 Starlette TestClient 弃用警告。不修。`DECISIONS.md:25` 已写明，且不许改依赖版本号。

不修：把 `198.18.0.0/15` 划进黑名单（`DECISIONS.md:16`）；把首次登录改回强制改密（`DECISIONS.md:7-10`）。
