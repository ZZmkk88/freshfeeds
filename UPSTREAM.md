# 上游溯源

- source_url: https://github.com/miniflux/v2
- source_commit: bdd8087d9cf7a20ca7e800948389e8a7e86445da
- license: Apache-2.0
- attribution: Copyright The Miniflux Authors. All rights reserved.

说明（核查记录，2026-10-21 通过 GitHub 接口实查）：

- 上游默认分支 HEAD 即上面的 source_commit。
- 上游 LICENSE 是 Apache License 2.0 标准全文，文末附录未填具体的版权行，仓库内也没有 NOTICE 文件；源码文件头使用 SPDX 标识，上面的 attribution 即逐字复制自主文件 `main.go` 文件头的 `SPDX-FileCopyrightText` 行。
- 本项目只学习其公开的设计思路（订阅/分类/文章模型、判重、条件请求、定时刷新、OPML 交换），代码为独立实现，未复制上游源码。
