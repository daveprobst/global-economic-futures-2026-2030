#!/usr/bin/env python3
"""Lightweight static server for the Global Economic Futures, 2026–2030 explorer.

Serves only the contents of website/site/ (read-only). Standard library only.

Environment:
  PORT   port to bind (default 8080 locally; the container and Render set PORT=10000)
  HOST   address to bind (default 127.0.0.1 locally; the container sets 0.0.0.0)
  SITE_ROOT  optional override of the directory to serve

Endpoints:
  GET/HEAD /            index.html
  GET/HEAD /healthz     200 "ok" (used by the Docker HEALTHCHECK and by Render)
  GET/HEAD /<path>      file under the site root; 404 otherwise; no directory listings

Security headers on every response: CSP limited to same-origin, nosniff, no referrer
leakage, no framing, HSTS (effective only behind HTTPS, which Render terminates).
"""
from __future__ import annotations

import os
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
SITE_ROOT = Path(os.environ.get("SITE_ROOT", HERE / "site")).resolve()

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; "
        "form-action 'none'; frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=(), usb=()",
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": "max-age=31536000",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}


class Handler(SimpleHTTPRequestHandler):
    server_version = "GEFStatic/1.0"
    sys_version = ""

    def log_message(self, fmt, *args):  # keep logs short; no query strings or user agents
        sys.stderr.write("%s %s\n" % (self.log_date_time_string(), fmt % args))

    def end_headers(self):
        for k, v in SECURITY_HEADERS.items():
            self.send_header(k, v)
        super().end_headers()

    def _resolve(self, url_path: str) -> Path | None:
        rel = unquote(url_path).lstrip("/")
        if rel == "" or rel.endswith("/"):
            rel += "index.html"
        candidate = (SITE_ROOT / rel).resolve()
        try:
            candidate.relative_to(SITE_ROOT)
        except ValueError:
            return None  # path traversal attempt
        return candidate

    def _send_bytes(self, status: int, ctype: str, body: bytes, head_only: bool):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def _handle(self, head_only: bool):
        path = urlsplit(self.path).path
        if path == "/healthz":
            return self._send_bytes(HTTPStatus.OK, "text/plain; charset=utf-8", b"ok\n", head_only)
        if path == "/favicon.ico":
            # Browsers request /favicon.ico by default; serve the SVG icon instead. Still resolved by _resolve.
            path = "/favicon.svg"
        target = self._resolve(path)
        if target is None or not target.is_file():
            return self._send_bytes(HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8", b"Not found\n", head_only)
        ctype = CONTENT_TYPES.get(target.suffix.lower(), "application/octet-stream")
        body = target.read_bytes()
        return self._send_bytes(HTTPStatus.OK, ctype, body, head_only)

    def do_GET(self):  # noqa: N802
        self._handle(head_only=False)

    def do_HEAD(self):  # noqa: N802
        self._handle(head_only=True)

    def do_POST(self):  # noqa: N802
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self.send_header("Allow", "GET, HEAD")
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_PUT = do_DELETE = do_PATCH = do_POST  # noqa: N815


def main() -> None:
    if not (SITE_ROOT / "index.html").exists():
        sys.exit(f"index.html not found under {SITE_ROOT}; run website/build/build_site.py first.")
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8080"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    print(f"Serving {SITE_ROOT} at http://{host}:{port}/ (healthz: /healthz)", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
