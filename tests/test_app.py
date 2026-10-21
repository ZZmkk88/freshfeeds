import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

os.environ["FRESHFEEDS_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["FRESHFEEDS_SCHEDULER"] = "0"

import pytest
from fastapi.testclient import TestClient

import app as appmod

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>示例博客</title><link>https://blog.example.com/</link><description>d</description>
<item><title>第一篇文章</title><link>https://blog.example.com/a1</link>
<guid>post-1</guid><pubDate>Mon, 20 Oct 2026 08:00:00 GMT</pubDate>
<description>第一篇的摘要，讲抓取。</description></item>
<item><title>第二篇文章</title><link>https://blog.example.com/a2</link>
<guid>post-2</guid><pubDate>Tue, 21 Oct 2026 08:00:00 GMT</pubDate>
<description>第二篇的摘要，讲解析。</description></item>
</channel></rss>"""

ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>原子博客</title><link href="https://atom.example.com/"/>
<entry><id>urn:x:1</id><title>Atom 文章</title>
<link href="https://atom.example.com/e1"/>
<updated>2026-10-21T09:00:00Z</updated><summary>atom 摘要</summary></entry>
</feed>"""


@pytest.fixture(scope="module")
def client():
    with TestClient(appmod.app) as c:
        yield c


@pytest.fixture(scope="module")
def auth(client):
    r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    return {"Authorization": "Bearer " + r.json()["token"]}


def fake_fetch_factory(mapping):
    def fake(url, etag="", last_modified=""):
        text = mapping[url]
        return ("ok", text, "", "", "application/rss+xml")

    return fake


# ---------------------------------------------------------------- 登录


def test_login_wrong_password(client):
    r = client.post("/api/login", json={"username": "admin", "password": "nope"})
    assert r.status_code == 401


def test_need_auth(client):
    assert client.get("/api/feeds").status_code == 401


def test_me_and_change_password(client, auth):
    r = client.get("/api/me", headers=auth)
    assert r.json()["must_change_password"] is True
    r = client.post(
        "/api/change-password",
        json={"old_password": "admin123", "new_password": "newpass456"},
        headers=auth,
    )
    assert r.status_code == 200
    assert client.post(
        "/api/login", json={"username": "admin", "password": "admin123"}
    ).status_code == 401
    r = client.post(
        "/api/login", json={"username": "admin", "password": "newpass456"}
    )
    assert r.status_code == 200
    assert r.json()["must_change_password"] is False
    # 改回来，后面的测试继续用新密码登录
    auth2 = {"Authorization": "Bearer " + r.json()["token"]}
    r = client.post(
        "/api/change-password",
        json={"old_password": "newpass456", "new_password": "admin123"},
        headers=auth2,
    )
    assert r.status_code == 200


# ---------------------------------------------------------------- 订阅与解析


def test_add_feed_and_dedup(client, auth, monkeypatch):
    monkeypatch.setattr(appmod, "fetch_url", fake_fetch_factory({"https://blog.example.com/feed": RSS}))
    r = client.post("/api/feeds", json={"url": "https://blog.example.com/feed"}, headers=auth)
    assert r.status_code == 200
    assert r.json()["added"] == 2
    feeds = client.get("/api/feeds", headers=auth).json()
    assert feeds[0]["title"] == "示例博客"
    assert feeds[0]["unread"] == 2
    # 再刷一次：GUID 判重，一篇都不该新增
    r = client.post(f"/api/feeds/{feeds[0]['id']}/refresh", headers=auth)
    assert r.json()["added"] == 0
    # 重复订阅同一地址应报错
    r = client.post("/api/feeds", json={"url": "https://blog.example.com/feed"}, headers=auth)
    assert r.status_code == 400


def test_atom_feed(client, auth, monkeypatch):
    monkeypatch.setattr(appmod, "fetch_url", fake_fetch_factory({"https://atom.example.com/feed": ATOM}))
    r = client.post("/api/feeds", json={"url": "https://atom.example.com/feed"}, headers=auth)
    assert r.json()["added"] == 1
    entries = client.get("/api/entries", params={"q": "Atom"}, headers=auth).json()
    assert len(entries) == 1
    assert entries[0]["feed_title"] == "原子博客"


def test_real_http_fetch(client, auth):
    """不打桩：本地真起一个 HTTP 服务器，走真实抓取路径。"""
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            body = RSS.encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/rss+xml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}/feed.xml"
    r = client.post("/api/feeds", json={"url": url}, headers=auth)
    assert r.status_code == 200
    assert r.json()["added"] == 2
    srv.shutdown()


