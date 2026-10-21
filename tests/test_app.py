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

RDF10 = """<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns="http://purl.org/rss/1.0/">
<channel rdf:about="https://rdf.example/"><title>RDF 标题</title><link>https://rdf.example/</link></channel>
<item rdf:about="https://rdf.example/1"><title>RDF 文章</title><link>https://rdf.example/1</link></item>
</rdf:RDF>"""

JS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>JS 测试源</title><link>https://js.example/</link>
<item><title>点我</title><link>javascript:alert(1)</link><guid>js-1</guid></item>
<item><title>正常</title><link>https://js.example/ok</link><guid>js-2</guid></item>
</channel></rss>"""


@pytest.fixture(scope="module")
def client():
    with TestClient(appmod.app) as c:
        yield c


def login(client):
    """每个用例独立登录（口径第 17 条：不许用模块级共享 token 掩盖会话逻辑）。"""
    r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    return {"Authorization": "Bearer " + r.json()["token"]}


def no_ssrf(monkeypatch):
    """本轮只测抓取流程、不测 SSRF 的用例：跳过内网校验。"""
    monkeypatch.setattr(appmod, "ensure_fetch_allowed", lambda url: None)


def fake_fetch_factory(mapping):
    def fake(url, etag="", last_modified=""):
        return ("ok", mapping[url], "", "", "application/rss+xml")

    return fake


# ---------------------------------------------------------------- 登录


def test_login_wrong_password(client):
    r = client.post("/api/login", json={"username": "admin", "password": "nope"})
    assert r.status_code == 401


def test_need_auth(client):
    assert client.get("/api/feeds").status_code == 401


def test_me_and_change_password(client):
    auth = login(client)
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
    r = client.post("/api/login", json={"username": "admin", "password": "newpass456"})
    assert r.status_code == 200
    assert r.json()["must_change_password"] is False
    auth2 = {"Authorization": "Bearer " + r.json()["token"]}
    r = client.post(
        "/api/change-password",
        json={"old_password": "newpass456", "new_password": "admin123"},
        headers=auth2,
    )
    assert r.status_code == 200


def test_password_change_revokes_other_tokens(client):
    """口径第 2 条：改密同事务吊销除本次外其他会话，本次会话保留。"""
    auth_a = login(client)
    auth_b = login(client)
    assert client.get("/api/me", headers=auth_a).status_code == 200
    r = client.post(
        "/api/change-password",
        json={"old_password": "admin123", "new_password": "temp999"},
        headers=auth_b,
    )
    assert r.status_code == 200
    assert client.get("/api/me", headers=auth_a).status_code == 401  # 旧会话被踢
    assert client.get("/api/me", headers=auth_b).status_code == 200  # 本次会话保留
    r = client.post(
        "/api/change-password",
        json={"old_password": "temp999", "new_password": "admin123"},
        headers=auth_b,
    )
    assert r.status_code == 200


# ---------------------------------------------------------------- 订阅与解析


def test_add_feed_and_dedup(client, monkeypatch):
    auth = login(client)
    no_ssrf(monkeypatch)
    monkeypatch.setattr(
        appmod, "fetch_url", fake_fetch_factory({"https://blog.example.com/feed": RSS})
    )
    r = client.post("/api/feeds", json={"url": "https://blog.example.com/feed"}, headers=auth)
    assert r.status_code == 200
    assert r.json()["added"] == 2
    feeds = client.get("/api/feeds", headers=auth).json()
    assert feeds[0]["title"] == "示例博客"
    assert feeds[0]["unread"] == 2
    r = client.post(f"/api/feeds/{feeds[0]['id']}/refresh", headers=auth)
    assert r.json()["added"] == 0
    r = client.post("/api/feeds", json={"url": "https://blog.example.com/feed"}, headers=auth)
    assert r.status_code == 400
    assert "已经订阅" in r.json()["detail"]


def test_bad_category_message(client, monkeypatch):
    """P2-3：不存在的分类不再报成"已经订阅过了"。"""
    auth = login(client)
    no_ssrf(monkeypatch)
    monkeypatch.setattr(appmod, "fetch_url", fake_fetch_factory({"https://x.example/f": RSS}))
    r = client.post(
        "/api/feeds", json={"url": "https://x.example/f", "category_id": 99999}, headers=auth
    )
    assert r.status_code == 400
    assert "分类不存在" in r.json()["detail"]


def test_atom_feed(client, monkeypatch):
    auth = login(client)
    no_ssrf(monkeypatch)
    monkeypatch.setattr(
        appmod, "fetch_url", fake_fetch_factory({"https://atom.example.com/feed": ATOM})
    )
    r = client.post("/api/feeds", json={"url": "https://atom.example.com/feed"}, headers=auth)
    assert r.json()["added"] == 1
    entries = client.get("/api/entries", params={"q": "Atom"}, headers=auth).json()
    assert len(entries) == 1
    assert entries[0]["feed_title"] == "原子博客"


def test_rdf10_title_and_link(client, monkeypatch):
    """P2-1：RSS 1.0 的 channel 标题/站点链接在命名空间下也要读到。"""
    auth = login(client)
    no_ssrf(monkeypatch)
    monkeypatch.setattr(
        appmod, "fetch_url", fake_fetch_factory({"https://rdf.example/feed": RDF10})
    )
    r = client.post("/api/feeds", json={"url": "https://rdf.example/feed"}, headers=auth)
    assert r.json()["added"] == 1
    feeds = client.get("/api/feeds", headers=auth).json()
    f = [x for x in feeds if x["url"] == "https://rdf.example/feed"][0]
    assert f["title"] == "RDF 标题"
    assert f["site_url"] == "https://rdf.example/"


def test_javascript_url_blanked(client, monkeypatch):
    """P1-2：条目里的 javascript: 链接入库置空。"""
    auth = login(client)
    no_ssrf(monkeypatch)
    monkeypatch.setattr(
        appmod, "fetch_url", fake_fetch_factory({"https://js.example/feed": JS_FEED})
    )
    r = client.post("/api/feeds", json={"url": "https://js.example/feed"}, headers=auth)
    assert r.json()["added"] == 2
    entries = client.get("/api/entries", params={"q": "点我"}, headers=auth).json()
    assert len(entries) == 1
    assert entries[0]["url"] == ""
    ok = client.get("/api/entries", params={"q": "正常"}, headers=auth).json()
    assert ok and ok[0]["url"] == "https://js.example/ok"


def test_real_http_fetch(client, monkeypatch):
    """不打桩：本地真起一个 HTTP 服务器，走真实抓取路径。"""
    no_ssrf(monkeypatch)

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
    auth = login(client)
    url = f"http://127.0.0.1:{srv.server_port}/feed.xml"
    r = client.post("/api/feeds", json={"url": url}, headers=auth)
    assert r.status_code == 200
    assert r.json()["added"] == 2
    srv.shutdown()


# ---------------------------------------------------------------- SSRF（口径第 9 条）


def test_ssrf_blocked_targets():
    with pytest.raises(appmod.BlockedUrlError):
        appmod.ensure_fetch_allowed("file:///etc/passwd")
    with pytest.raises(appmod.BlockedUrlError):
        appmod.ensure_fetch_allowed("http://127.0.0.1/feed.xml")
    with pytest.raises(appmod.BlockedUrlError):
        appmod.ensure_fetch_allowed("http://169.254.169.254/latest/meta-data")
    with pytest.raises(appmod.BlockedUrlError):
        appmod.ensure_fetch_allowed("http://10.1.2.3/x")
    with pytest.raises(appmod.BlockedUrlError):
        appmod.ensure_fetch_allowed("javascript:alert(1)")


def test_ssrf_allows_public_and_fakeip_range(monkeypatch):
    # 字面公网 IP 直接判，不走 DNS
    appmod.ensure_fetch_allowed("http://93.184.216.34/")
    # 域名解析路径：注入公网地址
    monkeypatch.setattr(
        appmod, "resolve_host_addresses", lambda host: ["93.184.216.34"]
    )
    appmod.ensure_fetch_allowed("http://example.com/")
    # 198.18/15 是本云端假 IP DNS 的保留段，不能拦，否则真实网站全挂
    assert appmod._is_public_ip("198.18.0.1") is True


def test_ssrf_redirect_to_internal_blocked():
    """重定向每一跳都校验：302 跳到 127.0.0.1:1 必须在第二跳被拦。"""

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:1/evil")
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    real = appmod.ensure_fetch_allowed

    def fake(url):
        if url.startswith("http://127.0.0.1:1/"):
            raise appmod.BlockedUrlError("test block")
        return real(url)

    appmod.ensure_fetch_allowed = fake
    try:
        with pytest.raises(appmod.BlockedUrlError):
            appmod.fetch_url(f"http://127.0.0.1:{srv.server_port}/go")
    finally:
        appmod.ensure_fetch_allowed = real
        srv.shutdown()


def test_create_feed_internal_url_rejected(client):
    auth = login(client)
    r = client.post(
        "/api/feeds", json={"url": "http://127.0.0.1/feed.xml"}, headers=auth
    )
    assert r.status_code == 400
    assert "内网" in r.json()["detail"] or "拒绝" in r.json()["detail"]


def test_not_modified_real(client, monkeypatch):
    auth = login(client)

    def fake304(url, etag="", last_modified=""):
        return ("not_modified", "", etag, last_modified, "")

    monkeypatch.setattr(appmod, "fetch_url", fake304)
    feeds = client.get("/api/feeds", headers=auth).json()
    r = client.post(f"/api/feeds/{feeds[0]['id']}/refresh", headers=auth)
    assert r.json()["added"] == 0
    assert r.json()["not_modified"] is True


# ---------------------------------------------------------------- 已读/分类/搜索


def test_status_toggle_and_filters(client):
    auth = login(client)
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
    assert client.put(
        f"/api/entries/{eid}/status", json={"status": "x"}, headers=auth
    ).status_code == 400


def test_limit_clamped(client):
    """P2-2：limit=-1 不能绕过上限。"""
    auth = login(client)
    r = client.get("/api/entries", params={"limit": -1}, headers=auth)
    assert r.status_code == 200
    assert len(r.json()) <= 1  # 被夹到 1


def test_category_flow(client, monkeypatch):
    auth = login(client)
    r = client.post("/api/categories", json={"name": "技术"}, headers=auth)
    assert r.status_code == 200
    cid = r.json()["id"]
    assert client.post("/api/categories", json={"name": "技术"}, headers=auth).status_code == 400
    no_ssrf(monkeypatch)
    monkeypatch.setattr(
        appmod, "fetch_url", fake_fetch_factory({"https://blog.example.com/feed2": RSS})
    )
    r = client.post(
        "/api/feeds",
        json={"url": "https://blog.example.com/feed2", "category_id": cid},
        headers=auth,
    )
    assert r.status_code == 200
    in_cat = client.get("/api/entries", params={"category_id": cid}, headers=auth).json()
    assert len(in_cat) == 2
    assert client.delete(f"/api/categories/{cid}", headers=auth).status_code == 200
    feeds = client.get("/api/feeds", headers=auth).json()
    f2 = [f for f in feeds if f["url"].endswith("feed2")][0]
    assert f2["category_id"] is None


def test_search(client):
    auth = login(client)
    hits = client.get("/api/entries", params={"q": "解析"}, headers=auth).json()
    assert hits and all("解析" in (e["title"] + e["content"]) for e in hits)
    assert client.get("/api/entries", params={"q": "不存在的词xyz"}, headers=auth).json() == []


def test_mark_all_read(client):
    auth = login(client)
    assert client.post("/api/entries/mark-all-read", headers=auth).status_code == 200
    unread = client.get("/api/entries", params={"status": "unread"}, headers=auth).json()
    assert unread == []


def test_delete_feed(client):
    auth = login(client)
    feeds = client.get("/api/feeds", headers=auth).json()
    target = [f for f in feeds if f["url"].endswith("feed2")][0]
    assert client.delete(f"/api/feeds/{target['id']}", headers=auth).status_code == 200
    left = client.get("/api/entries", headers=auth).json()
    assert all(e["feed_id"] != target["id"] for e in left)


# ---------------------------------------------------------------- OPML


def test_opml_roundtrip(client, monkeypatch):
    auth = login(client)
    r = client.get("/api/opml/export", headers=auth)
    assert r.status_code == 200
    assert "xmlUrl" in r.text and "blog.example.com" in r.text

    opml = """<?xml version="1.0"?>
    <opml version="2.0"><body>
      <outline text="新闻">
        <outline text="新闻源" type="rss" xmlUrl="https://news.example.com/rss" htmlUrl="https://news.example.com/"/>
      </outline>
    </body></opml>"""
    no_ssrf(monkeypatch)
    monkeypatch.setattr(
        appmod, "fetch_url", fake_fetch_factory({"https://news.example.com/rss": RSS})
    )
    r = client.post(
        "/api/opml/import",
        files={"file": ("sub.opml", opml, "text/x-opml")},
        headers=auth,
    )
    assert r.status_code == 200
    assert r.json()["added"] == 1
    cats = client.get("/api/categories", headers=auth).json()
    assert any(c["name"] == "新闻" for c in cats)
    r = client.post(
        "/api/opml/import",
        files={"file": ("sub.opml", opml, "text/x-opml")},
        headers=auth,
    )
    assert r.json()["skipped"] == 1


def test_opml_bad_file(client):
    auth = login(client)
    r = client.post(
        "/api/opml/import",
        files={"file": ("x.opml", "not xml at all", "text/plain")},
        headers=auth,
    )
    assert r.status_code == 400


def test_opml_size_limit(client):
    """P1-4：超过 2MB 的 OPML 直接拒绝。"""
    auth = login(client)
    big = b'<?xml version="1.0"?><opml><body>' + b"x" * (2_000_001) + b"</body></opml>"
    r = client.post(
        "/api/opml/import",
        files={"file": ("big.opml", big, "text/x-opml")},
        headers=auth,
    )
    assert r.status_code == 400
    assert "2MB" in r.json()["detail"]


def test_opml_dtd_rejected(client):
    """P1-4：带 DTD/实体声明的 OPML 直接拒绝，不交给解析器展开。"""
    auth = login(client)
    evil = (
        b'<?xml version="1.0"?><!DOCTYPE opml [<!ENTITY x "EXPANDED">]>'
        b'<opml><body></body></opml>'
    )
    r = client.post(
        "/api/opml/import",
        files={"file": ("evil.opml", evil, "text/x-opml")},
        headers=auth,
    )
    assert r.status_code == 400
    assert "DTD" in r.json()["detail"]


def test_opml_internal_url_failed(client):
    """P1-1：OPML 里 file:// 等地址记失败、不入库（用真实 SSRF 校验）。"""
    auth = login(client)
    opml = """<?xml version="1.0"?>
    <opml version="2.0"><body>
      <outline text="坏源" type="rss" xmlUrl="file:///etc/passwd"/>
    </body></opml>"""
    r = client.post(
        "/api/opml/import",
        files={"file": ("bad.opml", opml, "text/x-opml")},
        headers=auth,
    )
    assert r.status_code == 200
    assert r.json()["failed"] == 1
    assert r.json()["added"] == 0
    feeds = client.get("/api/feeds", headers=auth).json()
    assert not any("file://" in f["url"] for f in feeds)
