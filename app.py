"""freshfeeds - 轻量 RSS/Atom 阅读器（单文件后端）

设计学习了开源社区 RSS 阅读工具的通行思路：订阅源 + 分类 + 文章三级模型，
文章按源内唯一标识判重，抓取时带 ETag / Last-Modified 条件请求，
进程内定时刷新。代码为独立实现：FastAPI + SQLite + 标准库 XML 解析。
"""
import hashlib
import hmac
import html
import os
import re
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("FRESHFEEDS_DB", os.path.join(BASE_DIR, "data", "freshfeeds.db"))
REFRESH_MINUTES = int(os.environ.get("FRESHFEEDS_REFRESH_MINUTES", "30"))
SCHEDULER_ON = os.environ.get("FRESHFEEDS_SCHEDULER", "1") != "0"
TOKEN_TTL_HOURS = 24
USER_AGENT = "freshfeeds/1.0 (+https://github.com/ZZmkk88/freshfeeds)"
FETCH_TIMEOUT = 15

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(_app):
    init_db()
    if SCHEDULER_ON:
        threading.Thread(target=_scheduler_loop, daemon=True).start()
    yield


app = FastAPI(title="freshfeeds", lifespan=lifespan)

# ---------------------------------------------------------------- 数据库


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            pw_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            must_change INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS tokens (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS feeds (
            id INTEGER PRIMARY KEY,
            url TEXT UNIQUE NOT NULL,
            site_url TEXT DEFAULT '',
            title TEXT DEFAULT '',
            category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
            etag TEXT DEFAULT '',
            last_modified TEXT DEFAULT '',
            last_checked_at TEXT DEFAULT '',
            last_error TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY,
            feed_id INTEGER NOT NULL REFERENCES feeds(id) ON DELETE CASCADE,
            guid TEXT NOT NULL,
            title TEXT DEFAULT '',
            url TEXT DEFAULT '',
            author TEXT DEFAULT '',
            content TEXT DEFAULT '',
            published_at TEXT DEFAULT '',
            fetched_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'unread',
            UNIQUE(feed_id, guid)
        );
        """
    )
    row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
    if row["c"] == 0:
        salt = secrets.token_hex(16)
        conn.execute(
            "INSERT INTO users (username, pw_hash, salt, must_change) VALUES (?,?,?,1)",
            ("admin", hash_pw("admin123", salt), salt),
        )
    conn.commit()
    conn.close()


def hash_pw(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), 200_000
    ).hex()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- 登录鉴权


class LoginIn(BaseModel):
    username: str
    password: str


class ChangePwIn(BaseModel):
    old_password: str
    new_password: str


def current_user(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "未登录")
    th = hashlib.sha256(authorization[7:].encode()).hexdigest()
    conn = db()
    row = conn.execute(
        "SELECT u.* FROM tokens t JOIN users u ON u.id = t.user_id "
        "WHERE t.token_hash = ? AND t.expires_at > ?",
        (th, now_iso()),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(401, "登录已过期，请重新登录")
    return row


@app.post("/api/login")
def login(body: LoginIn):
    conn = db()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (body.username,)
    ).fetchone()
    if not row or not hmac.compare_digest(
        row["pw_hash"], hash_pw(body.password, row["salt"])
    ):
        conn.close()
        raise HTTPException(401, "用户名或密码不对")
    token = secrets.token_urlsafe(32)
    th = hashlib.sha256(token.encode()).hexdigest()
    exp = (datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)).isoformat(
        timespec="seconds"
    )
    conn.execute(
        "INSERT INTO tokens (token_hash, user_id, expires_at) VALUES (?,?,?)",
        (th, row["id"], exp),
    )
    conn.commit()
    conn.close()
    return {"token": token, "must_change_password": bool(row["must_change"])}


@app.post("/api/change-password")
def change_password(body: ChangePwIn, user=Depends(current_user)):
    if len(body.new_password) < 6:
        raise HTTPException(400, "新密码至少 6 位")
    conn = db()
    if not hmac.compare_digest(
        user["pw_hash"], hash_pw(body.old_password, user["salt"])
    ):
        conn.close()
        raise HTTPException(400, "旧密码不对")
    salt = secrets.token_hex(16)
    conn.execute(
        "UPDATE users SET pw_hash = ?, salt = ?, must_change = 0 WHERE id = ?",
        (hash_pw(body.new_password, salt), salt, user["id"]),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/me")
def me(user=Depends(current_user)):
    return {"username": user["username"], "must_change_password": bool(user["must_change"])}


# ---------------------------------------------------------------- 抓取与解析

ATOM = "{http://www.w3.org/2005/Atom}"
DC = "{http://purl.org/dc/elements/1.1/}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"
RDF_ROOT = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF"


def fetch_url(url: str, etag: str = "", last_modified: str = ""):
    """返回 (status, text, etag, last_modified)。status: ok / not_modified。"""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    if etag:
        req.add_header("If-None-Match", etag)
    if last_modified:
        req.add_header("If-Modified-Since", last_modified)
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            text = raw.decode(charset, errors="replace")
            return (
                "ok",
                text,
                resp.headers.get("ETag", "") or "",
                resp.headers.get("Last-Modified", "") or "",
                resp.headers.get_content_type() or "",
            )
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return ("not_modified", "", etag, last_modified, "")
        raise


def discover_feed_url(page_text: str, base_url: str) -> str:
    """页面 HTML 里找 RSS/Atom 的 link alternate（订阅网站首页时用）。"""
    m = re.search(
        r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]*>',
        page_text,
        re.I,
    )
    if not m:
        m = re.search(
            r'<link[^>]+rel=["\']alternate["\'][^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]*>',
            page_text,
            re.I,
        )
    if not m:
        return ""
    href = re.search(r'href=["\']([^"\']+)["\']', m.group(0), re.I)
    if not href:
        return ""
    from urllib.parse import urljoin

    return urljoin(base_url, href.group(1))


def _text(el, *paths):
    for p in paths:
        node = el.find(p)
        if node is not None and node.text and node.text.strip():
            return node.text.strip()
    return ""


def _parse_date(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    try:
        dt = parsedate_to_datetime(value)
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        pass
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
    except ValueError:
        return ""


def _strip_tags(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def parse_feed(xml_text: str):
    """解析 RSS 2.0 / RSS 1.0(RDF) / Atom，返回 (title, site_url, entries)。"""
    root = ET.fromstring(xml_text)
    entries = []

    def add(guid, title, url, author, content, published):
        guid = (guid or "").strip()
        if not guid:
            guid = url or hashlib.sha256((title + content).encode()).hexdigest()
        entries.append(
            {
                "guid": guid[:500],
                "title": _strip_tags(title)[:300] or "(无标题)",
                "url": url or "",
                "author": author or "",
                "content": _strip_tags(content)[:2000],
                "published_at": _parse_date(published),
            }
        )

    if root.tag == ATOM + "feed":  # Atom
        title = _text(root, ATOM + "title")
        site_url = ""
        for link in root.findall(ATOM + "link"):
            if link.get("rel") in (None, "alternate"):
                site_url = link.get("href", "")
                break
        for e in root.findall(ATOM + "entry"):
            url = ""
            for link in e.findall(ATOM + "link"):
                if link.get("rel") in (None, "alternate"):
                    url = link.get("href", "")
                    break
            author_el = e.find(ATOM + "author/" + ATOM + "name")
            add(
                _text(e, ATOM + "id"),
                _text(e, ATOM + "title"),
                url,
                author_el.text.strip() if author_el is not None and author_el.text else "",
                _text(e, ATOM + "content", ATOM + "summary"),
                _text(e, ATOM + "published", ATOM + "updated"),
            )
        return title, site_url, entries

    # RSS 2.0: rss/channel/item；RSS 1.0: rdf:RDF/item
    channel = root.find("channel") if root.tag == "rss" else root
    if channel is None:
        channel = root
    title = _text(channel, "title")
    site_url = _text(channel, "link")
    items = channel.findall("item")
    if not items and root.tag.endswith("RDF"):
        items = root.findall("{http://purl.org/rss/1.0/}item")
        ns = "{http://purl.org/rss/1.0/}"
        for it in items:
            add(
                it.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about", ""),
                _text(it, ns + "title"),
                _text(it, ns + "link"),
                _text(it, DC + "creator"),
                _text(it, ns + "description"),
                _text(it, DC + "date"),
            )
        return title, site_url, entries
    for it in items:
        add(
            _text(it, "guid"),
            _text(it, "title"),
            _text(it, "link"),
            _text(it, "author", DC + "creator"),
            _text(it, CONTENT + "encoded", "description"),
            _text(it, "pubDate", DC + "date"),
        )
    return title, site_url, entries


_refresh_lock = threading.Lock()


def refresh_feed(feed_id: int) -> dict:
    """抓取并入库一个源，返回统计。出错时记录 last_error 并抛出。"""
    with _refresh_lock:
        conn = db()
        feed = conn.execute("SELECT * FROM feeds WHERE id = ?", (feed_id,)).fetchone()
        if not feed:
            conn.close()
            raise HTTPException(404, "订阅不存在")
        try:
            status, text, etag, lm, ctype = fetch_url(
                feed["url"], feed["etag"], feed["last_modified"]
            )
            if status == "not_modified":
                conn.execute(
                    "UPDATE feeds SET last_checked_at = ?, last_error = '' WHERE id = ?",
                    (now_iso(), feed_id),
                )
                conn.commit()
                conn.close()
                return {"added": 0, "not_modified": True}
            if "html" in ctype and "<feed" not in text[:500].lower() and "<rss" not in text[:500].lower():
                found = discover_feed_url(text, feed["url"])
                if found and found != feed["url"]:
                    status, text, etag, lm, ctype = fetch_url(found)
                    conn.execute("UPDATE feeds SET url = ? WHERE id = ?", (found, feed_id))
            title, site_url, entries = parse_feed(text)
        except Exception as e:  # 网络/解析错误都记下来，不假装成功
            conn.execute(
                "UPDATE feeds SET last_checked_at = ?, last_error = ? WHERE id = ?",
                (now_iso(), str(e)[:300], feed_id),
            )
            conn.commit()
            conn.close()
            raise HTTPException(502, f"抓取失败：{e}")
        added = 0
        for en in entries:
            cur = conn.execute(
                "INSERT OR IGNORE INTO entries "
                "(feed_id, guid, title, url, author, content, published_at, fetched_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    feed_id,
                    en["guid"],
                    en["title"],
                    en["url"],
                    en["author"],
                    en["content"],
                    en["published_at"],
                    now_iso(),
                ),
            )
            added += cur.rowcount
        conn.execute(
            "UPDATE feeds SET title = ?, site_url = ?, etag = ?, last_modified = ?, "
            "last_checked_at = ?, last_error = '' WHERE id = ?",
            (title or feed["title"], site_url or feed["site_url"], etag, lm, now_iso(), feed_id),
        )
        conn.commit()
        conn.close()
        return {"added": added, "total_in_feed": len(entries)}


def refresh_all() -> dict:
    conn = db()
    ids = [r["id"] for r in conn.execute("SELECT id FROM feeds").fetchall()]
    conn.close()
    total_added, failed = 0, 0
    for fid in ids:
        try:
            total_added += refresh_feed(fid).get("added", 0)
        except HTTPException:
            failed += 1
    return {"feeds": len(ids), "added": total_added, "failed": failed}


# ---------------------------------------------------------------- 分类与订阅


class CategoryIn(BaseModel):
    name: str


class FeedIn(BaseModel):
    url: str
    category_id: int | None = None
    category_name: str = ""


@app.get("/api/categories")
def list_categories(user=Depends(current_user)):
    conn = db()
    rows = conn.execute(
        "SELECT c.*, (SELECT COUNT(*) FROM feeds f WHERE f.category_id = c.id) AS feed_count "
        "FROM categories c ORDER BY c.name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/categories")
def create_category(body: CategoryIn, user=Depends(current_user)):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "分类名不能为空")
    conn = db()
    try:
        cur = conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        cid = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(400, "分类已存在")
    conn.close()
    return {"id": cid, "name": name}


@app.delete("/api/categories/{cid}")
def delete_category(cid: int, user=Depends(current_user)):
    conn = db()
    conn.execute("UPDATE feeds SET category_id = NULL WHERE category_id = ?", (cid,))
    conn.execute("DELETE FROM categories WHERE id = ?", (cid,))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/feeds")
def list_feeds(user=Depends(current_user)):
    conn = db()
    rows = conn.execute(
        "SELECT f.*, c.name AS category_name, "
        "(SELECT COUNT(*) FROM entries e WHERE e.feed_id = f.id AND e.status = 'unread') AS unread "
        "FROM feeds f LEFT JOIN categories c ON c.id = f.category_id ORDER BY f.title, f.id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/feeds")
def create_feed(body: FeedIn, user=Depends(current_user)):
    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "请填 http(s) 开头的源地址")
    conn = db()
    cid = body.category_id
    if body.category_name.strip():
        conn.execute(
            "INSERT OR IGNORE INTO categories (name) VALUES (?)",
            (body.category_name.strip(),),
        )
        cid = conn.execute(
            "SELECT id FROM categories WHERE name = ?", (body.category_name.strip(),)
        ).fetchone()["id"]
    try:
        cur = conn.execute(
            "INSERT INTO feeds (url, category_id, created_at) VALUES (?,?,?)",
            (url, cid, now_iso()),
        )
        conn.commit()
        fid = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(400, "这个源已经订阅过了")
    conn.close()
    try:
        stats = refresh_feed(fid)
    except HTTPException as e:
        return {"id": fid, "warning": e.detail, "added": 0}
    return {"id": fid, "added": stats.get("added", 0)}


@app.delete("/api/feeds/{fid}")
def delete_feed(fid: int, user=Depends(current_user)):
    conn = db()
    conn.execute("DELETE FROM entries WHERE feed_id = ?", (fid,))
    conn.execute("DELETE FROM feeds WHERE id = ?", (fid,))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.post("/api/feeds/{fid}/refresh")
def refresh_one(fid: int, user=Depends(current_user)):
    return refresh_feed(fid)


@app.post("/api/feeds/refresh-all")
def refresh_everything(user=Depends(current_user)):
    return refresh_all()


# ---------------------------------------------------------------- 文章


@app.get("/api/entries")
def list_entries(
    status: str = "all",
    feed_id: int = 0,
    category_id: int = 0,
    q: str = "",
    limit: int = 50,
    offset: int = 0,
    user=Depends(current_user),
):
    sql = (
        "SELECT e.*, f.title AS feed_title FROM entries e "
        "JOIN feeds f ON f.id = e.feed_id WHERE 1=1"
    )
    args = []
    if status in ("unread", "read"):
        sql += " AND e.status = ?"
        args.append(status)
    if feed_id:
        sql += " AND e.feed_id = ?"
        args.append(feed_id)
    if category_id:
        sql += " AND f.category_id = ?"
        args.append(category_id)
    if q.strip():
        sql += " AND (e.title LIKE ? OR e.content LIKE ?)"
        args += [f"%{q.strip()}%", f"%{q.strip()}%"]
    sql += " ORDER BY COALESCE(NULLIF(e.published_at,''), e.fetched_at) DESC LIMIT ? OFFSET ?"
    args += [min(limit, 200), offset]
    conn = db()
    rows = conn.execute(sql, args).fetchall()
    conn.close()
    return [dict(r) for r in rows]


class StatusIn(BaseModel):
    status: str


@app.put("/api/entries/{eid}/status")
def set_status(eid: int, body: StatusIn, user=Depends(current_user)):
    if body.status not in ("read", "unread"):
        raise HTTPException(400, "状态只能是 read / unread")
    conn = db()
    conn.execute("UPDATE entries SET status = ? WHERE id = ?", (body.status, eid))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.post("/api/entries/mark-all-read")
def mark_all_read(feed_id: int = 0, category_id: int = 0, user=Depends(current_user)):
    conn = db()
    if feed_id:
        conn.execute(
            "UPDATE entries SET status = 'read' WHERE feed_id = ? AND status = 'unread'",
            (feed_id,),
        )
    elif category_id:
        conn.execute(
            "UPDATE entries SET status = 'read' WHERE status = 'unread' AND feed_id IN "
            "(SELECT id FROM feeds WHERE category_id = ?)",
            (category_id,),
        )
    else:
        conn.execute("UPDATE entries SET status = 'read' WHERE status = 'unread'")
    conn.commit()
    conn.close()
    return {"ok": True}


# ---------------------------------------------------------------- OPML


@app.get("/api/opml/export")
def export_opml(user=Depends(current_user)):
    conn = db()
    cats = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    feeds = conn.execute("SELECT * FROM feeds ORDER BY title").fetchall()
    conn.close()
    opml = ET.Element("opml", {"version": "2.0"})
    head = ET.SubElement(opml, "head")
    ET.SubElement(head, "title").text = "freshfeeds 订阅"
    body = ET.SubElement(opml, "body")

    def feed_outline(parent, f):
        o = ET.SubElement(
            parent,
            "outline",
            {
                "text": f["title"] or f["url"],
                "title": f["title"] or f["url"],
                "type": "rss",
                "xmlUrl": f["url"],
                "htmlUrl": f["site_url"] or "",
            },
        )
        return o

    by_cat = {}
    for f in feeds:
        by_cat.setdefault(f["category_id"], []).append(f)
    for c in cats:
        o = ET.SubElement(body, "outline", {"text": c["name"], "title": c["name"]})
        for f in by_cat.get(c["id"], []):
            feed_outline(o, f)
    for f in by_cat.get(None, []):
        feed_outline(body, f)
    xml = ET.tostring(opml, encoding="unicode", xml_declaration=True)
    return PlainTextResponse(
        xml,
        media_type="text/x-opml",
        headers={"Content-Disposition": "attachment; filename=freshfeeds.opml"},
    )


@app.post("/api/opml/import")
async def import_opml(file: UploadFile = File(...), user=Depends(current_user)):
    raw = await file.read()
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        raise HTTPException(400, "这不是合法的 OPML/XML 文件")
    conn = db()
    stats = {"total": 0, "added": 0, "skipped": 0, "failed": 0}
    new_ids = []

    def walk(parent, category_name):
        for o in parent.findall("outline"):
            xml_url = o.get("xmlUrl") or o.get("xmlurl") or ""
            if xml_url:
                stats["total"] += 1
                cid = None
                if category_name:
                    conn.execute(
                        "INSERT OR IGNORE INTO categories (name) VALUES (?)",
                        (category_name,),
                    )
                    cid = conn.execute(
                        "SELECT id FROM categories WHERE name = ?", (category_name,)
                    ).fetchone()["id"]
                try:
                    cur = conn.execute(
                        "INSERT INTO feeds (url, title, site_url, category_id, created_at) "
                        "VALUES (?,?,?,?,?)",
                        (
                            xml_url,
                            o.get("text") or o.get("title") or "",
                            o.get("htmlUrl") or "",
                            cid,
                            now_iso(),
                        ),
                    )
                    conn.commit()
                    new_ids.append(cur.lastrowid)
                    stats["added"] += 1
                except sqlite3.IntegrityError:
                    stats["skipped"] += 1
            else:
                walk(o, o.get("text") or o.get("title") or category_name)

    body = root.find("body")
    if body is not None:
        walk(body, "")
    conn.close()
    for fid in new_ids:
        try:
            refresh_feed(fid)
        except HTTPException:
            stats["failed"] += 1
    return stats


# ---------------------------------------------------------------- 定时刷新与入口


def _scheduler_loop():
    while True:
        time.sleep(REFRESH_MINUTES * 60)
        try:
            refresh_all()
        except Exception:
            pass


@app.get("/")
def index():
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
