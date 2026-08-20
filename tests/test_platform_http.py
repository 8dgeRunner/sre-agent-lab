import json
import threading
import urllib.error
import urllib.request

import pytest
from http.server import ThreadingHTTPServer

from sre_lab.serve import make_handler
from sre_lab.token_store import TokenStore
from test_platform import make_app


def test_http_gateway_serves_cases_and_starts_run(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(make_app(tmp_path)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urllib.request.urlopen(base + "/v1/cases") as response:
            assert json.loads(response.read())["cases"][0]["case_id"] == "t001"
        request = urllib.request.Request(
            base + "/v1/runs", data=json.dumps({"case_id": "t001", "agent_id": "alice"}).encode(),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read())
            assert payload["status"] == "running"
            assert payload["run_id"]
    finally:
        server.shutdown()
        server.server_close()


def test_web_login_uses_secure_session_cookie_for_api(tmp_path):
    app = make_app(tmp_path)
    app.access_tokens = {"platform-token"}
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(
        app, web_username="demo", web_password="correct-password", platform_token="platform-token"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urllib.request.urlopen(base + "/") as response:
            html = response.read().decode()
            assert "SRE Agent 靶场" in html
            assert "登录平台" in html
        login = urllib.request.Request(
            base + "/v1/login",
            data=json.dumps({"username": "demo", "password": "correct-password"}).encode(),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(login) as response:
            cookie = response.headers["Set-Cookie"].split(";", 1)[0]
            assert "HttpOnly" in response.headers["Set-Cookie"]
            assert "Secure" in response.headers["Set-Cookie"]
        cases = urllib.request.Request(base + "/v1/cases", headers={"Cookie": cookie})
        with urllib.request.urlopen(cases) as response:
            assert json.loads(response.read())["cases"][0]["case_id"] == "t001"
    finally:
        server.shutdown()
        server.server_close()


def test_web_login_rejects_wrong_password(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(
        make_app(tmp_path), web_username="demo", web_password="correct-password"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/v1/login",
            data=json.dumps({"username": "demo", "password": "wrong"}).encode(),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(request)
        assert exc.value.code == 401
    finally:
        server.shutdown()
        server.server_close()


def test_admin_can_issue_and_revoke_agent_token(tmp_path):
    app = make_app(tmp_path)
    app.access_tokens = {"platform-token"}
    token_store = TokenStore(tmp_path / "tokens.json")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(
        app, web_username="guest", web_password="guest-password",
        web_admin_username="admin", web_admin_password="admin-password",
        platform_token="platform-token", token_store=token_store))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        login = urllib.request.Request(
            base + "/v1/login", data=json.dumps({"username": "admin", "password": "admin-password"}).encode(),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(login) as response:
            cookie = response.headers["Set-Cookie"].split(";", 1)[0]
            assert json.loads(response.read())["is_admin"] is True
        request = urllib.request.Request(
            base + "/v1/admin/tokens", data=json.dumps({"name": "alice-agent", "ttl_days": 7}).encode(),
            headers={"Content-Type": "application/json", "Cookie": cookie}, method="POST",
        )
        with urllib.request.urlopen(request) as response:
            issued = json.loads(response.read())
        assert token_store.verify(issued["token"])
        assert issued["owner"] == ""
        assert issued["created_by"] == "admin"
        revoke = urllib.request.Request(
            base + f"/v1/admin/tokens/{issued['token_id']}/revoke", data=b"{}",
            headers={"Content-Type": "application/json", "Cookie": cookie}, method="POST",
        )
        with urllib.request.urlopen(revoke) as response:
            assert json.loads(response.read())["ok"] is True
        assert not token_store.verify(issued["token"])
    finally:
        server.shutdown()
        server.server_close()


def test_agent_token_scope_is_enforced_by_http_gateway(tmp_path):
    app = make_app(tmp_path)
    token_store = TokenStore(tmp_path / "tokens.json")
    app.token_validator = token_store.verify
    issued = token_store.issue("case-browser", scopes=["run:create"])
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app, token_store=token_store))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    headers = {"Authorization": f"Bearer {issued['token']}"}
    try:
        with urllib.request.urlopen(urllib.request.Request(base + "/v1/cases", headers=headers)) as response:
            assert json.loads(response.read())["cases"]
        start = urllib.request.Request(
            base + "/v1/runs", data=json.dumps({"case_id": "t001"}).encode(),
            headers={**headers, "Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(start) as response:
            run_id = json.loads(response.read())["run_id"]
        tool = urllib.request.Request(
            base + f"/v1/runs/{run_id}/tools", data=json.dumps({"tool": "get_alerts", "arguments": {}}).encode(),
            headers={**headers, "Content-Type": "application/json"}, method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(tool)
        assert exc.value.code == 403
    finally:
        server.shutdown()
        server.server_close()
