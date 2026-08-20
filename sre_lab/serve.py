from __future__ import annotations

import argparse
import hmac
import json
import os
import secrets
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .platform import PlatformApp, PlatformError
from .token_store import TokenStore
from .web import WEB_APP_HTML


class WebSessionStore:
    def __init__(self, username: str | None, password: str | None,
                 admin_username: str | None = None, admin_password: str | None = None,
                 *, ttl_seconds: int = 8 * 3600):
        self.username = username
        self.password = password
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, tuple[str, bool, float]] = {}
        self._lock = threading.RLock()

    @property
    def enabled(self) -> bool:
        return bool(self.username and self.password)

    def user(self, token: str | None) -> str | None:
        if not token:
            return None
        with self._lock:
            value = self._sessions.get(token)
            if not value:
                return None
            username, _is_admin, expires = value
            if expires <= time.time():
                self._sessions.pop(token, None)
                return None
            return username

    def is_admin(self, token: str | None) -> bool:
        if not token:
            return False
        with self._lock:
            value = self._sessions.get(token)
            return bool(value and value[2] > time.time() and value[1])

    def login_result(self, username: str, password: str) -> tuple[str, str, bool] | None:
        if not self.enabled:
            return None
        valid_user = username == self.username and hmac.compare_digest(password, self.password or "")
        valid_admin = username == self.admin_username and hmac.compare_digest(password, self.admin_password or "")
        if not (valid_user or valid_admin):
            return None
        token = secrets.token_urlsafe(32)
        is_admin = valid_admin
        with self._lock:
            self._sessions[token] = (username, is_admin, time.time() + self.ttl_seconds)
        return token, username, is_admin

    def revoke(self, token: str | None) -> None:
        if token:
            with self._lock:
                self._sessions.pop(token, None)


def make_handler(app: PlatformApp, *, web_username: str | None = None,
                 web_password: str | None = None, web_admin_username: str | None = None,
                 web_admin_password: str | None = None, platform_token: str | None = None,
                 token_store: TokenStore | None = None):
    sessions = WebSessionStore(web_username, web_password, web_admin_username, web_admin_password)

    class Handler(BaseHTTPRequestHandler):
        def _write(self, status: int, payload: dict[str, Any], *, headers: dict[str, str] | None = None) -> None:
            data = json.dumps(payload, ensure_ascii=False, default=str).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(data)

        def _html(self) -> None:
            data = WEB_APP_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _session_token(self) -> str | None:
            cookies = SimpleCookie()
            cookies.load(self.headers.get("Cookie", ""))
            morsel = cookies.get("lab_session")
            return morsel.value if morsel else None

        def _session_headers(self) -> dict[str, str]:
            headers = {key: value for key, value in self.headers.items()}
            if "Authorization" not in headers and platform_token and sessions.user(self._session_token()):
                headers["Authorization"] = f"Bearer {platform_token}"
            return headers

        def _body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 256_000:
                raise PlatformError("request exceeds size limit")
            raw = self.rfile.read(length) if length else b"{}"
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise PlatformError("request body must be an object")
            return parsed

        def _dispatch(self) -> None:
            try:
                route = self.path.split("?", 1)[0]
                if self.command == "GET" and route == "/":
                    self._html()
                    return
                body = self._body() if self.command == "POST" else {}
                if route == "/v1/login" and self.command == "POST":
                    result = sessions.login_result(str(body.get("username", "")), str(body.get("password", "")))
                    if not result:
                        self._write(401, {"error": "用户名或密码错误"})
                        return
                    token, username, is_admin = result
                    self._write(200, {"ok": True, "user": username, "is_admin": is_admin}, headers={
                        "Set-Cookie": f"lab_session={token}; Path=/; HttpOnly; Secure; SameSite=Lax"
                    })
                    return
                if route == "/v1/session" and self.command == "GET":
                    username = sessions.user(self._session_token())
                    if not username:
                        self._write(401, {"error": "未登录"})
                        return
                    self._write(200, {"ok": True, "user": username, "is_admin": sessions.is_admin(self._session_token())})
                    return
                if route == "/v1/logout" and self.command == "POST":
                    sessions.revoke(self._session_token())
                    self._write(200, {"ok": True}, headers={
                        "Set-Cookie": "lab_session=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax"
                    })
                    return
                if route == "/v1/admin/tokens" and self.command == "GET":
                    if not sessions.is_admin(self._session_token()):
                        self._write(403, {"error": "管理员权限 required"})
                        return
                    self._write(200, {"tokens": token_store.list() if token_store else []})
                    return
                if route == "/v1/admin/tokens" and self.command == "POST":
                    if not sessions.is_admin(self._session_token()):
                        self._write(403, {"error": "管理员权限 required"})
                        return
                    if not token_store:
                        self._write(503, {"error": "token store unavailable"})
                        return
                    issued = token_store.issue(
                        str(body.get("name", "")), ttl_days=int(body.get("ttl_days", 7)),
                        scopes=body.get("scopes"), owner=str(body.get("owner", "")),
                        created_by=sessions.user(self._session_token()) or "",
                    )
                    self._write(201, issued, headers={"Location": f"/v1/admin/tokens/{issued['token_id']}"})
                    return
                if route.startswith("/v1/admin/tokens/") and route.endswith("/revoke") and self.command == "POST":
                    if not sessions.is_admin(self._session_token()):
                        self._write(403, {"error": "管理员权限 required"})
                        return
                    if not token_store or not token_store.revoke(route.split("/")[4]):
                        self._write(404, {"error": "token not found"})
                        return
                    self._write(200, {"ok": True})
                    return
                headers = self._session_headers()
                result = app.handle(self.command, route, body, headers)
                self._write(200, result)
            except PlatformError as exc:
                status = 401 if str(exc) == "unauthorized" else (403 if str(exc) == "forbidden" else 400)
                self._write(status, {"error": str(exc)})
            except (ValueError, json.JSONDecodeError) as exc:
                self._write(400, {"error": str(exc)})
            except Exception:
                self._write(500, {"error": "internal server error"})

        do_GET = _dispatch
        do_POST = _dispatch

        def log_message(self, *_args: Any) -> None:
            return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the Contabo SRE lab platform API")
    parser.add_argument("--case-root", default="data/rca100")
    parser.add_argument("--ground-truth-root", default="data/rca100/answer_key")
    parser.add_argument("--reports-dir", default="reports/runs")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    token = os.environ.get("LAB_ACCESS_TOKEN")
    web_username = os.environ.get("LAB_WEB_USERNAME")
    web_password = os.environ.get("LAB_WEB_PASSWORD")
    web_admin_username = os.environ.get("LAB_WEB_ADMIN_USERNAME")
    web_admin_password = os.environ.get("LAB_WEB_ADMIN_PASSWORD")
    token_store = TokenStore(os.environ.get("LAB_TOKEN_STORE", str(Path.home() / ".config/sre-lab/tokens.json")))
    app = PlatformApp(args.case_root, args.ground_truth_root, reports_dir=args.reports_dir,
                      access_tokens={token} if token else None, token_validator=token_store.verify)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(
        app, web_username=web_username, web_password=web_password,
        web_admin_username=web_admin_username, web_admin_password=web_admin_password,
        platform_token=token, token_store=token_store))
    print(f"SRE lab listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
