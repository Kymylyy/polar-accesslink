#!/usr/bin/env python3
"""Minimal helper for Polar AccessLink OAuth on localhost."""

from __future__ import annotations

import base64
import json
import os
import secrets
import sys
import threading
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

AUTH_URL = "https://flow.polar.com/oauth2/authorization"
TOKEN_URL = "https://polarremote.com/v2/oauth2/token"
REGISTER_URL = "https://www.polaraccesslink.com/v3/users"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:3000/auth/polar/callback"
DEFAULT_SCOPE = "accesslink.read_all"


@dataclass
class CallbackResult:
    code: str | None = None
    error: str | None = None
    error_description: str | None = None


def load_env(name: str, *, required: bool = True, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    if required and not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def build_auth_url(client_id: str, redirect_uri: str, state: str, scope: str) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def token_request(
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict[str, Any]:
    auth_bytes = f"{client_id}:{client_secret}".encode()
    auth_header = base64.b64encode(auth_bytes).decode("ascii")
    body = urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
    ).encode("utf-8")
    request = Request(
        TOKEN_URL,
        data=body,
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json;charset=UTF-8",
        },
        method="POST",
    )
    return request_json(request)


def register_user(access_token: str, member_id: str) -> dict[str, Any]:
    body = json.dumps({"member-id": member_id}).encode("utf-8")
    request = Request(
        REGISTER_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    return request_json(request)


def request_json(request: Request) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload) if payload else {}
    except HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code} calling {request.full_url}", file=sys.stderr)
        if payload:
            print(payload, file=sys.stderr)
        sys.exit(1)
    except URLError as exc:
        print(f"Network error calling {request.full_url}: {exc}", file=sys.stderr)
        sys.exit(1)


def make_handler(
    expected_path: str,
    expected_state: str,
    result: CallbackResult,
    done: threading.Event,
):
    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != expected_path:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found")
                return

            params = parse_qs(parsed.query)
            state = params.get("state", [None])[0]
            code = params.get("code", [None])[0]
            error = params.get("error", [None])[0]
            error_description = params.get("error_description", [None])[0]

            if state != expected_state:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid OAuth state")
                result.error = "invalid_state"
                result.error_description = "Returned state does not match."
                done.set()
                return

            result.code = code
            result.error = error
            result.error_description = error_description

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"""<!doctype html>
<html>
  <body style="font-family: sans-serif; padding: 2rem;">
    <h1>Polar authorization received</h1>
    <p>You can return to the terminal.</p>
  </body>
</html>"""
            )
            done.set()

        def log_message(self, format: str, *args: Any) -> None:
            return

    return CallbackHandler


def main() -> None:
    client_id = load_env("POLAR_CLIENT_ID")
    client_secret = load_env("POLAR_CLIENT_SECRET")
    redirect_uri = load_env("POLAR_REDIRECT_URI", default=DEFAULT_REDIRECT_URI)
    member_id = load_env("POLAR_MEMBER_ID", required=False)
    scope = load_env("POLAR_SCOPE", required=False, default=DEFAULT_SCOPE) or DEFAULT_SCOPE
    open_browser = load_env("POLAR_OPEN_BROWSER", required=False, default="1") == "1"

    parsed_redirect = urlparse(redirect_uri or "")
    if (
        parsed_redirect.scheme != "http"
        or parsed_redirect.hostname != "127.0.0.1"
        or parsed_redirect.port != 3000
    ):
        print(
            "This helper expects POLAR_REDIRECT_URI to be http://127.0.0.1:3000/auth/polar/callback",
            file=sys.stderr,
        )
        sys.exit(1)

    state = secrets.token_urlsafe(24)
    result = CallbackResult()
    done = threading.Event()
    handler = make_handler(parsed_redirect.path, state, result, done)
    server = ThreadingHTTPServer((parsed_redirect.hostname, parsed_redirect.port), handler)
    auth_url = build_auth_url(client_id or "", redirect_uri or "", state, scope)

    print("Polar OAuth helper")
    print(f"Redirect URI: {redirect_uri}")
    print(f"Auth URL: {auth_url}")
    print()
    print("Waiting for Polar callback on http://127.0.0.1:3000 ...")

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    if open_browser:
        webbrowser.open(auth_url)

    try:
        if not done.wait(timeout=300):
            print("Timed out waiting for Polar callback.", file=sys.stderr)
            sys.exit(1)
    finally:
        server.shutdown()
        server.server_close()

    if result.error:
        description = f": {result.error_description}" if result.error_description else ""
        print(f"Polar authorization failed with {result.error}{description}", file=sys.stderr)
        sys.exit(1)

    if not result.code:
        print("Polar callback did not include an authorization code.", file=sys.stderr)
        sys.exit(1)

    token_payload = token_request(
        client_id or "",
        client_secret or "",
        result.code,
        redirect_uri or "",
    )
    print()
    print("Token response:")
    print(json.dumps(token_payload, indent=2, sort_keys=True))

    access_token = token_payload.get("access_token")
    if member_id and access_token:
        register_payload = register_user(access_token, member_id)
        print()
        print("User registration response:")
        print(json.dumps(register_payload, indent=2, sort_keys=True))
    elif not member_id:
        print()
        print("POLAR_MEMBER_ID not set, skipping POST /v3/users registration.")


if __name__ == "__main__":
    main()