def test_not_modified(client, auth, monkeypatch):
    def fake304(url, etag="", last_modified=""):
        return ("not_modified", "", etag, last_modified, "")

    monkeypatch.setattr(appmod, "fetch_url", fake304)
    feeds = client.get("/api/feeds", headers=auth).json()
    r = client.post(f"/api/feeds/{feeds[0]['id']}/refresh", headers=auth)
    assert r.json()["added"] == 0
    assert r.json()["not_modified"] is True


# ---------------------------------------------------------------- 已读/分类/搜索


def test_status_toggle_and_filters(client, auth):
    entries = client.get("/api/entries", headers=auth).json()
    assert entries
    eid = entries[0]["id"]
    r = client.put(f"/api/entries/{eid}/status", json={"status": "read"}, headers=auth)
    assert r.status_code == 200
    unread = client.get("/api/entries", params={"status": "unread"}, headers=auth).json()
    assert all(e["id"] != eid for e in unread)
    client.put(f"/api/entries/{eid}/status", json={"status": "unread"}, headers=auth)
    unread2 = client.get("/api/entries", params={"status": "unread"}, headers=auth).json()
    assert any(e["id"] == eid for e in unread2)
    # 非法状态
    assert client.put(
        f"/api/entries/{eid}/status", json={"status": "x"}, headers=auth
    ).status_code == 400


def test_category_flow(client, auth, monkeypatch):
    r = client.post("/api/categories", json={"name": "技术"}, headers=auth)
    assert r.status_code == 200
    cid = r.json()["id"]
    assert client.post("/api/categories", json={"name": "技术"}, headers=auth).status_code == 400
    monkeypatch.setattr(appmod, "fetch_url", fake_fetch_factory({"https://blog.example.com/feed2": RSS}))
    r = client.post(
        "/api/feeds",
        json={"url": "https://blog.example.com/feed2", "category_id": cid},
        headers=auth,
    )
    assert r.status_code == 200
    in_cat = client.get("/api/entries", params={"category_id": cid}, headers=auth).json()
    assert len(in_cat) == 2
    # 删分类：源保留、文章还在，只是不再归类
    assert client.delete(f"/api/categories/{cid}", headers=auth).status_code == 200
    feeds = client.get("/api/feeds", headers=auth).json()
    f2 = [f for f in feeds if f["url"].endswith("feed2")][0]
    assert f2["category_id"] is None


def test_search(client, auth):
    hits = client.get("/api/entries", params={"q": "解析"}, headers=auth).json()
    assert hits and all("解析" in (e["title"] + e["content"]) for e in hits)
    assert client.get("/api/entries", params={"q": "不存在的词xyz"}, headers=auth).json() == []


def test_mark_all_read(client, auth):
    assert client.post("/api/entries/mark-all-read", headers=auth).status_code == 200
    unread = client.get("/api/entries", params={"status": "unread"}, headers=auth).json()
    assert unread == []


def test_delete_feed(client, auth):
    feeds = client.get("/api/feeds", headers=auth).json()
    target = [f for f in feeds if f["url"].startswith("http://127.0.0.1")][0]
    assert client.delete(f"/api/feeds/{target['id']}", headers=auth).status_code == 200
    left = client.get("/api/entries", headers=auth).json()
    assert all(e["feed_id"] != target["id"] for e in left)


# ---------------------------------------------------------------- OPML


def test_opml_roundtrip(client, auth, monkeypatch):
    r = client.get("/api/opml/export", headers=auth)
    assert r.status_code == 200
    assert "xmlUrl" in r.text and "blog.example.com" in r.text

    opml = """<?xml version="1.0"?>
    <opml version="2.0"><body>
      <outline text="新闻">
        <outline text="新闻源" type="rss" xmlUrl="https://news.example.com/rss" htmlUrl="https://news.example.com/"/>
      </outline>
    </body></opml>"""
    monkeypatch.setattr(appmod, "fetch_url", fake_fetch_factory({"https://news.example.com/rss": RSS}))
    r = client.post(
        "/api/opml/import",
        files={"file": ("sub.opml", opml, "text/x-opml")},
        headers=auth,
    )
    assert r.status_code == 200
    assert r.json()["added"] == 1
    cats = client.get("/api/categories", headers=auth).json()
    assert any(c["name"] == "新闻" for c in cats)
    # 再导入一次：判重跳过
    r = client.post(
        "/api/opml/import",
        files={"file": ("sub.opml", opml, "text/x-opml")},
        headers=auth,
    )
    assert r.json()["skipped"] == 1


def test_opml_bad_file(client, auth):
    r = client.post(
        "/api/opml/import",
        files={"file": ("x.opml", "not xml at all", "text/plain")},
        headers=auth,
    )
    assert r.status_code == 400
