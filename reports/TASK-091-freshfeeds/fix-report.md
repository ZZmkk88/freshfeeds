# freshfeeds 修复记录

结论：`review.md` 的分级清单里 P0 为 0 条，P1 为 0 条。没有修改仓库源码。

## 问题编号

无 P0 / P1 条目。P2 共 13 条，按任务只修 P0 和 P1，所以一条都没改。

不修的直接原因：

- P0：`python -m pytest tests/ -q` 的等价运行结果是 `31 passed`。服务在 `127.0.0.1:18765` 上 `GET /` 返回 200，登录返回 200。8000 的 `Errno 10048` 是本机 PID 35756（weblens）占用，不是本仓库绑定代码错误。
- 曾考虑过的安全项不构成待修 P1：内网与内嵌私网地址在本地探针中被拒绝；`198.18.0.0/15` 放行被 `tests/test_app.py:258` 锁定，且 `DECISIONS.md:16` 写明是假 IP DNS 的取舍；强制改密被 `DECISIONS.md:7-10` 永久排除，改了会让现有测试失败，而测试不许改。
- `fec0::/10` 等网段缺口放在 P2，`DECISIONS.md:32` 写明维持现状。

没有「改了哪个文件」。下面没有补丁行号。

## 全量测试

审查结束后重跑。命令：

```
python E:\muse-bridge\work\TASK-091-freshfeeds\run_pytest.py
```

该脚本在仓库根目录执行 `pytest tests/ -q -p no:cacheprovider`，TEMP 指向 `E:\muse-bridge\work\TASK-091-freshfeeds`。

输出：

```
...............................                                          [100%]
============================== warnings summary ===============================
..\..\env\TASK-091-freshfeeds\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\env\TASK-091-freshfeeds\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
31 passed, 1 warning in 6.92s
```

退出码 0。没有失败项。警告与修代码无关，来自已安装的 fastapi/starlette，按 `DECISIONS.md:25` 与「不许改依赖版本号」保留。

## git status

```
git status --porcelain
```

无输出，退出码 0。

仓库里没有待提交改动。空输出是因为本轮没有改仓库文件，不是改动丢失。`review.md`、`run.md`、`fix-report.md` 写在 `E:\muse-bridge\out\TASK-091-freshfeeds\`，不在仓库工作区。
