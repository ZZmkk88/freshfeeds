# freshfeeds · 清泉阅读

一个轻量、可自己部署的 RSS/Atom 阅读器——订阅信息源、定时抓取新文章、按分类整理，用已读/未读清爽地读完每天的更新。

设计学习了开源社区 RSS 阅读工具的通行思路，代码为独立实现（Python + FastAPI + SQLite，单个后端文件 + 单页前端）。

## 功能清单

- 单用户登录：Token 24 小时有效，首次登录会提示改密码（只提示、不强制）
- 订阅管理：填源地址添加（支持 RSS 2.0 / RSS 1.0 / Atom 解析）；填网站首页地址时，如果响应是 HTML 且正文前 500 字符不含订阅源，会从页面自动发现源（并改写该订阅的地址）
- 添加时立即抓取一次，拿到源标题与首批文章；重复订阅同一地址会被拦下
- 抓取：单个源手动刷新、一键刷新全部；进程内定时刷新（默认每 30 分钟一轮，可用环境变量调）
- 条件请求：带 ETag / Last-Modified，没更新的源不重复下载；文章按源内唯一标识判重，不会重复入库
- 阅读：文章按时间倒序排列，可标已读/未读、只看未读、一键全部标已读
- 分类：源可归到分类下，按分类筛选文章；删分类不删源
- 搜索：按标题与正文关键词搜
- OPML 导入/导出：和其它阅读器互换订阅清单，导入时按地址判重
- 抓取失败会在源名旁标 ⚠️ 并记录原因，不会假装成功

## 运行

需要 Python 3.10+。

Linux / macOS：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Windows (PowerShell)：

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

打开 http://127.0.0.1:8000 ，默认账号 `admin` / `admin123`，首次登录会提示改密码（只提示、不强制）。

## 测试

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

Linux/macOS 与 Windows 命令相同（Windows 在已激活 venv 的 PowerShell 里执行即可）。

## 配置（环境变量）

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | 监听地址；只放内网/公网访问时显式改，放开前先改掉默认密码 |
| `PORT` | `8000` | 监听端口 |
| `FRESHFEEDS_DB` | `data/freshfeeds.db`（相对 app.py 所在目录） | 数据库文件路径 |
| `FRESHFEEDS_REFRESH_MINUTES` | `30` | 定时刷新间隔（分钟） |
| `FRESHFEEDS_SCHEDULER` | `1` | 设为 `0` 关闭定时刷新 |

## 目录

- `app.py` — 后端（接口、抓取、解析、定时刷新都在这一个文件里）
- `static/index.html` — 前端单页
- `tests/test_app.py` — 自动化测试
- `NOTES.md` — 调研与取舍笔记
- `UPSTREAM.md` — 上游溯源与署名
- `DECISIONS.md` — 已定决策与审查结论记录
- `LICENSE` — Apache 2.0 许可证文本
- `requirements.txt` / `requirements-dev.txt` — 运行/开发依赖（版本钉死）

## 许可证

Apache License 2.0，见 `LICENSE`。
